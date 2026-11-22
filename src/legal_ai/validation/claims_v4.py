"""Automatic validation of LLM knowledge-base claims, version `kb-validator-v4`: v3 plus lead-in evidence.

Same checks, reason codes and decision rule as `kb-validator-v3` (`validation/claims.py`, unchanged and still
selectable), with one difference in V3 evidence and V4 modality: a value that is not an exact quote of the claim's
sentence but is an exact quote of the lead-in of the sentence's parent unit (the Clause text before its Points, or
the Article text after its heading and before its Clauses; `extraction.inherit.lead_in`) is accepted, with evidence
pointing to the lead-in. Statutes put the bearer, the sanction or the modal cue of a list in that lead-in
("2. Phạt tiền từ ... đối với người sử dụng lao động có một trong các hành vi sau đây:"); the model sees the lead-in
as the sentence's context, and in the scope-v3 run 136 of 181 v3 evidence rejections were such values.

The sentence is searched first, then the lead-in; a value found in neither still fails with `<slot>_not_verbatim`.
A modal cue taken from the lead-in passes the same lexicon checks as one in the sentence. A slot inherited by
`claims-inherit-v1` is checked against its own evidence row: the row must be a valid contract evidence row of the
parent unit, inside the lead-in, and its quote must equal the slot value (`<slot>_inheritance_invalid` otherwise).

Accepted evidence keeps the v3 shape (`slots` and `modality_cue` as document offsets) and adds `lead_in` when a
value came from the lead-in: the parent unit, which slots, and one contract evidence row per value (offsets local
to the parent text, the parent's normalized SHA-256), so every lead-in quote can be checked with
`validation.evidence.check_evidence`. Accepted still means passing these checks, not a legally right norm.
"""

from legal_ai.extraction.inherit import lead_in
from legal_ai.extraction.llm_norms import locate
from legal_ai.kb.references import evidence_at
from legal_ai.schemas.contract import MODALITY_CUES
from legal_ai.validation.claims import _duplicate_key, _integrity, _local, _schema

VALIDATOR_VERSION = "kb-validator-v4"


def _inherited(claim, name, value, place):
    """Local (start, end) of a valid inherited evidence row for this slot, False if one is claimed but invalid,
    None when the slot is not inherited."""
    entry = ((claim.get("inheritance") or {}).get("slots") or {}).get(name)
    if entry is None:
        return None
    if place is None:
        return False
    parent, lead_start, lead_end = place
    row = entry.get("evidence") or {}
    start, end = row.get("start"), row.get("end")
    if (type(start) is not int or type(end) is not int or not lead_start <= start < end <= lead_end
            or row.get("unit_version_id") != parent["unit_version_id"] or row.get("normalized_sha256") != parent["normalized_sha256"]
            or parent["text"][start:end] != row.get("quote") or row.get("quote") != value
            or row != evidence_at(parent, start, end)):
        return False
    return start, end


def evidence_spans(claim, unit, place):
    """(document offsets per slot found in the sentence or the lead-in, local lead-in offsets per slot taken from
    the lead-in, missing slot names, invalid inherited slot names)."""
    start, end = _local(unit, claim)
    spans, lead, missing, invalid = {}, {}, [], []
    for name, value in sorted((claim.get("slots") or {}).items()):
        if value in (None, ""):
            continue
        inherited = _inherited(claim, name, value, place)
        if inherited is False:
            invalid.append(name)
            continue
        found = None if inherited else locate(unit["text"], start, end, value)
        if found is not None:
            spans[name] = [unit["source_start"] + found[0], unit["source_start"] + found[1]]
            continue
        local = inherited or (locate(place[0]["text"], place[1], place[2], value) if place else None)
        if local is None:
            missing.append(name)
        else:
            lead[name] = local
            spans[name] = [place[0]["source_start"] + local[0], place[0]["source_start"] + local[1]]
    return spans, lead, missing, invalid


def _modality(claim, unit, place):
    """(cue document offsets or None, cue local lead-in offsets or None, problems, verified)."""
    if claim.get("modality") == "unknown" or claim.get("modality_cue") in (None, ""):
        return None, None, [], False
    start, end = _local(unit, claim)
    cue = locate(unit["text"], start, end, claim.get("modality_cue"))
    text, base, from_lead = unit["text"], unit["source_start"], False
    if cue is None and place is not None:
        cue = locate(place[0]["text"], place[1], place[2], claim.get("modality_cue"))
        text, base, from_lead = place[0]["text"], place[0]["source_start"], True
    if cue is None:
        return None, None, ["modality_cue_not_verbatim"], False
    word = text[cue[0]:cue[1]].casefold()
    if word not in MODALITY_CUES.get(claim.get("modality"), set()):
        if any(word in cues for cues in MODALITY_CUES.values()):
            return None, None, ["modality_cue_mismatch"], False
        return None, None, [], False  # A real word of the text that the lexicon does not know: unverifiable.
    return [base + cue[0], base + cue[1]], (cue if from_lead else None), [], True


def validate(claims, units):
    """One result per claim, in input order: {claim_id, validator_version, checks, reasons, decision, evidence}."""
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
            place = lead_in(unit, by_id)
            spans, lead, missing, invalid = evidence_spans(claim, unit, place)
            checks["V3_evidence"] = "fail" if missing or invalid else "pass"
            reasons += [f"{name}_not_verbatim" for name in missing] + [f"{name}_inheritance_invalid" for name in invalid]
            cue, cue_lead, problem, verified = _modality(claim, unit, place)
            if problem:
                checks["V4_modality"] = "fail"
            elif verified:
                checks["V4_modality"] = "pass"
            else:
                checks["V4_modality"] = "not_applicable" if claim.get("modality") == "unknown" else "unverified"
            reasons += problem
            evidence = {"slots": spans, **({"modality_cue": cue} if cue else {})}
            if lead or cue_lead:
                parent = place[0]
                rows = {name: evidence_at(parent, *local) for name, local in sorted(lead.items())}
                if cue_lead:
                    rows["modality_cue"] = evidence_at(parent, *cue_lead)
                evidence["lead_in"] = {"unit_id": parent["unit_id"], "unit_version_id": parent["unit_version_id"],
                                       "slots": sorted(lead), "modality_cue": bool(cue_lead), "evidence": rows}
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
