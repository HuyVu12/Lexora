"""Loopback-only, single-user knowledge base workspace demo. Run: python -m legal_ai.demo."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, urlsplit

from legal_ai.glossary import embed_terms
from legal_ai.kb.import_review import MAX_BYTES, Conflict, ReviewStore
from legal_ai.ingestion.source_library import SourceLibrary
from legal_ai.rag.review_chat import ChatService
from legal_ai.web.setup import add_arguments, providers, run_extraction


STATIC = {"/demo-app.js": ("demo-app.js", "text/javascript; charset=utf-8"),
          "/demo.css": ("demo.css", "text/css; charset=utf-8")}


def make_server(store, port=8765, *, provider=None, source_catalog=None, extractor=None, embedder=None):
    token = secrets.token_urlsafe(32)
    chat = ChatService(store, provider, embedder)
    library = SourceLibrary(source_catalog)
    store.interrupt_extractions()

    def options(body):
        mode = body.get("extraction", "rules")
        if mode == "llm" and extractor is None:
            raise ValueError("Chưa bật model tách quy phạm cho phiên chạy này")
        return {"extraction": mode, "extraction_model": extractor.model if mode == "llm" else None}

    def launch(draft):
        if draft.get("extraction", {}).get("mode") == "llm":
            units, targets = store.start_extraction(draft["id"])
            threading.Thread(target=run_extraction, args=(store, extractor, draft["id"], units, targets), daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not log uploaded content or request URLs.

        def respond(self, value, status=200, mime="application/json; charset=utf-8"):
            body = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def host_ok(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.host_ok():
                self.respond({"error": "Invalid local host"}, 403)
                return
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            try:
                if url.path == "/":
                    page = Path(__file__).with_name("demo.html").read_text(encoding="utf-8")
                    self.respond(embed_terms(page.replace("__CSRF_TOKEN__", token)), mime="text/html; charset=utf-8")
                elif url.path in STATIC:
                    name, mime = STATIC[url.path]
                    self.respond(Path(__file__).with_name(name).read_text(encoding="utf-8"), mime=mime)
                elif url.path == "/api/state":
                    self.respond({**store.state(), "chat_sessions": chat.sessions(), "router_enabled": provider is not None,
                                  "extraction_model": extractor.model if extractor else None,
                                  "embedding_model": embedder.model if embedder else None})
                elif url.path == "/api/sources":
                    self.respond({"entries": library.entries()})
                elif url.path == "/api/kb":
                    self.respond(store.knowledge_base(query["id"][0]))
                elif url.path == "/api/chat/session":
                    self.respond(chat.session(query["id"][0]))
                elif url.path == "/api/draft":
                    self.respond(store.draft_view(query["id"][0]))
                elif url.path in {"/viewer", "/structure.html"}:
                    revision = store.revision(query["revision"][0])
                    graph = revision["graph"]
                    semantic = any(n["kind"] == "NormClaim" and n["payload"].get("semantic_extraction") for n in graph["nodes"])
                    template = "entity-viewer.html" if semantic and url.path == "/viewer" else "viewer.html"
                    page = (Path(__file__).parent / "kb" / template).read_text(encoding="utf-8")
                    payload = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
                    page = page.replace("__GRAPH_JSON__", payload).replace('href="structure.html"', 'href="/structure.html?revision=' + revision["id"] + '"').replace('href="index.html"', 'href="/viewer?revision=' + revision["id"] + '"')
                    self.respond(embed_terms(page), mime="text/html; charset=utf-8")
                else:
                    self.respond({"error": "Not found"}, 404)
            except (ValueError, KeyError) as exc:
                self.respond({"error": str(exc)}, 400)

        def do_POST(self):
            # Drain bounded request bodies before an early rejection. Otherwise
            # Windows can reset the socket while the client is still sending.
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BYTES * 7:
                    raise ValueError("Request exceeds local upload limit")
                raw = self.rfile.read(size)
            except ValueError as exc:
                self.respond({"error": str(exc)}, 400)
                return
            if not self.host_ok() or self.headers.get("X-Lexora-Token") != token:
                self.respond({"error": "Invalid local request token"}, 403)
                return
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers["Host"]:
                self.respond({"error": "Invalid origin"}, 403)
                return
            try:
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("Expected application/json")
                body = json.loads(raw.decode("utf-8"))
                if self.path == "/api/prepare":
                    draft = store.prepare(body["title"], body["text"], body.get("synthetic", False), target=body.get("target"), **options(body))
                    launch(draft)
                    self.respond(store.draft_view(draft["id"]))
                elif self.path == "/api/prepare-source":
                    draft = library.prepare(store, body["source_id"], body.get("target"), **options(body))
                    launch(draft)
                    self.respond(store.draft_view(draft["id"]))
                elif self.path == "/api/draft/extract":
                    if extractor is None:
                        raise ValueError("Chưa bật model tách quy phạm cho phiên chạy này")
                    launch(store.draft(body["draft_id"]))
                    self.respond(store.draft_view(body["draft_id"]))
                elif self.path == "/api/draft/review":
                    self.respond(store.review(body["draft_id"], body.get("item_id"), body["decision"], body.get("payload")))
                elif self.path == "/api/draft/discard":
                    store.discard(body["draft_id"])
                    self.respond({"discarded": body["draft_id"]})
                elif self.path == "/api/chat/start":
                    self.respond(chat.start(body["kb_ids"]))
                elif self.path == "/api/chat/ask":
                    self.respond(chat.ask(body["session_id"], body["question"], body.get("mode", "extractive"),
                                          body.get("allow_public_transfer", False), body.get("semantic", False)))
                elif self.path == "/api/publish":
                    revision = store.publish(body["draft_id"], body["reviewer"], body["reason"])
                    self.respond({"revision": revision["id"], "kb_id": revision["kb_id"], "summary": revision["graph"]["summary"]})
                else:
                    self.respond({"error": "Not found"}, 404)
            except Conflict as exc:
                self.respond({"error": str(exc), "code": "base_changed"}, 409)
            except (ValueError, KeyError, TypeError) as exc:
                self.respond({"error": str(exc)}, 400)
            except OSError:
                self.respond({"error": "Không thể lưu dữ liệu local; kiểm tra dung lượng và quyền thư mục"}, 500)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser, 8765)
    args = parser.parse_args()
    provider, extractor, embedder = providers(args, parser)
    store = ReviewStore(args.store, args.seed)
    server = make_server(store, args.port, provider=provider, source_catalog=args.source_catalog, extractor=extractor, embedder=embedder)
    print(f"Lexora local demo: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
