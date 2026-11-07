"""Strict v1 pilot contracts. No implicit coercion or inferred legal status."""

from datetime import date, datetime
import re

from legal_ai.common.io import digest, canonical

VERSION = "1.0.0-pilot"
NORMALIZATION_VERSION = "nfc-newlines-v1"
MODALITIES = {"obligation", "permission", "prohibition", "entitlement", "definition", "procedure", "unknown"}
# Exact source words (casefolded) accepted as evidence for a modality. A cue is
# evidence of wording only; reviewers still confirm the legal reading.
MODALITY_CUES = {"obligation": {"phải", "có trách nhiệm", "có nghĩa vụ", "bắt buộc", "buộc"},
                 "prohibition": {"không được", "nghiêm cấm", "cấm", "bị cấm"},
                 "entitlement": {"có quyền", "được quyền"},
                 "permission": {"có thể", "được"}}


def text_hash(text):
    return digest(canonical({"normalization_version": NORMALIZATION_VERSION, "text": text}))


def unit_version(unit):
    return digest(canonical([unit["document_version_id"], unit["unit_id"], unit["normalized_sha256"]]))


def _string(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name}: expected nonempty string")


def _hash(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name}: expected SHA-256")


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name}: expected nonnegative integer")


def _keys(row, required, optional=()):
    if not isinstance(row, dict):
        raise ValueError("expected object")
    missing, extra = set(required) - row.keys(), row.keys() - set(required) - set(optional)
    if missing or extra:
        raise ValueError(f"fields: missing={sorted(missing)} extra={sorted(extra)}")


def validate_document(row):
    _keys(row, ("schema_version", "document_id", "document_version_id", "snapshot_id", "title", "source_url", "accessed_at", "source_sha256", "effective_from", "effective_to", "legal_status", "synthetic"))
    for key in ("document_id", "document_version_id", "snapshot_id", "title", "source_url"):
        _string(row[key], key)
    if row["schema_version"] != VERSION or type(row["synthetic"]) is not bool:
        raise ValueError("invalid version or synthetic flag")
    _hash(row["source_sha256"], "source_sha256")
    _string(row["accessed_at"], "accessed_at")
    stamp = datetime.fromisoformat(row["accessed_at"].replace("Z", "+00:00"))
    if stamp.utcoffset() is None:
        raise ValueError("accessed_at must include timezone")
    for key in ("effective_from", "effective_to"):
        if row[key] is not None:
            _string(row[key], key)
            date.fromisoformat(row[key])
    if row["effective_from"] and row["effective_to"] and row["effective_to"] < row["effective_from"]:
        raise ValueError("effective date range reversed")
    if row["legal_status"] != "unknown":
        raise ValueError("pilot accepts unknown legal status only; verified status needs provenance extension")
    return row


def validate_unit(row):
    _keys(row, ("schema_version", "unit_id", "unit_version_id", "document_id", "document_version_id", "parent_id", "unit_type", "label", "text", "normalized_sha256", "source_start", "source_end", "source_locator"))
    if row["schema_version"] != VERSION or row["unit_type"] not in {"chapter", "section", "article", "clause", "point"}:
        raise ValueError("invalid schema version or unit type")
    for key in ("unit_id", "unit_version_id", "document_id", "document_version_id", "label", "text", "source_locator"):
        _string(row[key], key)
    if row["parent_id"] is not None:
        _string(row["parent_id"], "parent_id")
    for key in ("source_start", "source_end"):
        _integer(row[key], key)
    if row["source_end"] - row["source_start"] != len(row["text"]):
        raise ValueError("source span length mismatch")
    if row["normalized_sha256"] != text_hash(row["text"]) or row["unit_version_id"] != unit_version(row):
        raise ValueError("unit hash/version mismatch")
    return row


def validate_evidence(row):
    _keys(row, ("evidence_id", "document_id", "unit_id", "unit_version_id", "quote", "start", "end", "normalized_sha256"))
    for key in ("evidence_id", "document_id", "unit_id", "unit_version_id", "quote"):
        _string(row[key], key)
    _hash(row["normalized_sha256"], "normalized_sha256")
    _integer(row["start"], "start")
    _integer(row["end"], "end")
    if row["end"] <= row["start"] or row["end"] - row["start"] != len(row["quote"]):
        raise ValueError("invalid evidence span")
    return row


def validate_claim(row):
    _keys(row, ("schema_version", "claim_id", "source_unit_version_ids", "modality", "slots", "evidence_ids", "extraction_run_id", "extraction_scope", "completeness"), ("modality_evidence_ids",))
    if row["schema_version"] != VERSION or row["modality"] not in MODALITIES or row["completeness"] not in {"unknown", "explicitly_complete"}:
        raise ValueError("invalid claim version/modality/completeness")
    for key in ("claim_id", "extraction_run_id", "extraction_scope"):
        _string(row[key], key)
    for key in ("source_unit_version_ids", "evidence_ids"):
        if not isinstance(row[key], list) or not row[key] or not all(isinstance(item, str) and item for item in row[key]):
            raise ValueError(f"{key}: expected nonempty string list")
        if len(set(row[key])) != len(row[key]):
            raise ValueError(f"{key}: expected nonempty unique list")
        for item in row[key]:
            _string(item, key)
    if not isinstance(row["slots"], dict) or not row["slots"]:
        raise ValueError("slots required")
    if "modality_evidence_ids" in row:
        ids = row["modality_evidence_ids"]
        if not isinstance(ids, list) or not all(isinstance(eid, str) for eid in ids) or len(ids) != len(set(ids)) or not set(ids) <= set(row["evidence_ids"]):
            raise ValueError("invalid modality evidence")
        if row["modality"] != "unknown" and not ids:
            raise ValueError("known modality requires evidence")
    allowed = {"actor", "beneficiary", "recipient", "counterparty", "action", "object", "outcome", "conditions", "exceptions", "scope", "quantities", "deadlines", "references"}
    for name, slot in row["slots"].items():
        if name not in allowed:
            raise ValueError(f"unknown slot {name}")
        _keys(slot, ("state", "text", "evidence_ids"))
        if slot["state"] not in {"present", "unknown", "not_present"} or not isinstance(slot["evidence_ids"], list):
            raise ValueError("invalid slot state/evidence IDs")
        if not all(isinstance(item, str) and item for item in slot["evidence_ids"]) or len(set(slot["evidence_ids"])) != len(slot["evidence_ids"]):
            raise ValueError("slot evidence must be unique string IDs")
        if slot["state"] == "present":
            _string(slot["text"], name)
            if not slot["evidence_ids"] or not set(slot["evidence_ids"]) <= set(row["evidence_ids"]):
                raise ValueError("present slot needs claim evidence")
        elif slot["text"] is not None or slot["evidence_ids"]:
            raise ValueError("unknown/not_present slot must have null text and no evidence")
    return row
