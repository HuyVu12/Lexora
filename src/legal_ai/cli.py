"""Local CLI. Network access only via the explicit snapshot and vbpl-fetch subcommands."""

import argparse
import json
from pathlib import Path

from legal_ai.common.io import read_jsonl, write_json, write_jsonl, digest
from legal_ai.ingestion.parser import parse
from legal_ai.ingestion.snapshot import snapshot
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_document, validate_unit, validate_evidence


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="lexora")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("snapshot", help="download an explicitly approved vbpl HTML snapshot")
    command.add_argument("url")
    command.add_argument("--document-id", required=True)
    command.add_argument("--marker", required=True)
    command.add_argument("--output", default="data/raw")
    command = commands.add_parser("parse", help="parse a UTF-8 text source, without network access")
    command.add_argument("input")
    command.add_argument("--document-id", required=True)
    command.add_argument("--output", required=True)
    command = commands.add_parser("validate", help="check a JSONL contract bundle")
    command.add_argument("bundle")
    command.add_argument("--output", required=True)
    command = commands.add_parser("build-pilot", help="build pilot from pinned local VBPL snapshots")
    command.add_argument("--config", default="configs/sources-pilot.json")
    command.add_argument("--raw-root", default="data/raw")
    command.add_argument("--output", required=True)
    command = commands.add_parser("search", help="retrieve exact source passages; no generated legal answer")
    command.add_argument("bundle")
    command.add_argument("question")
    command.add_argument("--top-k", type=int, default=5)
    command = commands.add_parser("catalog-build", help="build the local document catalog from downloaded dataset files; no network")
    command.add_argument("--raw", default="data/catalog/raw")
    command.add_argument("--output", required=True, help="new catalog file, e.g. data/catalog/catalog-v1.sqlite")
    command = commands.add_parser("catalog-search", help="search the local catalog by title or number, accents ignored; no network")
    command.add_argument("catalog")
    command.add_argument("query")
    command.add_argument("--limit", type=int, default=10)
    command.add_argument("--include-translations", action="store_true")
    command = commands.add_parser("vbpl-fetch", help="fetch ONE explicitly approved vbpl.vn document (link or ID) as an immutable snapshot")
    command.add_argument("reference", help="vbpl.vn document link or ID")
    command.add_argument("--output", default="data/raw/vbpl")
    command = commands.add_parser("corpus-export", help="write a frozen research corpus version as a contract bundle for run-retrieval")
    command.add_argument("--store", required=True, help="workspace SQLite store of the web app")
    command.add_argument("--version", required=True, help="corpus version ID (shown in the app)")
    command.add_argument("--output", required=True, help="new, empty directory")
    command = commands.add_parser("corpus-scope", help="create a research corpus from the chosen articles of pinned local vbpl.vn snapshots; no network")
    command.add_argument("--store", required=True, help="workspace SQLite store of the web app")
    command.add_argument("--config", default="configs/experiment-scope-v1.json")
    command.add_argument("--actor", required=True, help="account name recorded as the creator")
    command = commands.add_parser("kb-extract", help="DK3/DK4 knowledge base: one Claude Code model extracts norms from every sentence of a corpus bundle")
    command.add_argument("bundle", help="contract bundle written by corpus-export")
    command.add_argument("--output", required=True, help="new directory, or an earlier run of the same bundle to resume")
    command.add_argument("--model", default="claude-opus-5-5")
    command.add_argument("--effort", default="medium")
    command.add_argument("--max-calls", type=int, default=0, help="call budget of this session (required unless --dry-run)")
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the model calls")
    command.add_argument("--router-model", help="extract with one approved 9Router model instead (a MODEL_* alias from .env or a model name)")
    command.add_argument("--approve-router", action="store_true", help="explicit approval of the 9Router endpoint, model and data")
    command.add_argument("--timeout", type=int, default=300, help="seconds per 9Router call (5-600)")
    command.add_argument("--max-tokens", type=int, default=16000, help="output token limit per 9Router call, the same for every compared model")
    command.add_argument("--dry-run", action="store_true", help="only count batches and characters; no model call")
    command = commands.add_parser("kb-materialize", help="rebuild dk3/dk4 and the validation report of a knowledge-base run from raw.jsonl; offline")
    command.add_argument("run", help="knowledge-base run directory")
    command.add_argument("--bundle", help="contract bundle (default: the one recorded in the run manifest)")
    command = commands.add_parser("answer-run", help="cited answers for one retrieval run through Claude Code; resumes an earlier run")
    command.add_argument("retrieval_run", help="run directory written by run-retrieval")
    command.add_argument("--questions", required=True, help="the question file the retrieval run used")
    command.add_argument("--config", default="configs/experiments/answer.json")
    command.add_argument("--output", required=True, help="new directory, or an earlier answer run with the same inputs")
    command.add_argument("--split", choices=["dev", "held_out"], help="answer only this split")
    command.add_argument("--max-calls", type=int, required=True, help="call budget of this session")
    command.add_argument("--approve-claude", action="store_true", help="explicit approval of the model calls")
    command = commands.add_parser("answer-score", help="automatic metrics of an answer run (refusals, citations against gold units); offline")
    command.add_argument("answer_run")
    command.add_argument("--questions", required=True)
    command = commands.add_parser("answer-sheet", help="blinded CSV grading sheet pooling several answer runs, and its separate key; offline")
    command.add_argument("answer_runs", nargs="+")
    command.add_argument("--questions", required=True)
    command.add_argument("--sheet", required=True, help="CSV file to write")
    command.add_argument("--key", required=True, help="JSON key file to write; keep it away from graders")
    command = commands.add_parser("answer-grades", help="per-condition scores of a filled grading sheet; offline")
    command.add_argument("sheet")
    command.add_argument("--key", required=True)
    command.add_argument("--compare", help="a second filled sheet of the same items: report Cohen's kappa")
    command = commands.add_parser("answer-judge", help="fill a copy of a grading sheet with a Claude Code judge (supplement to people)")
    command.add_argument("sheet")
    command.add_argument("--output", required=True, help="CSV file to write")
    command.add_argument("--config", default="configs/experiments/answer.json")
    command.add_argument("--max-calls", type=int, required=True)
    command.add_argument("--approve-claude", action="store_true")
    command = commands.add_parser("preflight", help="fairness checks of DK1-DK4 retrieval (and answer) runs before reporting RQ3; offline")
    command.add_argument("--retrieval", nargs="+", required=True, help="retrieval run directories, one per condition")
    command.add_argument("--answers", nargs="*", default=[], help="answer run directories made from those retrieval runs")
    command.add_argument("--output", help="write the report as JSON here")
    command = commands.add_parser("kb-compare", help="re-validate knowledge-base runs with the current validator and write a side-by-side report; offline")
    command.add_argument("runs", nargs="*", help="run directories (default: every knowledge-base run under experiments/runs)")
    command.add_argument("--json", default="docs/results/extraction-models.json")
    command.add_argument("--markdown", default="docs/results/extraction-models.md")
    command = commands.add_parser("kb-inject", help="RQ2: plant errors of each type in DK4 claims and measure what the validator catches; offline")
    command.add_argument("run", help="knowledge-base run directory")
    command.add_argument("--output", required=True, help="new, empty directory")
    command.add_argument("--per-type", type=int, default=30)
    command.add_argument("--seed", default="lexora-inject-v1")
    command = commands.add_parser("gold-template", help="RQ1: empty extraction gold rows for every sentence of the chosen articles; offline")
    command.add_argument("bundle")
    command.add_argument("--output", required=True, help="JSONL file to write")
    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument("--article", action="append", help="article unit ID, e.g. 45-2019-qh14/chapter-iii/section-1/article-24 (repeatable)")
    group.add_argument("--sample", type=int, help="seeded sample of this many articles, spread over documents")
    command.add_argument("--seed", default="lexora-gold-v1")
    command = commands.add_parser("gold-check", help="RQ1: check a filled gold file (exact quotes, offsets); offline")
    command.add_argument("gold")
    command.add_argument("--bundle", required=True)
    command = commands.add_parser("gold-agreement", help="RQ1: agreement of two annotators on the same gold template; offline")
    command.add_argument("first")
    command.add_argument("second")
    command = commands.add_parser("gold-score", help="RQ1: P/R/F1 of the rule baseline or a knowledge-base run against the gold file; offline")
    command.add_argument("gold")
    command.add_argument("--bundle", required=True)
    command.add_argument("--predictions", required=True, help="'rules', or a dk3.jsonl / dk4.jsonl of a knowledge-base run")
    command = commands.add_parser("run-retrieval", help="DK1/DK2 retrieval run with Recall@K into a new run directory; no network")
    command.add_argument("bundle")
    command.add_argument("--condition", required=True, help="configs/experiments/dk1.json or dk2.json")
    command.add_argument("--questions", default="tests/fixtures/pilot-questions.json")
    command.add_argument("--shared", default="configs/pilot.json")
    command.add_argument("--output", required=True, help="new, empty directory, e.g. experiments/runs/<run-id>")
    command = commands.add_parser("graph-build", help="build a local knowledge graph and evidence viewer")
    command.add_argument("bundle")
    command.add_argument("--output", required=True)
    command.add_argument("--config", default="configs/knowledge-graph.json")
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            print(json.dumps(snapshot(args.url, args.output, args.document_id, args.marker), ensure_ascii=False, indent=2))
        elif args.command == "build-pilot":
            from legal_ai.ingestion.pilot import build_pilot
            print(json.dumps(build_pilot(args.config, args.raw_root, args.output), ensure_ascii=False, indent=2))
        elif args.command == "catalog-build":
            from legal_ai.ingestion.catalog import build_catalog
            print(json.dumps(build_catalog(args.raw, args.output), ensure_ascii=False, indent=2))
        elif args.command == "catalog-search":
            from legal_ai.ingestion.catalog import Catalog
            print(json.dumps(Catalog(args.catalog).search(args.query, args.limit, args.include_translations), ensure_ascii=False, indent=2))
        elif args.command == "vbpl-fetch":
            from legal_ai.ingestion.vbpl_api import fetch_document
            print(json.dumps(fetch_document(args.reference, args.output), ensure_ascii=False, indent=2))
        elif args.command == "corpus-export":
            from legal_ai.research.corpus import CorpusStore
            print(json.dumps(CorpusStore(args.store).export_version(args.version, args.output), ensure_ascii=False, indent=2))
        elif args.command == "corpus-scope":
            from legal_ai.research.corpus import CorpusStore
            from legal_ai.research.scope import build_scope
            corpus = build_scope(CorpusStore(args.store), args.config, args.actor)
            print(json.dumps({"corpus_id": corpus["id"], "name": corpus["name"],
                              "documents": [{"document_id": d["document_id"], "articles": d["article_count"], "audit": d["audit_count"]} for d in corpus["documents"]]},
                             ensure_ascii=False, indent=2))
        elif args.command in ("kb-extract", "kb-materialize"):
            from legal_ai.common.io import read_jsonl
            from legal_ai.evaluation import kb_run
            if args.command == "kb-materialize":
                bundle = args.bundle or json.loads((Path(args.run) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
                print(json.dumps(kb_run.materialize(read_jsonl(Path(bundle) / "units.jsonl"), args.run), ensure_ascii=False, indent=2))
            else:
                units = read_jsonl(Path(args.bundle) / "units.jsonl")
                if args.dry_run:
                    print(json.dumps(kb_run.estimate(units), ensure_ascii=False, indent=2))
                else:
                    if args.max_calls < 1:
                        raise ValueError("--max-calls must be a positive call budget")
                    if args.router_model:
                        from legal_ai.providers.router import RouterProvider, read_settings
                        settings = read_settings(Path.cwd() / ".env")
                        name = settings[args.router_model] if args.router_model.startswith("MODEL_") and settings.get(args.router_model) else args.router_model
                        provider = RouterProvider(settings, model=name, approved_route=args.approve_router, max_calls=args.max_calls, timeout=args.timeout)
                        kb_run.start(args.bundle, args.output, name, "temperature-0", provider="9router", max_tokens=args.max_tokens)
                    else:
                        from legal_ai.providers.claude_code import ClaudeCodeProvider
                        provider = ClaudeCodeProvider(args.model, args.effort, args.max_calls, approved=args.approve_claude)
                        kb_run.start(args.bundle, args.output, args.model, args.effort)
                    counts = kb_run.extract(units, provider, args.output, log=lambda line: print(line, flush=True), max_tokens=args.max_tokens)
                    print(json.dumps({"calls": counts, "report": kb_run.materialize(units, args.output)}, ensure_ascii=False, indent=2))
        elif args.command in ("answer-run", "answer-judge"):
            from legal_ai.providers.claude_code import ClaudeCodeProvider
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            log = lambda line: print(line, flush=True)
            if args.command == "answer-run":
                from legal_ai.evaluation.answer_run import run as answer_run
                provider = ClaudeCodeProvider(config["model"], config["effort"], args.max_calls, approved=args.approve_claude)
                print(json.dumps(answer_run(args.retrieval_run, args.questions, args.config, provider, args.output, split=args.split, log=log), indent=2))
            else:
                from legal_ai.evaluation.answer_grading import judge_sheet
                provider = ClaudeCodeProvider(config["judge_model"], config["judge_effort"], args.max_calls, approved=args.approve_claude)
                print(json.dumps(judge_sheet(args.sheet, provider, args.output, log=log), indent=2))
        elif args.command == "answer-score":
            from legal_ai.evaluation.answer_run import score
            print(json.dumps(score(args.answer_run, args.questions), ensure_ascii=False, indent=2))
        elif args.command == "answer-sheet":
            from legal_ai.evaluation.answer_grading import make_sheet
            print(json.dumps(make_sheet(args.answer_runs, args.questions, args.sheet, args.key), indent=2))
        elif args.command == "answer-grades":
            from legal_ai.evaluation.answer_grading import agreement, score_sheet
            report = score_sheet(args.sheet, args.key)
            if args.compare:
                report["agreement"] = agreement(args.sheet, args.compare)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.command == "preflight":
            from legal_ai.common.io import write_json
            from legal_ai.evaluation.preflight import check
            report = check(args.retrieval, args.answers)
            if args.output:
                write_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["status"] == "fail":
                return 1
        elif args.command == "kb-compare":
            from legal_ai.evaluation.kb_compare import compare, kb_runs
            runs = args.runs or kb_runs("experiments/runs")
            summaries = compare(runs, args.json, args.markdown)
            print(json.dumps([{k: s[k] for k in ("model", "batches_ok", "batches_attempted", "dk3_claims", "dk4_claims", "rejected")} for s in summaries],
                             ensure_ascii=False, indent=2))
        elif args.command == "kb-inject":
            from legal_ai.common.io import read_jsonl
            from legal_ai.evaluation.error_injection import run as inject_run
            bundle = json.loads((Path(args.run) / "manifest.json").read_text(encoding="utf-8"))["bundle"]
            print(json.dumps(inject_run(args.run, read_jsonl(Path(bundle) / "units.jsonl"), args.output, args.per_type, args.seed), ensure_ascii=False, indent=2))
        elif args.command.startswith("gold-"):
            from legal_ai.common.io import read_jsonl, write_jsonl
            from legal_ai.evaluation import extraction_gold as gold
            if args.command == "gold-agreement":
                print(json.dumps(gold.agreement(read_jsonl(args.first), read_jsonl(args.second)), ensure_ascii=False, indent=2))
            else:
                units = read_jsonl(Path(args.bundle) / "units.jsonl")
                if args.command == "gold-template":
                    articles = args.article or gold.sample_articles(units, args.sample, args.seed)
                    rows = gold.template(units, articles)
                    write_jsonl(args.output, rows)
                    print(json.dumps({"articles": articles, "sentences": len(rows)}, ensure_ascii=False, indent=2))
                else:
                    rows = read_jsonl(args.gold)
                    problems = gold.check(rows, units)
                    if args.command == "gold-check" or problems:
                        print(json.dumps({"rows": len(rows), "problems": problems}, ensure_ascii=False, indent=2))
                        if problems:
                            raise ValueError(f"{len(problems)} problems in the gold file")
                    else:
                        predicted = gold.rule_predictions(units, rows) if args.predictions == "rules" else gold.claim_predictions(read_jsonl(args.predictions), rows)
                        print(json.dumps(gold.score(rows, predicted), ensure_ascii=False, indent=2))
        elif args.command == "run-retrieval":
            from legal_ai.evaluation.retrieval_run import run
            shared = json.loads(Path(args.shared).read_text(encoding="utf-8"))
            embedder = None
            if shared["retrieval"].get("method") in ("dense", "hybrid"):
                from legal_ai.retrieval.embeddings import LocalEmbedder
                model = shared["embedding_model"]
                embedder = LocalEmbedder(model["path"], model["name"], model["revision"], model.get("max_seq_length", 1024))
            print(json.dumps(run(args.bundle, args.questions, args.condition, args.shared, args.output, embedder), ensure_ascii=False, indent=2))
        elif args.command == "graph-build":
            from legal_ai.kb.graph import GRAPH_VERSION, build_graph
            config = json.loads(Path(args.config).read_text(encoding="utf-8"))
            if config.get("graph_version") != GRAPH_VERSION:
                raise ValueError("graph config version does not match runtime; review migration before rebuilding")
            print(json.dumps(build_graph(args.bundle, args.output, config["source_aliases"], config["include_review_candidates"], config.get("extraction_mode", "unit-cues")), ensure_ascii=False, indent=2))
        elif args.command == "search":
            from legal_ai.retrieval.bm25 import search
            from legal_ai.validation.bundle import validate_bundle
            folder = Path(args.bundle)
            documents, units, evidence, claims = [read_jsonl(folder / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")]
            validate_bundle(documents, units, evidence, claims)
            results = search(units, args.question, args.top_k)
            print(json.dumps({"mode": "lexical_source_retrieval", "legal_status": "unknown", "generated_answer": False, "results": results}, ensure_ascii=False, indent=2))
        elif args.command == "parse":
            raw = Path(args.input).read_bytes().decode("utf-8")
            normalized = normalize(raw, Path(args.input).as_posix())
            version = digest(normalized["normalized_sha256"])
            result = parse(normalized, args.document_id, version)
            for unit in result["units"]:
                validate_unit(unit)
            folder = Path(args.output)
            write_json(folder / "normalized.json", normalized)
            write_jsonl(folder / "units.jsonl", result.pop("units"))
            write_json(folder / "parser-report.json", result)
            print(json.dumps({"output": str(folder), "audit_count": len(result["audit"]), "schema_version": VERSION}))
        else:
            folder = Path(args.bundle)
            documents = [validate_document(row) for row in read_jsonl(folder / "documents.jsonl")]
            units = [validate_unit(row) for row in read_jsonl(folder / "units.jsonl")]
            evidence = [validate_evidence(row) for row in read_jsonl(folder / "evidence.jsonl")]
            claims = read_jsonl(folder / "claims.jsonl")
            from legal_ai.validation.bundle import validate_bundle
            results = validate_bundle(documents, units, evidence, claims)
            write_jsonl(args.output, results)
            print(json.dumps({state: sum(row["decision"] == state for row in results) for state in ("accepted", "rejected", "needs_review")}))
            if any(row["decision"] == "rejected" for row in results):
                return 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
