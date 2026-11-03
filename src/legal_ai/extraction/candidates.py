"""Review candidates only: unit-level normative cues, never atomic legal truth."""

import re

from legal_ai.common.io import digest, canonical
from legal_ai.schemas.contract import VERSION
from legal_ai.validation.evidence import align_quote

CUE = re.compile(r"\b(?:phải|không được|có quyền|có thể|không áp dụng|không quá)\b", re.IGNORECASE)


def rule_candidates(units):
    parents = {unit["parent_id"] for unit in units}
    claims, evidence = [], []
    for unit in units:
        if unit["unit_id"] in parents or not CUE.search(unit["text"]):
            continue
        anchor = align_quote(unit, unit["text"])
        evidence.append(anchor)
        unknown = {"state": "unknown", "text": None, "evidence_ids": []}
        claims.append({"schema_version": VERSION, "claim_id": digest(canonical(["norm-candidate-v1", unit["unit_version_id"]])), "source_unit_version_ids": [unit["unit_version_id"]], "modality": "unknown", "slots": {"action": {"state": "present", "text": unit["text"], "evidence_ids": [anchor["evidence_id"]]}, "actor": dict(unknown), "conditions": dict(unknown), "exceptions": dict(unknown)}, "evidence_ids": [anchor["evidence_id"]], "extraction_run_id": "norm-candidate-v1", "extraction_scope": "own unit only; cue candidate, not atomic claim extraction; parent qualifiers not extracted", "completeness": "unknown"})
    return claims, evidence
