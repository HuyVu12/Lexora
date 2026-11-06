"""FastAPI web layer over the standard-library core (ReviewStore, ChatService, SourceLibrary, AccountStore).

Business logic stays in the core; this layer adds accounts and roles and keeps the loopback gates
of the legacy server: a per-process POST token, Host and Origin checks, a bounded request size,
no request logging, strict security headers, {"error": ...} bodies and 409 with code
"base_changed". Sessions are HttpOnly, SameSite=Strict cookies.

Roles: `reader` asks questions over published knowledge bases; `reviewer` also imports, reviews and
publishes; `admin` also manages accounts. Chat sessions are private to the account that started them.
"""

from pathlib import Path
import json
import secrets
import threading
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from legal_ai.auth import SESSION_HOURS, AccountStore, AuthError
from legal_ai.glossary import bilingual, embed_terms
from legal_ai.ingestion.source_library import SourceLibrary
from legal_ai.kb.import_review import MAX_BYTES, Conflict
from legal_ai.rag.review_chat import ChatService
from legal_ai.web.setup import run_extraction

PACKAGE = Path(__file__).resolve().parents[1]
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; "
       "img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
TOKEN_PLACEHOLDER = "__CSRF_TOKEN__"
COOKIE = "lexora_session"
NO_EXTRACTOR = "Chưa bật model tách quy phạm cho phiên chạy này"
REVIEW_ROLES = ("admin", "reviewer")


class Denied(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(Body):
    username: str
    password: str


class PrepareBody(Body):
    title: str
    text: str
    synthetic: bool = False
    target: dict | None = None
    extraction: Literal["rules", "llm"] = "rules"


class PrepareSourceBody(Body):
    source_id: str
    target: dict | None = None
    extraction: Literal["rules", "llm"] = "rules"


class DraftBody(Body):
    draft_id: str


class ReviewBody(Body):
    draft_id: str
    item_id: str | None = None
    decision: str
    payload: dict | None = None


class PublishBody(Body):
    draft_id: str
    reason: str


class ChatStartBody(Body):
    kb_ids: list[str]


class ChatAskBody(Body):
    session_id: str
    question: str
    mode: Literal["extractive", "llm"] = "extractive"
    allow_public_transfer: bool = False
    semantic: bool = False


class AccountCreateBody(Body):
    username: str
    display_name: str
    role: Literal["admin", "reviewer", "reader"]
    password: str


class AccountUpdateBody(Body):
    id: int
    display_name: str | None = None
    role: Literal["admin", "reviewer", "reader"] | None = None
    active: bool | None = None
    password: str | None = None


def error(message, status, **extra):
    return JSONResponse({"error": message, **extra}, status_code=status)


def create_app(store, port, *, provider=None, source_catalog=None, extractor=None, embedder=None, token=None, frontend_dir=None):
    """Build the app for one loopback port and one workspace store; `frontend_dir` is the SvelteKit static build."""
    token = token or secrets.token_urlsafe(32)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    accounts = AccountStore(store.path)
    chat = ChatService(store, provider, embedder)
    library = SourceLibrary(source_catalog)
    store.interrupt_extractions()
    frontend = Path(frontend_dir).resolve() if frontend_dir else None
    app = FastAPI(title="Lexora", docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")
    app.state.token, app.state.accounts = token, accounts

    def options(body):
        if body.extraction == "llm" and extractor is None:
            raise ValueError(NO_EXTRACTOR)
        return {"extraction": body.extraction, "extraction_model": extractor.model if body.extraction == "llm" else None}

    def launch(draft):
        if draft.get("extraction", {}).get("mode") == "llm":
            units, targets = store.start_extraction(draft["id"])
            threading.Thread(target=run_extraction, args=(store, extractor, draft["id"], units, targets), daemon=True).start()

    def current(request: Request):
        account = accounts.session(request.cookies.get(COOKIE))
        if account is None:
            raise Denied(401, "Phiên đăng nhập đã hết hạn; hãy đăng nhập lại")
        return account

    def reviewer(account=Depends(current)):
        if account["role"] not in REVIEW_ROLES:
            raise Denied(403, "Tài khoản tra cứu không được nhập, duyệt hay công bố")
        return account

    def admin(account=Depends(current)):
        if account["role"] != "admin":
            raise Denied(403, "Chỉ quản trị được quản lý tài khoản")
        return account

    def own_chat(session_id, account):
        if session_id not in accounts.chats_of(account["id"]):
            raise Denied(404, "Không tìm thấy cuộc trò chuyện")

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = request.headers.get("host")
        if request.method == "POST":
            try:
                size = int(request.headers.get("content-length", "0"))
            except ValueError:
                size = -1
            if not 0 < size <= MAX_BYTES * 7:
                response = error("Request exceeds local upload limit", 400)
            elif host not in hosts or request.headers.get("x-lexora-token") != token:
                response = error("Invalid local request token", 403)
            elif request.headers.get("origin") and request.headers["origin"] != "http://" + host:
                response = error("Invalid origin", 403)
            elif request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
                response = error("Expected application/json", 400)
            else:
                response = await call_next(request)
        elif host not in hosts:
            response = error("Invalid local host", 403)
        else:
            response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = CSP
        return response

    @app.exception_handler(Denied)
    async def denied(_, exc):
        return error(exc.message, exc.status)

    @app.exception_handler(AuthError)
    async def refused(_, exc):
        return error(str(exc), 401)

    @app.exception_handler(Conflict)
    async def conflict(_, exc):
        return error(str(exc), 409, code="base_changed")

    @app.exception_handler(ValueError)
    @app.exception_handler(KeyError)
    @app.exception_handler(TypeError)
    async def bad_request(_, exc):
        return error(str(exc), 400)

    @app.exception_handler(OSError)
    async def storage_failed(_, __):
        return error("Không thể lưu dữ liệu local; kiểm tra dung lượng và quyền thư mục", 500)

    @app.exception_handler(RequestValidationError)
    async def invalid_body(_, exc):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        return error(f"Invalid request: {where} {first.get('msg', '')}".strip(), 400)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_, exc):
        return error("Not found" if exc.status_code == 404 else str(exc.detail), exc.status_code)

    # Accounts --------------------------------------------------------------------------
    @app.post("/api/auth/login")
    def login(body: LoginBody):
        session, account = accounts.login(body.username, body.password)
        response = JSONResponse(account)
        response.set_cookie(COOKIE, session, max_age=SESSION_HOURS * 3600, httponly=True, samesite="strict", path="/")
        return response

    @app.post("/api/auth/logout")
    def logout(request: Request):
        accounts.logout(request.cookies.get(COOKIE))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
        return response

    @app.get("/api/auth/me")
    def me(account=Depends(current)):
        return account

    @app.get("/api/users")
    def users(_=Depends(admin)):
        return {"accounts": accounts.list()}

    @app.post("/api/users")
    def create_user(body: AccountCreateBody, _=Depends(admin)):
        return accounts.create(body.username, body.display_name, body.role, body.password)

    @app.post("/api/users/update")
    def update_user(body: AccountUpdateBody, actor=Depends(admin)):
        return accounts.update(body.id, actor_id=actor["id"], role=body.role, active=body.active,
                               password=body.password, display_name=body.display_name)

    # Workspace -------------------------------------------------------------------------
    @app.get("/api/state")
    def state(account=Depends(current)):
        mine = accounts.chats_of(account["id"])
        value = {**store.state(), "chat_sessions": [s for s in chat.sessions() if s["id"] in mine],
                 "router_enabled": provider is not None, "account": account,
                 "extraction_model": extractor.model if extractor else None,
                 "embedding_model": embedder.model if embedder else None}
        if account["role"] not in REVIEW_ROLES:
            value["drafts"] = []
            value["knowledge_bases"] = [k for k in value["knowledge_bases"] if k.get("current_revision")]
        return value

    @app.get("/api/glossary")
    def glossary():
        return bilingual()

    @app.get("/api/sources")
    def sources(_=Depends(reviewer)):
        return {"entries": library.entries()}

    @app.get("/api/kb")
    def knowledge_base(id: str = Query(), _=Depends(current)):
        return store.knowledge_base(id)

    @app.get("/api/draft")
    def draft(id: str = Query(), _=Depends(reviewer)):
        return store.draft_view(id)

    @app.post("/api/prepare")
    def prepare(body: PrepareBody, _=Depends(reviewer)):
        made = store.prepare(body.title, body.text, body.synthetic, target=body.target, **options(body))
        launch(made)
        return store.draft_view(made["id"])

    @app.post("/api/prepare-source")
    def prepare_source(body: PrepareSourceBody, _=Depends(reviewer)):
        made = library.prepare(store, body.source_id, body.target, **options(body))
        launch(made)
        return store.draft_view(made["id"])

    @app.post("/api/draft/extract")
    def extract(body: DraftBody, _=Depends(reviewer)):
        if extractor is None:
            raise ValueError(NO_EXTRACTOR)
        launch(store.draft(body.draft_id))
        return store.draft_view(body.draft_id)

    @app.post("/api/draft/review")
    def review(body: ReviewBody, _=Depends(reviewer)):
        return store.review(body.draft_id, body.item_id, body.decision, body.payload)

    @app.post("/api/draft/discard")
    def discard(body: DraftBody, _=Depends(reviewer)):
        store.discard(body.draft_id)
        return {"discarded": body.draft_id}

    @app.post("/api/publish")
    def publish(body: PublishBody, account=Depends(reviewer)):
        # The reviewer of record is the signed-in account, never a name typed into the form.
        revision = store.publish(body.draft_id, f"{account['display_name']} ({account['username']})", body.reason)
        return {"revision": revision["id"], "kb_id": revision["kb_id"], "summary": revision["graph"]["summary"]}

    @app.post("/api/chat/start")
    def chat_start(body: ChatStartBody, account=Depends(current)):
        started = chat.start(body.kb_ids)
        accounts.own_chat(started["id"], account["id"])
        return started

    @app.get("/api/chat/session")
    def chat_session(id: str = Query(), account=Depends(current)):
        own_chat(id, account)
        return chat.session(id)

    @app.post("/api/chat/ask")
    def chat_ask(body: ChatAskBody, account=Depends(current)):
        own_chat(body.session_id, account)
        return chat.ask(body.session_id, body.question, body.mode, body.allow_public_transfer, body.semantic)

    # Graph viewers (self-contained pages of published revisions) --------------------------
    def viewer_page(request, revision_id, structure):
        if accounts.session(request.cookies.get(COOKIE)) is None:
            return RedirectResponse("/login", status_code=303)
        revision = store.revision(revision_id)
        graph = revision["graph"]
        semantic = any(n["kind"] == "NormClaim" and n["payload"].get("semantic_extraction") for n in graph["nodes"])
        template = "entity-viewer.html" if semantic and not structure else "viewer.html"
        page = (PACKAGE / "kb" / template).read_text(encoding="utf-8")
        payload = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        page = (page.replace("__GRAPH_JSON__", payload)
                .replace('href="structure.html"', f'href="/structure.html?revision={revision["id"]}"')
                .replace('href="index.html"', f'href="/viewer?revision={revision["id"]}"'))
        return HTMLResponse(embed_terms(page))

    @app.get("/viewer")
    def viewer(request: Request, revision: str = Query()):
        return viewer_page(request, revision, False)

    @app.get("/structure.html")
    def structure(request: Request, revision: str = Query()):
        return viewer_page(request, revision, True)

    # SvelteKit static build ------------------------------------------------------------------
    def index_page():
        if not frontend or not (frontend / "index.html").is_file():
            return HTMLResponse("<!doctype html><meta charset=utf-8><title>Lexora</title>"
                                "<p>Chưa có bản build giao diện. Chạy <code>npm run build</code> trong <code>frontend/</code>, "
                                "rồi khởi động lại với <code>--frontend frontend/build</code>.</p>", status_code=503)
        page = (frontend / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(page.replace(TOKEN_PLACEHOLDER, token))

    @app.get("/")
    def index():
        return index_page()

    @app.get("/{path:path}")
    def static(path: str):
        if path.startswith("api/"):
            raise StarletteHTTPException(404)
        if frontend:
            target = (frontend / path).resolve()
            if frontend in target.parents and target.is_file():
                return Response(target.read_bytes(), media_type=_mime(target.suffix),
                                headers={"Cache-Control": "public, max-age=31536000, immutable"} if "/immutable/" in path else None)
        return index_page()  # SPA fallback for client-side routes; never serves files outside the build.

    return app


def _mime(suffix):
    return {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8",
            ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
            ".woff2": "font/woff2", ".woff": "font/woff", ".txt": "text/plain; charset=utf-8", ".webmanifest": "application/manifest+json"
            }.get(suffix.lower(), "application/octet-stream")
