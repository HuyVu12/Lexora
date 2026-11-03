"""Local CLI. Network access only via the explicit snapshot subcommand."""

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
