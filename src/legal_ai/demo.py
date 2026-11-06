"""Loopback-only, single-user import/review demo. Run: python -m legal_ai.demo."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit

from legal_ai.kb.import_review import MAX_BYTES, ReviewStore
from legal_ai.ingestion.source_library import SourceLibrary
from legal_ai.rag.review_chat import ChatService


def make_server(store, port=8765, *, provider=None, source_catalog=None):
    token = secrets.token_urlsafe(32)
    chat = ChatService(store, provider)
    library = SourceLibrary(source_catalog)

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
                    self.respond(page.replace("__CSRF_TOKEN__", token), mime="text/html; charset=utf-8")
                elif url.path == "/demo-chat.js":
                    self.respond(Path(__file__).with_name("demo-chat.js").read_text(encoding="utf-8"), mime="text/javascript; charset=utf-8")
                elif url.path == "/api/state":
                    self.respond({**store.state(), "chat_sessions": chat.sessions(), "router_enabled": provider is not None})
                elif url.path == "/api/sources":
                    self.respond({"entries": library.entries()})
                elif url.path == "/api/chat/session":
                    self.respond(chat.session(query["id"][0]))
                elif url.path == "/api/draft":
                    self.respond(store.draft(query["id"][0]))
                elif url.path == "/api/revision":
                    self.respond(store.revision(query["id"][0]))
                elif url.path in {"/viewer", "/structure.html"}:
                    revision = store.revision(query["revision"][0]) if "revision" in query else store.current()
                    graph = revision["graph"]
                    semantic = any(n["kind"] == "NormClaim" and n["payload"].get("semantic_extraction") for n in graph["nodes"])
                    template = "entity-viewer.html" if semantic and url.path == "/viewer" else "viewer.html"
                    page = (Path(__file__).parent / "kb" / template).read_text(encoding="utf-8")
                    payload = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
                    page = page.replace("__GRAPH_JSON__", payload).replace('href="structure.html"', 'href="/structure.html?revision=' + revision["id"] + '"')
                    self.respond(page, mime="text/html; charset=utf-8")
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
                    self.respond(store.prepare(body["title"], body["text"], body.get("synthetic", False)))
                elif self.path == "/api/prepare-source":
                    self.respond(library.prepare(store, body["source_id"]))
                elif self.path == "/api/chat/start":
                    self.respond(chat.start(body["revision"]))
                elif self.path == "/api/chat/ask":
                    self.respond(chat.ask(body["session_id"], body["question"], body.get("mode", "extractive"), body.get("allow_public_transfer", False)))
                elif self.path == "/api/publish":
                    revision = store.publish(body["draft_id"], body["decisions"], body["links"], body["reviewer"], body["reason"])
                    self.respond({"revision": revision["id"], "summary": revision["graph"]["summary"]})
                else:
                    self.respond({"error": "Not found"}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                self.respond({"error": str(exc)}, 400)
            except OSError:
                self.respond({"error": "Không thể lưu dữ liệu local; kiểm tra dung lượng và quyền thư mục"}, 500)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="data/kb/import-demo.sqlite")
    parser.add_argument("--seed", help="Existing evidence-graph-v2 graph.json; used only for a new store")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--source-catalog", help="Local pinned source-library-v1 catalog; no network access")
    parser.add_argument("--router-model", help="Opt in to one explicitly approved 9Router model")
    parser.add_argument("--approve-router", action="store_true", help="Explicitly authorize the exact selected route; does not assert pricing")
    parser.add_argument("--router-max-calls", type=int, default=3)
    args = parser.parse_args()
    provider = None
    if args.router_model:
        from legal_ai.providers.router import RouterProvider, read_settings
        provider = RouterProvider(read_settings(Path.cwd() / ".env"), model=args.router_model,
                                  approved_route=args.approve_router, max_calls=args.router_max_calls)
    elif args.approve_router:
        parser.error("--approve-router requires --router-model")
    store = ReviewStore(args.store, args.seed)
    server = make_server(store, args.port, provider=provider, source_catalog=args.source_catalog)
    print(f"Lexora local demo: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
