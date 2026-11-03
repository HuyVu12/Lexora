"""Validate schema, hierarchy and evidence even when a bundle has no claims."""

from legal_ai.schemas.contract import validate_document, validate_unit, validate_evidence
from legal_ai.validation.evidence import check_evidence, validate_record


def validate_bundle(documents, units, evidence, claims):
    for validator, rows in ((validate_document, documents), (validate_unit, units), (validate_evidence, evidence)):
        for row in rows:
            validator(row)
    for rows, field in ((documents, "document_id"), (units, "unit_id"), (units, "unit_version_id"), (evidence, "evidence_id"), (claims, "claim_id")):
        if len({row[field] for row in rows}) != len(rows):
            raise ValueError(f"duplicate {field}")
    by_doc = {row["document_id"]: row for row in documents}
    by_unit = {row["unit_id"]: row for row in units}
    parents = {"chapter": {None}, "section": {None, "chapter"}, "article": {None, "chapter", "section"}, "clause": {"article"}, "point": {"clause"}}
    for unit in units:
        doc = by_doc.get(unit["document_id"])
        parent = by_unit.get(unit["parent_id"])
        if doc is None or unit["document_version_id"] != doc["document_version_id"]:
            raise ValueError("unit document/version missing or mismatched")
        if unit["parent_id"] and (parent is None or parent["document_id"] != unit["document_id"] or parent["document_version_id"] != unit["document_version_id"]):
            raise ValueError("parent missing or outside document/version")
        if (parent["unit_type"] if parent else None) not in parents[unit["unit_type"]]:
            raise ValueError("invalid hierarchy")
        visited, current = set(), unit
        while current:
            if current["unit_id"] in visited:
                raise ValueError("parent cycle")
            visited.add(current["unit_id"])
            current = by_unit.get(current["parent_id"])
    for row in evidence:
        reasons = check_evidence(row, units)
        if reasons:
            raise ValueError("invalid bundle evidence: " + ",".join(reasons))
    return [validate_record(row, evidence, units) for row in claims]
