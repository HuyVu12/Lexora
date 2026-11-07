"""FastAPI web layer over the standard-library core (ReviewStore, ChatService, SourceLibrary, AccountStore).

Business logic stays in the core; this layer adds accounts and roles and keeps the loopback gates
of the legacy server: a per-process POST token, Host and Origin checks, a bounded request size,
no request logging, strict security headers, {"error": ...} bodies and 409 with code
"base_changed". Sessions are HttpOnly, SameSite=Strict cookies.

Roles: `reader` asks questions over published knowledge bases; `reviewer` also imports, reviews and
publishes; `admin` also manages accounts. Chat sessions are private to the account that started them.
"""

import base64
import binascii
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
from legal_ai.ingestion.catalog import Catalog
from legal_ai.ingestion.excerpt import excerpt as cut_excerpt, outline as article_outline
from legal_ai.ingestion.files import MAX_FILE_BYTES, extract_text
from legal_ai.ingestion.source_library import SourceLibrary
from legal_ai.ingestion.vbpl_api import document_text, fetch_document, load_snapshot, unwrap
from legal_ai.kb.import_review import MAX_BYTES, Conflict
from legal_ai.rag.review_chat import ChatService
from legal_ai.research.corpus import CorpusStore
from legal_ai.research import proposals as question_proposals
from legal_ai.research.questions import QuestionStore
from legal_ai.providers.claude_code import ProviderError
from legal_ai.web.setup import run_extraction

PACKAGE = Path(__file__).resolve().parents[1]
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; "
       "img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
TOKEN_PLACEHOLDER = "__CSRF_TOKEN__"
COOKIE = "lexora_session"
NO_EXTRACTOR = "Chưa bật model tách quy phạm cho phiên chạy này"
REVIEW_ROLES = ("admin", "reviewer")
NO_VBPL = "Chưa bật lấy văn bản từ vbpl.vn cho phiên chạy này (khởi động lại với --allow-vbpl)"
NO_CATALOG = "Chưa có danh mục văn bản (khởi động với --catalog)"
# A base64 upload of the largest accepted file, plus the JSON around it.
UPLOAD_PATH, UPLOAD_LIMIT = "/api/corpus/file", MAX_FILE_BYTES * 4 // 3 + 100_000
# Question packs carry a corpus version; they get the same large limit as file uploads.
LARGE_PATHS = {UPLOAD_PATH, "/api/prepare-file", "/api/question-sets/import-pack", "/api/question-set/import-labels"}
NO_PROPOSER = "Chưa bật đề xuất bằng model cho phiên chạy này (khởi động với --proposal-model và --approve-claude)"


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


class ImportVbplBody(Body):
    reference: str
    confirm: bool = False


class PrepareVbplBody(Body):
    vbpl_id: str
    source_sha256: str
    article_ids: list[str]
    target: dict | None = None
    extraction: Literal["rules", "llm"] = "rules"


class PrepareFileBody(Body):
    filename: str
    content_base64: str
    title: str
    synthetic: bool = False
    target: dict | None = None
    extraction: Literal["rules", "llm"] = "rules"


class CorpusCreateBody(Body):
    name: str
    description: str = ""


class CorpusVbplBody(Body):
    corpus_id: str
    reference: str
    document_id: str | None = None
    confirm: bool = False


class CorpusFileBody(Body):
    corpus_id: str
    filename: str
    content_base64: str
    title: str | None = None
    document_id: str | None = None


class CorpusDocumentBody(Body):
    corpus_id: str
    document_row: str


class CorpusFreezeBody(Body):
    corpus_id: str
    note: str = ""


class QuestionSetCreateBody(Body):
    name: str
    corpus_version_id: str
    guideline: str = ""


class QuestionSetBody(Body):
    set_id: str


class QuestionModeBody(Body):
    set_id: str
    show_proposals: bool


class QuestionAddBody(Body):
    set_id: str
    text: str
    family_id: str | None = None


class QuestionRefBody(Body):
    set_id: str
    question_id: str


class QuestionLabelBody(Body):
    set_id: str
    question_id: str
    fields: dict
    note: str = ""


class QuestionProposeBody(Body):
    set_id: str
    question_id: str
    confirm: bool = False


class QuestionDraftBody(Body):
    set_id: str
    unit_ids: list[str]
    count: int = 4
    confirm: bool = False


class QuestionAcceptBody(Body):
    set_id: str
    draft_id: str
    index: int
    texts: list[str]


class PackBody(Body):
    pack: dict


class LabelsBody(Body):
    labels: dict


class FreezeQuestionsBody(Body):
    set_id: str
    other: str
    held_out: float = 0.3


def error(message, status, **extra):
    return JSONResponse({"error": message, **extra}, status_code=status)


def create_app(store, port, *, provider=None, source_catalog=None, extractor=None, embedder=None, token=None, frontend_dir=None,
               catalog_path=None, vbpl_dir=None, proposer=None):
    """Build the app for one loopback port and one workspace store; `frontend_dir` is the SvelteKit static build.

    `catalog_path` enables the offline document catalog. `vbpl_dir` (only with --allow-vbpl) lets reviewers fetch
    one vbpl.vn document per confirmed request into that snapshot directory. `proposer` (only with --approve-claude)
    is the structured model provider for question proposals and drafts; each call needs a confirmation."""
    token = token or secrets.token_urlsafe(32)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    accounts = AccountStore(store.path)
    chat = ChatService(store, provider, embedder)
    library = SourceLibrary(source_catalog)
    corpora = CorpusStore(store.path)
    catalog = Catalog(catalog_path) if catalog_path else None
    questions = QuestionStore(store.path, corpora)
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
            if not 0 < size <= (UPLOAD_LIMIT if request.url.path in LARGE_PATHS else MAX_BYTES * 7):
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

    @app.get("/api/kb/graph")
    def knowledge_base_graph(id: str = Query(), _=Depends(current)):
        """The evidence graph of a base's current published revision (what readers may see)."""
        kb = store.knowledge_base(id)
        revision = store.revision(kb["current_revision"], kb["id"])
        return {"kb_id": kb["id"], "revision": revision["id"], "graph": revision["graph"]}

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

    # Importing official documents and files into a knowledge base ------------------------
    def vbpl_text(manifest, raw):
        meta = manifest["metadata"]
        if meta.get("is_translation"):
            raise ValueError("Đây là bản dịch; hãy chọn bản gốc tiếng Việt")
        return document_text(unwrap(raw))["text"]

    @app.post("/api/import/vbpl")
    def import_vbpl(body: ImportVbplBody, _=Depends(reviewer)):
        """One confirmed vbpl.vn fetch; returns the document and its article outline for choosing what to import."""
        if vbpl_dir is None:
            raise ValueError(NO_VBPL)
        if not body.confirm:
            raise ValueError("Hãy xác nhận trước khi Lexora gọi vbpl.vn")
        try:
            manifest = fetch_document(body.reference, vbpl_dir)
        except OSError as exc:
            raise ValueError(f"Không kết nối được vbpl.vn ({exc.__class__.__name__})") from exc
        articles = article_outline(vbpl_text(manifest, Path(manifest["local_path"]).read_bytes()))
        if not articles:
            meta = manifest["metadata"]
            raise ValueError(f"Văn bản này ({(meta.get('doc_type') or 'văn bản').lower()} {meta.get('doc_num') or ''}) không chia thành Điều nên không nhập được. "
                             "Lệnh công bố, chỉ thị và công văn thường như vậy; hãy chọn chính văn bản luật, nghị định hoặc thông tư.")
        return {"vbpl_id": manifest["vbpl_id"], "source_sha256": manifest["source_sha256"], "site_url": manifest["site_url"],
                "metadata": manifest["metadata"], "accessed_at": manifest["accessed_at"], "articles": articles}

    @app.post("/api/prepare-vbpl")
    def prepare_vbpl(body: PrepareVbplBody, _=Depends(reviewer)):
        """A draft from chosen articles of a stored vbpl.vn snapshot (no new network call)."""
        if vbpl_dir is None:
            raise ValueError(NO_VBPL)
        manifest, raw = load_snapshot(vbpl_dir, body.vbpl_id, body.source_sha256)
        meta = manifest["metadata"]
        text = cut_excerpt(vbpl_text(manifest, raw), body.article_ids)
        headings = [a["heading"].split(".")[0] for a in article_outline(text)]
        span = headings[0] if len(headings) == 1 else f"{headings[0]} - {headings[-1]}"
        title = f"{meta.get('title') or meta.get('doc_num')} ({span})"[:200]
        made = store.prepare(title, text, False, manifest["site_url"], target=body.target, **options(body))
        launch(made)
        return store.draft_view(made["id"])

    @app.post("/api/prepare-file")
    def prepare_file(body: PrepareFileBody, _=Depends(reviewer)):
        try:
            data = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Nội dung tệp không hợp lệ") from exc
        text = extract_text(body.filename, data)["text"]
        made = store.prepare(body.title, text, body.synthetic, target=body.target, **options(body))
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

    # Research corpora (reviewers) -------------------------------------------------------
    @app.get("/api/corpora")
    def corpus_list(_=Depends(reviewer)):
        return {"corpora": corpora.corpora(), "vbpl_enabled": vbpl_dir is not None, "catalog": catalog.info() if catalog else None}

    @app.post("/api/corpora")
    def corpus_create(body: CorpusCreateBody, account=Depends(reviewer)):
        return corpora.create(body.name, body.description, account["username"])

    @app.get("/api/corpus")
    def corpus_detail(id: str = Query(), _=Depends(reviewer)):
        return corpora.corpus(id)

    @app.get("/api/corpus/document")
    def corpus_document(id: str = Query(), _=Depends(reviewer)):
        return corpora.document(id)

    @app.post("/api/corpus/vbpl")
    def corpus_vbpl(body: CorpusVbplBody, account=Depends(reviewer)):
        """One network call to vbpl.vn, only when this run allows it and the reviewer confirmed it."""
        if vbpl_dir is None:
            raise ValueError(NO_VBPL)
        if not body.confirm:
            raise ValueError("Hãy xác nhận trước khi Lexora gọi vbpl.vn")
        corpora.corpus(body.corpus_id)
        try:
            manifest = fetch_document(body.reference, vbpl_dir)
        except OSError as exc:  # Network failures are not storage failures.
            raise ValueError(f"Không kết nối được vbpl.vn ({exc.__class__.__name__})") from exc
        raw = Path(manifest["local_path"]).read_bytes()
        return corpora.add_vbpl(body.corpus_id, manifest, raw, account["username"], body.document_id or None)

    @app.post(UPLOAD_PATH)
    def corpus_file(body: CorpusFileBody, account=Depends(reviewer)):
        try:
            data = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Nội dung tệp không hợp lệ") from exc
        return corpora.add_file(body.corpus_id, body.filename, data, account["username"], body.title, body.document_id or None)

    @app.post("/api/corpus/remove")
    def corpus_remove(body: CorpusDocumentBody, _=Depends(reviewer)):
        return corpora.remove(body.corpus_id, body.document_row)

    @app.post("/api/corpus/freeze")
    def corpus_freeze(body: CorpusFreezeBody, account=Depends(reviewer)):
        return corpora.freeze(body.corpus_id, body.note, account["username"])

    @app.get("/api/catalog/search")
    def catalog_search(q: str = Query(), limit: int = Query(20), translations: bool = Query(False), _=Depends(reviewer)):
        if catalog is None:
            raise ValueError(NO_CATALOG)
        return {"results": catalog.search(q, limit, translations)}

    @app.get("/api/catalog/document")
    def catalog_document(id: str = Query(), _=Depends(reviewer)):
        if catalog is None:
            raise ValueError(NO_CATALOG)
        document = catalog.document(id)
        if document is None:
            raise ValueError("Không có văn bản này trong danh mục")
        return document | {"relationships": catalog.relationships(id)}

    # Question sets (reviewers; the signed-in account is the annotator) ------------------
    def frozen_versions():
        listing = []
        for c in corpora.corpora():
            for v in corpora.corpus(c["id"])["versions"]:
                listing.append({"id": v["id"], "corpus_id": c["id"], "corpus_name": c["name"], "number": v["number"],
                                "document_count": v["document_count"], "unit_count": v["unit_count"], "frozen_at": v["frozen_at"]})
        return listing

    def model_call(fn):
        if proposer is None:
            raise ValueError(NO_PROPOSER)
        try:
            return fn()
        except ProviderError as exc:
            raise ValueError(f"Model không trả lời được ({exc.code}); lần gọi đã được ghi lại") from exc

    def download(body, filename):
        return JSONResponse(body, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @app.get("/api/question-sets")
    def question_sets(_=Depends(reviewer)):
        return {"sets": questions.sets(), "versions": frozen_versions(), "proposal_model": proposer.model if proposer else None,
                "proposal_effort": proposer.effort if proposer else None}

    @app.post("/api/question-sets")
    def question_set_create(body: QuestionSetCreateBody, account=Depends(reviewer)):
        return questions.create(body.name, body.corpus_version_id, body.guideline, account["username"])

    @app.get("/api/question-set")
    def question_set(id: str = Query(), account=Depends(reviewer)):
        view = questions.workspace(id, account["username"])
        return view | {"annotators": questions.annotators(id), "calls": len(questions.calls(id)),
                       "proposal_model": proposer.model if proposer else None,
                       "proposal_calls_left": proposer.max_calls - proposer.calls if proposer else 0}

    @app.post("/api/question-set/mode")
    def question_set_mode(body: QuestionModeBody, account=Depends(reviewer)):
        questions.set_mode(body.set_id, account["username"], body.show_proposals)
        return {"show_proposals": body.show_proposals}

    @app.post("/api/question-set/question")
    def question_add(body: QuestionAddBody, account=Depends(reviewer)):
        return questions.add_question(body.set_id, body.text, account["username"], body.family_id or None)

    @app.post("/api/question-set/question/remove")
    def question_remove(body: QuestionRefBody, _=Depends(reviewer)):
        questions.remove_question(body.set_id, body.question_id)
        return {"removed": body.question_id}

    @app.post("/api/question-set/label")
    def question_label(body: QuestionLabelBody, account=Depends(reviewer)):
        return questions.save_label(body.set_id, body.question_id, account["username"], account["display_name"], body.fields, body.note)

    @app.get("/api/question-set/candidates")
    def question_candidates(set_id: str = Query(), q: str = Query(), k: int = Query(8), _=Depends(reviewer)):
        version = questions.summary(set_id)["corpus_version_id"]
        return {"candidates": question_proposals.candidates(corpora, version, q, max(1, min(k, 20)))}

    @app.get("/api/question-set/outline")
    def question_outline(set_id: str = Query(), _=Depends(reviewer)):
        """The articles of the set's corpus version (ID, document, heading line), for picking draft sources."""
        documents, units, _ = corpora.bundle(questions.summary(set_id)["corpus_version_id"])
        titles = {d["document_id"]: d["title"] for d in documents}
        return {"articles": [{"unit_id": u["unit_id"], "document_id": u["document_id"], "document_title": titles[u["document_id"]],
                              "heading": u["text"].strip().split("\n")[0][:200]} for u in units if u["unit_type"] == "article"]}

    @app.get("/api/question-set/units")
    def question_units(set_id: str = Query(), ids: str = Query(), _=Depends(reviewer)):
        _, units, _ = corpora.bundle(questions.summary(set_id)["corpus_version_id"])
        wanted = set(ids.split(","))
        return {"units": [{"unit_id": u["unit_id"], "unit_type": u["unit_type"], "text": u["text"]} for u in units if u["unit_id"] in wanted]}

    @app.post("/api/question-set/propose")
    def question_propose(body: QuestionProposeBody, _=Depends(reviewer)):
        if not body.confirm:
            raise ValueError("Hãy xác nhận trước khi Lexora gọi model")
        return model_call(lambda: question_proposals.propose_label(proposer, questions, body.set_id, body.question_id))

    @app.post("/api/question-set/draft")
    def question_draft(body: QuestionDraftBody, _=Depends(reviewer)):
        if not body.confirm:
            raise ValueError("Hãy xác nhận trước khi Lexora gọi model")
        return model_call(lambda: question_proposals.draft_questions(proposer, questions, body.set_id, body.unit_ids, body.count))

    @app.post("/api/question-set/draft/accept")
    def question_draft_accept(body: QuestionAcceptBody, account=Depends(reviewer)):
        return {"added": questions.accept_draft(body.set_id, body.draft_id, body.index, body.texts, account["username"])}

    @app.get("/api/question-set/pack")
    def question_pack(id: str = Query(), _=Depends(reviewer)):
        return download(questions.export_pack(id), f"lexora-question-pack-{id}.json")

    @app.post("/api/question-sets/import-pack")
    def question_import_pack(body: PackBody, account=Depends(reviewer)):
        return questions.import_pack(body.pack, account["username"])

    @app.get("/api/question-set/labels")
    def question_labels(id: str = Query(), account=Depends(reviewer)):
        return download(questions.export_labels(id, account["username"]), f"lexora-labels-{id}-{account['username']}.json")

    @app.post("/api/question-set/import-labels")
    def question_import_labels(body: LabelsBody, account=Depends(reviewer)):
        return questions.import_labels(body.labels, account["username"])

    @app.get("/api/question-set/compare")
    def question_compare(id: str = Query(), other: str = Query(), account=Depends(reviewer)):
        return questions.comparison(id, account["username"], other)

    @app.post("/api/question-set/adjudicate")
    def question_adjudicate(body: QuestionLabelBody, account=Depends(reviewer)):
        return questions.adjudicate(body.set_id, body.question_id, body.fields, body.note, account["username"])

    @app.post("/api/question-set/freeze")
    def question_freeze(body: FreezeQuestionsBody, account=Depends(reviewer)):
        return questions.freeze(body.set_id, account["username"], body.other, account["username"], body.held_out)

    @app.get("/api/question-set/frozen")
    def question_frozen(id: str = Query(), _=Depends(reviewer)):
        return download(questions.frozen_file(id), f"lexora-questions-{id}.json")

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
