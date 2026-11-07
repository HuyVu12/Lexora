"""Run the Lexora web app on loopback: python -m legal_ai.web (needs the `web` extra in .venv)."""

import argparse

from legal_ai.kb.import_review import ReviewStore
from legal_ai.web.setup import add_arguments, proposer, providers, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser, 8765)
    parser.add_argument("--frontend", default="frontend/build", help="SvelteKit static build to serve (default: frontend/build)")
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
                     proposer=question_model)
    if question_model:
        print(f"Claude Code: up to {question_model.max_calls} proposal calls with {question_model.model} ({question_model.effort})", flush=True)
    if vbpl_dir:
        print("vbpl.vn: reviewers may fetch one document per confirmed request", flush=True)
    print(f"Lexora: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
    # Loopback only, no access log: request URLs and uploads are never logged.
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False, log_level="warning", server_header=False)


if __name__ == "__main__":
    main()
