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
