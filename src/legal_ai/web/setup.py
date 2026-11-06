"""Standard-library pieces shared by the FastAPI app and the legacy demo server.

Command-line options, opt-in 9Router providers and the background extraction job live here so
both servers behave identically while the migration is in progress.
"""

from pathlib import Path


def add_arguments(parser, default_port):
    parser.add_argument("--store", default="data/kb/import-demo.sqlite")
    parser.add_argument("--seed", help="Existing evidence-graph-v2 graph.json; used only for a new store")
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--source-catalog", help="Local pinned source-library-v1 catalog; no network access")
    parser.add_argument("--router-model", help="Opt in to one explicitly approved 9Router model for cited answers")
    parser.add_argument("--router-max-calls", type=int, default=3)
    parser.add_argument("--extract-model", help="Opt in to one approved 9Router model for norm extraction of public KBs")
    parser.add_argument("--extract-max-calls", type=int, default=60)
    parser.add_argument("--extract-timeout", type=int, default=90, help="Seconds per extraction request")
    parser.add_argument("--embedding-model", help="Opt in to one approved 9Router embedding model for public KBs")
    parser.add_argument("--embedding-dimensions", type=int, default=768)
    parser.add_argument("--embedding-max-calls", type=int, default=200)
    parser.add_argument("--approve-router", action="store_true", help="Explicitly authorize the exact selected routes; does not assert pricing")


def providers(args, parser):
    """Build the opt-in (provider, extractor, embedder); each stays None unless its flag is given."""
    provider = extractor = embedder = None
    if args.router_model or args.extract_model or args.embedding_model:
        from legal_ai.providers.router import RouterEmbeddings, RouterProvider, read_settings
        settings = read_settings(Path.cwd() / ".env")

        def model(name):
            # Accept a MODEL_* alias from Lexora's .env, e.g. MODEL_OSS_120B.
            return settings[name] if name.startswith("MODEL_") and settings.get(name) else name

        if args.router_model:
            provider = RouterProvider(settings, model=model(args.router_model), approved_route=args.approve_router, max_calls=args.router_max_calls)
        if args.extract_model:
            extractor = RouterProvider(settings, model=model(args.extract_model), approved_route=args.approve_router,
                                       max_calls=args.extract_max_calls, timeout=args.extract_timeout)
        if args.embedding_model:
            embedder = RouterEmbeddings(settings, model=model(args.embedding_model), approved_route=args.approve_router,
                                        max_calls=args.embedding_max_calls, dimensions=args.embedding_dimensions)
    elif args.approve_router:
        parser.error("--approve-router requires --router-model, --extract-model or --embedding-model")
    return provider, extractor, embedder


def run_extraction(store, extractor, draft_id, units, targets):
    """Background AI extraction for one draft. Never raises; the draft records the outcome."""
    from legal_ai.extraction.llm_norms import extract
    try:
        claims, evidence, reports, errors = extract(units, targets, extractor,
                                                    progress=lambda done, total: store.extraction_progress(draft_id, done, total))
        store.finish_extraction(draft_id, claims, evidence, reports, errors)
    except Exception:  # Keep the server alive and unblock review with rule results.
        store.fail_extraction(draft_id, "internal_error")
