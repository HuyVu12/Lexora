"""Run the Lexora web app on loopback: python -m legal_ai.web (needs the `web` extra in .venv)."""

import argparse
import sys

from legal_ai.kb.import_review import ReviewStore
from legal_ai.web.setup import add_arguments, proposer, providers, sources


def main():
    # Vietnamese notices must not crash the launcher when stdout is a pipe or file in a legacy Windows code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser, 8765)
    parser.add_argument("--frontend", default="frontend/build", help="SvelteKit static build to serve (default: frontend/build)")
    parser.add_argument("--bind", default="127.0.0.1", help="address to listen on; keep loopback unless a reverse proxy on a private network forwards to it")
    parser.add_argument("--public-host", action="append", default=[], help="DNS name served over HTTPS by a reverse proxy, e.g. vlexora.duckdns.org (repeatable)")
    args = parser.parse_args()
    provider, extractor, embedder = providers(args, parser)
    import uvicorn
    from legal_ai.web.app import create_app
    store = ReviewStore(args.store, args.seed)
    from legal_ai.auth import AccountStore
    if AccountStore(store.path).count() == 0:
        print(f"Chưa có tài khoản. Tạo quản trị đầu tiên: python -m legal_ai.auth create-admin --store {args.store} --username <tên>", flush=True)
    catalog_path, vbpl_dir = sources(args)
    question_model = proposer(args, parser)
    app = create_app(store, args.port, provider=provider, source_catalog=args.source_catalog, extractor=extractor,
                     embedder=embedder, frontend_dir=args.frontend, catalog_path=catalog_path, vbpl_dir=vbpl_dir,
                     proposer=question_model, public_hosts=args.public_host)
    if extractor is not None and hasattr(extractor, "structured"):
        print(f"Claude Code: up to {extractor.max_calls} extraction calls with {extractor.model} ({extractor.effort})", flush=True)
    if question_model:
        print(f"Claude Code: up to {question_model.max_calls} proposal calls with {question_model.model} ({question_model.effort})", flush=True)
    if vbpl_dir:
        print("vbpl.vn: reviewers may fetch one document per confirmed request", flush=True)
    for name in args.public_host:
        print(f"Lexora: https://{name} (behind the reverse proxy)", flush=True)
    print(f"Lexora: listening on http://{args.bind}:{args.port} (Ctrl+C to stop)", flush=True)
    # No access log: request URLs and uploads are never logged.
    uvicorn.run(app, host=args.bind, port=args.port, access_log=False, log_level="warning", server_header=False)


if __name__ == "__main__":
    main()
