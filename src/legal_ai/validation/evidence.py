"""Technical integrity checks; accepted does not assert legal correctness."""

from legal_ai.common.io import digest, canonical
from legal_ai.schemas.contract import MODALITY_CUES, VERSION, validate_claim, validate_evidence, validate_unit


def align_quote(unit, quote):
    validate_unit(unit)
    if not isinstance(quote, str) or not quote:
        raise ValueError("quote must be nonempty")
    matches, start = [], 0
    while (start := unit["text"].find(quote, start)) >= 0:
        matches.append(start)
        start += 1
    if len(matches) != 1:
        raise ValueError("quote_missing" if not matches else "quote_ambiguous")
    start = matches[0]
    row = {"evidence_id": digest(canonical([unit["unit_version_id"], start, quote])), "document_id": unit["document_id"], "unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"], "quote": quote, "start": start, "end": start + len(quote), "normalized_sha256": unit["normalized_sha256"]}
    return validate_evidence(row)


def check_evidence(evidence, units):
    try:
        validate_evidence(evidence)
    except (ValueError, TypeError) as exc:
        return [f"evidence_schema:{exc}"]
    matches = [u for u in units if u.get("unit_version_id") == evidence["unit_version_id"]]
    if len(matches) != 1:
        return ["missing_or_duplicate_unit_version"]
    unit = matches[0]
    try:
        validate_unit(unit)
    except (ValueError, TypeError) as exc:
        return [f"unit_integrity:{exc}"]
    errors = []
    for key in ("document_id", "unit_id", "normalized_sha256"):
        if evidence[key] != unit[key]:
            errors.append(f"evidence_{key}_mismatch")
    if evidence["end"] > len(unit["text"]) or unit["text"][evidence["start"]:evidence["end"]] != evidence["quote"]:
        errors.append("quote_offset_mismatch")
    if evidence["evidence_id"] != digest(canonical([unit["unit_version_id"], evidence["start"], evidence["quote"]])):
        errors.append("evidence_id_mismatch")
    return errors


def validate_record(claim, evidence, units):
    reasons = []
    try:
        validate_claim(claim)
    except (ValueError, TypeError) as exc:
        return {"claim_id": claim.get("claim_id") if isinstance(claim, dict) else None, "schema_version": VERSION, "decision": "rejected", "reasons": [f"claim_schema:{exc}"]}
    by_id = {}
    for row in evidence:
        key = row.get("evidence_id")
        if key in by_id:
            reasons.append("duplicate_evidence_id")
        by_id[key] = row
    for key in claim["evidence_ids"]:
        if key not in by_id:
            reasons.append("missing_evidence")
        else:
            row = by_id[key]
            reasons.extend(check_evidence(row, units))
            if row.get("unit_version_id") not in claim["source_unit_version_ids"]:
                reasons.append("evidence_outside_claim_sources")
    known = {unit.get("unit_version_id") for unit in units}
    if not set(claim["source_unit_version_ids"]) <= known:
        reasons.append("missing_claim_source")
    for slot in claim["slots"].values():
        if slot["state"] == "present" and not any(slot["text"] in by_id[key].get("quote", "") for key in slot["evidence_ids"] if key in by_id):
            reasons.append("slot_text_not_in_evidence")
    if claim.get("modality_evidence_ids"):
        expected = MODALITY_CUES.get(claim["modality"])
        if expected is None or any(by_id.get(eid, {}).get("quote", "").casefold() not in expected for eid in claim["modality_evidence_ids"]):
            reasons.append("modality_evidence_mismatch")
    review = claim["modality"] == "unknown" or claim["completeness"] == "unknown" or any(slot["state"] == "unknown" for slot in claim["slots"].values())
    decision = "rejected" if reasons else "needs_review" if review else "accepted"
    return {"claim_id": claim["claim_id"], "schema_version": VERSION, "decision": decision, "reasons": sorted(set(reasons)) or (["semantic_review_required"] if review else [])}
