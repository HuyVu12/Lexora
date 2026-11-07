"""Automatic validation of LLM knowledge-base claims (`kb-validator-v3`): what turns DK3 into DK4.

A DK3 claim is one norm the model reported for one source sentence, with the model's slot strings as given.
Each check records `pass`, `fail` or `not_applicable` with reason codes, so "not checked" never reads as "passed":

- V1 schema: modality in the enum, slot values strings or null within length limits, and at least one content slot
  (action, object, conditions, exceptions, quantities, deadlines or outcome; a party alone is not a norm). Points of
  a list often carry only an object, an amount or a condition while the action sits in the lead text ("Ít nhất 120
  ngày đối với ...", "Bị quấy rối tình dục tại nơi làm việc"), so the action itself is not required.
- V2 integrity: the source unit exists in this corpus version and the sentence span is inside it.
- V3 evidence: every non-null slot is an exact quote of its source sentence (case folded only when lengths match).
- V4 modality: a cue word the model gives must be an exact quote of the sentence (`fail` otherwise: made up) and
  must not be a cue of only other modalities (`fail`: contradicting). A verbatim cue outside the cue lexicon
  ("chỉ được", "không phải") cannot be checked and is `unverified`. Statutes often state a norm without a cue in the
  sentence itself (points of a list whose lead carries the sanction, "... thì áp dụng ..."); a modality given
  without any cue cannot be checked and is recorded as `unverified`, which is not a failure (design 7.2: what
  cannot be decided is not rejected automatically). Reports count `unverified` separately.
- V7 duplicate: the same unit, modality and slot strings as an earlier claim (kept once, later copies flagged).

A claim is accepted when no check fails (V4 may be `unverified`) and it is not a duplicate. Accepted means it passed these checks, not that
the norm is legally right: a verbatim quote can still be read the wrong way, which the gold set has to measure.
"""

from legal_ai.extraction.llm_norms import LLM_SLOTS, MODALITIES, locate
from legal_ai.schemas.contract import MODALITY_CUES

VALIDATOR_VERSION = "kb-validator-v3"
CONTENT_SLOTS = ("action", "object", "conditions", "exceptions", "quantities", "deadlines", "outcome")
CHECKS = ("V1_schema", "V2_integrity", "V3_evidence", "V4_modality", "V7_duplicate")
MAX_SLOT_CHARS = 1000


def _schema(claim):
    reasons = []
    if claim.get("modality") not in MODALITIES:
        reasons.append("modality_not_in_enum")
    slots = claim.get("slots")
    if not isinstance(slots, dict) or set(slots) - set(LLM_SLOTS):
        return ["slots_malformed"] + reasons
    for name, value in slots.items():
        if value is not None and (not isinstance(value, str) or len(value) > MAX_SLOT_CHARS):
            reasons.append(f"{name}_not_text")
    if not any(isinstance(slots.get(name), str) and slots[name].strip() for name in CONTENT_SLOTS):
        reasons.append("content_missing")
    cue = claim.get("modality_cue")
    if cue is not None and not isinstance(cue, str):
        reasons.append("modality_cue_not_text")
    return reasons


def _integrity(claim, units):
    unit = units.get(claim.get("unit_id"))
    if unit is None:
        return ["unit_unknown"], None
    if unit["unit_version_id"] != claim.get("unit_version_id"):
        return ["unit_version_mismatch"], None
    sentence = claim.get("sentence") or {}
    start, end = sentence.get("start"), sentence.get("end")
    if type(start) is not int or type(end) is not int or not unit["source_start"] <= start < end <= unit["source_end"]:
        return ["sentence_outside_unit"], None
    return [], unit


def _local(unit, claim):
    return claim["sentence"]["start"] - unit["source_start"], claim["sentence"]["end"] - unit["source_start"]


def evidence_spans(claim, unit):
    """Document offsets of every non-null slot that is an exact quote of the sentence, and the slots that are not."""
    start, end = _local(unit, claim)
    spans, missing = {}, []
    for name, value in sorted((claim.get("slots") or {}).items()):
        if value in (None, ""):
            continue
        found = locate(unit["text"], start, end, value)
        if found is None:
            missing.append(name)
        else:
            spans[name] = [unit["source_start"] + found[0], unit["source_start"] + found[1]]
    return spans, missing


def _modality(claim, unit):
    """(cue offsets or None, problems, verified) for the claim's modality."""
    if claim.get("modality") == "unknown":
        return None, [], False
    if claim.get("modality_cue") in (None, ""):
        return None, [], False
    start, end = _local(unit, claim)
    cue = locate(unit["text"], start, end, claim.get("modality_cue"))
    if cue is None:
        return None, ["modality_cue_not_verbatim"], False
    word = unit["text"][cue[0]:cue[1]].casefold()
    if word not in MODALITY_CUES.get(claim.get("modality"), set()):
        if any(word in cues for cues in MODALITY_CUES.values()):
            return None, ["modality_cue_mismatch"], False
        return None, [], False  # A real word of the sentence that the lexicon does not know: unverifiable.
    return [unit["source_start"] + cue[0], unit["source_start"] + cue[1]], [], True


def _duplicate_key(claim):
    slots = claim.get("slots") or {}
    return (claim.get("unit_id"), claim.get("modality"), tuple((name, " ".join(str(slots.get(name) or "").split()).casefold()) for name in LLM_SLOTS))


def validate(claims, units):
    """One result per claim, in input order: {claim_id, checks, reasons, decision, evidence}."""
    by_id = {unit["unit_id"]: unit for unit in units}
    seen, results = {}, []
    for claim in claims:
        checks, reasons, evidence = {}, [], {}
        schema = _schema(claim)
        checks["V1_schema"] = "fail" if schema else "pass"
        reasons += schema
        integrity, unit = _integrity(claim, by_id)
        checks["V2_integrity"] = "fail" if integrity else "pass"
        reasons += integrity
        if unit is None or "slots_malformed" in schema:
            checks["V3_evidence"] = checks["V4_modality"] = "not_applicable"
        else:
            spans, missing = evidence_spans(claim, unit)
            checks["V3_evidence"] = "fail" if missing else "pass"
            reasons += [f"{name}_not_verbatim" for name in missing]
            cue, problem, verified = _modality(claim, unit)
            if problem:
                checks["V4_modality"] = "fail"
            elif verified:
                checks["V4_modality"] = "pass"
            else:
                checks["V4_modality"] = "not_applicable" if claim.get("modality") == "unknown" else "unverified"
            reasons += problem
            evidence = {"slots": spans, **({"modality_cue": cue} if cue else {})}
        hard = any(checks[name] == "fail" for name in ("V1_schema", "V2_integrity", "V3_evidence", "V4_modality"))
        key = _duplicate_key(claim)
        if not hard and key in seen:
            checks["V7_duplicate"] = "fail"
            reasons.append(f"duplicate_of:{seen[key]}")
        else:
            checks["V7_duplicate"] = "pass" if not hard else "not_applicable"
            if not hard:
                seen[key] = claim["claim_id"]
        decision = "accepted" if not hard and checks["V7_duplicate"] == "pass" else "rejected"
        results.append({"claim_id": claim["claim_id"], "validator_version": VALIDATOR_VERSION, "checks": checks,
                        "reasons": reasons, "decision": decision, "evidence": evidence if decision == "accepted" else {}})
    return results
