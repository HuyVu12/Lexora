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
                    from legal_ai.providers.claude_code import ClaudeCodeProvider
                    if args.max_calls < 1:
                        raise ValueError("--max-calls must be a positive call budget")
                    provider = ClaudeCodeProvider(args.model, args.effort, args.max_calls, approved=args.approve_claude)
                    kb_run.start(args.bundle, args.output, args.model, args.effort)
                    counts = kb_run.extract(units, provider, args.output, log=lambda line: print(line, flush=True))
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
        elif args.command == "run-retrieval":
            from legal_ai.evaluation.retrieval_run import run
            print(json.dumps(run(args.bundle, args.questions, args.condition, args.shared, args.output), ensure_ascii=False, indent=2))
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
