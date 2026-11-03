"""Rebuild the explicitly synthetic contract bundle. No network or model."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.io import digest, write_jsonl
from legal_ai.ingestion.parser import parse
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import VERSION, validate_document, validate_claim
from legal_ai.validation.evidence import align_quote


def build(output):
    source = Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic-law.txt"
    data = source.read_bytes()
    normalized = normalize(data.decode("utf-8"), "tests/fixtures/synthetic-law.txt")
    version = normalized["normalized_sha256"]
    document = {"schema_version": VERSION, "document_id": "synthetic", "document_version_id": version, "snapshot_id": digest(data), "title": "SYNTHETIC — NOT REAL LAW", "source_url": "fixture://synthetic-law", "accessed_at": "2026-11-02T00:00:00Z", "source_sha256": digest(data), "effective_from": None, "effective_to": None, "legal_status": "unknown", "synthetic": True}
    units = parse(normalized, "synthetic", version)["units"]
    unit = next(unit for unit in units if unit["unit_id"].endswith("article-1/clause-1"))
    quotes = {"actor": "Chủ thể B", "action": "thực hiện C", "conditions": "trừ trường hợp D", "deadlines": "7 ngày"}
    evidence = [align_quote(unit, quote) for quote in quotes.values()]
    claim = {"schema_version": VERSION, "claim_id": "synthetic-claim-1", "source_unit_version_ids": [unit["unit_version_id"]], "modality": "obligation", "slots": {}, "evidence_ids": [row["evidence_id"] for row in evidence], "extraction_run_id": "synthetic-manual-fixture-v1", "extraction_scope": "synthetic clause only; parent condition intentionally unknown", "completeness": "unknown"}
    for (slot, quote), item in zip(quotes.items(), evidence):
        # The exception is deliberately stored as an exception, not a condition.
        claim["slots"]["exceptions" if slot == "conditions" else slot] = {"state": "present", "text": quote, "evidence_ids": [item["evidence_id"]]}
    claim["slots"]["conditions"] = {"state": "unknown", "text": None, "evidence_ids": []}
    validate_document(document)
    validate_claim(claim)
    output = Path(output)
    for name, rows in (("documents", [document]), ("units", units), ("evidence", evidence), ("claims", [claim])):
        write_jsonl(output / f"{name}.jsonl", rows)
    return document, units, evidence, claim


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "tests/fixtures/contract-v1")
