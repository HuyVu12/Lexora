"""Build a scoped or whole-document corpus from pinned local snapshots. No network requests.

Each source lists `article_ids`, or `"all"` to take every article the parser found in the snapshot.
"""

import json
from pathlib import Path

from legal_ai.common.io import digest, write_json, write_jsonl
from legal_ai.ingestion.parser import parse
from legal_ai.ingestion.vbpl_html import legal_html, extract_paragraphs
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_document, validate_unit
from legal_ai.validation.evidence import align_quote


def build_pilot(config_path, raw_root, output):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty: use a new build directory")
    documents, units, evidence, reports = [], [], [], []
    for source in config["sources"]:
        folder = Path(raw_root) / source["document_id"] / source["snapshot_sha256"]
        data = (folder / "snapshot.html").read_bytes()
        meta = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if digest(data) != source["snapshot_sha256"] or meta["source_sha256"] != digest(data) or meta["source_url"] != source["url"]:
            raise ValueError("snapshot/manifest/config mismatch")
        body = legal_html(data.decode(meta["charset"]))
        extracted = extract_paragraphs(body)
        locator = f"{source['document_id']}/source.txt"
        normalized = normalize(extracted["text"], locator)
        version = normalized["normalized_sha256"]
        parsed = parse(normalized, source["document_id"], version)
        by_id = {unit["unit_id"]: unit for unit in parsed["units"]}
        if source["article_ids"] == "all":
            targets = {uid for uid, unit in by_id.items() if unit["unit_type"] == "article"}
        else:
            targets = set(source["article_ids"])
        if not targets or not targets <= by_id.keys():
            raise ValueError("configured article missing from snapshot")
        selected = {uid for uid in by_id if any(uid == article or uid.startswith(article + "/") for article in targets)}
        target_ids = set(selected)
        for uid in list(selected):
            current = by_id[uid]
            while current["parent_id"]:
                selected.add(current["parent_id"])
                current = by_id[current["parent_id"]]
        document = {"schema_version": VERSION, "document_id": source["document_id"], "document_version_id": version, "snapshot_id": meta["source_sha256"], "title": source["title"], "source_url": source["url"], "accessed_at": meta["accessed_at"], "source_sha256": meta["source_sha256"], "effective_from": None, "effective_to": None, "legal_status": "unknown", "synthetic": False}
        documents.append(validate_document(document))
        for unit in parsed["units"]:
            if unit["unit_id"] in selected:
                units.append(validate_unit(unit))
                if unit["unit_id"] in target_ids:
                    evidence.append(align_quote(unit, unit["text"]))
        scoped_units = [by_id[uid] for uid in target_ids]
        pilot_audit = [item for item in parsed["audit"] if any(unit["source_start"] <= item["offset"] < unit["source_end"] for unit in scoped_units)]
        report = {"document_id": source["document_id"], "target_unit_ids": sorted(target_ids), "context_unit_ids": sorted(selected - target_ids), "whole_document_unit_count": len(parsed["units"]), "whole_document_audit": parsed["audit"], "pilot_audit": pilot_audit, "unassigned_characters": len(parsed["unassigned_text"]), "manual_review": "required"}
        reports.append(report)
        write_json(output / source["document_id"] / "normalized.json", normalized)
        write_json(output / source["document_id"] / "paragraphs.json", extracted["paragraphs"])
        path = output / source["document_id"] / "content.html"
        path.write_text(body, encoding="utf-8")
        (path.parent / "source.txt").write_text(extracted["text"], encoding="utf-8")
    write_jsonl(output / "documents.jsonl", documents)
    write_jsonl(output / "units.jsonl", units)
    write_jsonl(output / "evidence.jsonl", evidence)
    write_jsonl(output / "claims.jsonl", [])
    write_json(output / "parser-report.json", reports)
    from legal_ai.validation.bundle import validate_bundle
    validate_bundle(documents, units, evidence, [])
    artifact_files = sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file())
    hashes = {name: digest((output / name).read_bytes()) for name in artifact_files}
    parent_ids = {unit["parent_id"] for unit in units}
    manifest = {"schema_version": VERSION, "topic": config["topic"], "synthetic": False, "status": "prepared_for_review", "document_count": len(documents), "target_unit_count": sum(len(r["target_unit_ids"]) for r in reports), "context_unit_count": sum(len(r["context_unit_ids"]) for r in reports), "leaf_unit_count": sum(unit["unit_id"] not in parent_ids for unit in units), "claim_count": 0, "legal_status": "unknown", "config_sha256": digest(Path(config_path).read_bytes()), "artifact_hashes": hashes, "limitations": ["Not a consolidated/current-law corpus", "No LLM extraction or generation", "Whole-document parser audits remain; only scoped pilot prepared" if any(s["article_ids"] != "all" for s in config["sources"]) else "Whole-document parser audits remain and need human review", "Requires human parser and metadata review"]}
    write_json(output / "manifest.json", manifest)
    return manifest
