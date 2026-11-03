"""Conservative, review-only semantic extraction for a small set of grammars.

Rules bind exact source spans. Unsupported sentences stay unit candidates.
No general legal inference, entity resolution, or assertion of completeness.
"""

import re

from legal_ai.common.io import canonical, digest
from legal_ai.extraction.candidates import rule_candidates
from legal_ai.kb.references import evidence_at
from legal_ai.schemas.contract import VERSION

RUN = "norm-rules-v1"
MODAL = re.compile(r"(?P<actor>.+?)\s+(?P<modality>không được|có quyền|có thể|phải)\s+(?P<action>.+)", re.IGNORECASE)
PREFIX = re.compile(r"^(?P<condition>(?:Trong trường hợp|Trong thời gian|Khi)\s+[^,]+),\s*", re.IGNORECASE)
BOUND = re.compile(r"(?P<quantity>Không quá\s+\d+\s+ngày(?:\s+làm việc)?)\s+đối với\s+(?P<condition>.+)", re.IGNORECASE)
SALARY = re.compile(r"(?P<object>Tiền lương) của (?P<beneficiary>người lao động) (?P<condition>trong thời gian thử việc) do hai bên thỏa thuận nhưng (?P<quantity>ít nhất (?P<modality>phải) (?P<action>bằng \d+% mức lương của công việc đó))", re.IGNORECASE)


def body_start(unit):
    text = unit["text"]
    heading = re.match(r"^Điều\s+\d+[^\n]*\n", text, re.IGNORECASE)
    if heading:
        return heading.end()
    label = re.match(r"^\s*(?:\d+\.|[a-zđ]\))\s+", text, re.IGNORECASE)
    return label.end() if label else 0


def extract_norms(units):
    by_id = {unit["unit_id"]: unit for unit in units}
    parents = {unit["parent_id"] for unit in units}
    fallback_claims, fallback_evidence = rule_candidates(units)
    fallback_by_version = {claim["source_unit_version_ids"][0]: claim for claim in fallback_claims}
    claims, evidence, reports = [], {}, []

    def add_anchor(unit, start, end):
        anchor = evidence_at(unit, start, end)
        evidence[anchor["evidence_id"]] = anchor
        return anchor["evidence_id"]

    def build(unit, sentence_start, sentence_end, spans, modality, modality_span, rule):
        slots = {name: {"state": "unknown", "text": None, "evidence_ids": []} for name in ("actor", "action", "beneficiary", "recipient", "object", "outcome", "conditions", "exceptions", "quantities", "deadlines", "scope")}
        ids = [add_anchor(unit, sentence_start, sentence_end)]
        for name, (start, end) in spans.items():
            if end <= start:
                continue
            eid = add_anchor(unit, start, end)
            slots[name] = {"state": "present", "text": unit["text"][start:end], "evidence_ids": [eid]}
            ids.append(eid)
        versions = [unit["unit_version_id"]]
        parent = by_id.get(unit["parent_id"])
        if parent and parent["text"].strip():
            # Keep the entire nearest parent as context, never silently discard
            # its conditions or try to reinterpret them as an inferred predicate.
            eid = add_anchor(parent, 0, len(parent["text"]))
            slots["scope"] = {"state": "present", "text": parent["text"], "evidence_ids": [eid]}
            ids.append(eid)
            versions.append(parent["unit_version_id"])
            if rule == "duration-bound":
                match = re.search(r"\bThời gian thử việc\b", parent["text"][body_start(parent):], re.IGNORECASE)
                if match:
                    start = body_start(parent) + match.start()
                    end = body_start(parent) + match.end()
                    eid = add_anchor(parent, start, end)
                    slots["object"] = {"state": "present", "text": parent["text"][start:end], "evidence_ids": [eid]}
                    ids.append(eid)
        modality_ids = []
        if modality_span:
            eid = add_anchor(unit, *modality_span)
            modality_ids.append(eid)
            ids.append(eid)
        return {"schema_version": VERSION, "claim_id": digest(canonical([RUN, rule, unit["unit_version_id"], sentence_start, sentence_end])), "source_unit_version_ids": versions, "modality": modality, "modality_evidence_ids": modality_ids, "slots": slots, "evidence_ids": sorted(set(ids)), "extraction_run_id": RUN + ":" + rule, "extraction_scope": "matched source sentence only + nearest parent context; unparsed text and unknown qualifiers require review", "completeness": "unknown"}

    for unit in units:
        if unit["unit_id"] in parents:
            continue
        start = body_start(unit)
        unit_claims, unmatched = [], []
        # Delimit sentences without splitting decimal numbers. Newlines also
        # bound a candidate so one rule cannot consume another paragraph.
        for sentence in re.finditer(r"[^\n]+", unit["text"][start:]):
            line_start = start + sentence.start()
            line = sentence.group()
            for piece in re.finditer(r".+?(?:\.(?=\s|$)|$)", line):
                raw = piece.group()
                left = len(raw) - len(raw.lstrip())
                text = raw.strip().rstrip(".;")
                if not text:
                    continue
                offset = line_start + piece.start() + left
                end = offset + len(text)
                spans, mode, cue, rule = {}, "unknown", None, None
                salary = SALARY.fullmatch(text)
                bound = BOUND.fullmatch(text)
                if salary:
                    spans = {name + "s" if name == "condition" else name: (offset + salary.start(name), offset + salary.end(name)) for name in ("beneficiary", "condition", "quantity", "action", "object")}
                    spans["quantities"] = spans.pop("quantity")
                    mode, cue, rule = "obligation", (offset + salary.start("modality"), offset + salary.end("modality")), "salary-bound"
                elif bound:
                    spans = {"quantities": (offset + bound.start("quantity"), offset + bound.end("quantity")), "conditions": (offset + bound.start("condition"), offset + bound.end("condition"))}
                    rule = "duration-bound"
                else:
                    prefix = PREFIX.match(text)
                    actor_offset = prefix.end() if prefix else 0
                    match = MODAL.fullmatch(text[actor_offset:])
                    if match and len(match.group("actor")) <= 100 and not re.search(r"\b(?:không|nhưng|thì|trừ|nếu|khi|trường hợp)\b|,", match.group("actor"), re.IGNORECASE) and not (match.group("modality").casefold() == "có thể" and re.match(r"bị\b", match.group("action"), re.IGNORECASE)):
                        base = offset + actor_offset
                        spans["actor"] = (base + match.start("actor"), base + match.end("actor"))
                        action_start, action_end = base + match.start("action"), base + match.end("action")
                        if prefix:
                            spans["conditions"] = (offset + prefix.start("condition"), offset + prefix.end("condition"))
                        action = unit["text"][action_start:action_end]
                        exception = re.search(r",\s*(trừ\s+.+)$", action, re.IGNORECASE)
                        if exception:
                            spans["exceptions"] = (action_start + exception.start(1), action_end)
                            action_end = action_start + exception.start()
                        # A whole explicit deadline phrase is retained; neither
                        # trigger nor calendar/working-day basis is inferred.
                        deadline = re.search(r"\s+(trong\s+\d+\s+ngày(?:\s+làm việc)?)$", unit["text"][action_start:action_end], re.IGNORECASE)
                        if deadline:
                            spans["deadlines"] = (action_start + deadline.start(1), action_end)
                            action_end = action_start + deadline.start()
                        beneficiary = re.search(r"\s+cho\s+(người lao động)$", unit["text"][action_start:action_end], re.IGNORECASE)
                        if beneficiary:
                            spans["recipient"] = (action_start + beneficiary.start(1), action_end)
                            action_end = action_start + beneficiary.start()
                        notification = re.fullmatch(r"(?P<verb>thông báo) (?P<object>kết quả thử việc)", unit["text"][action_start:action_end], re.IGNORECASE)
                        cancellation = re.fullmatch(r"(?P<verb>hủy bỏ) (?P<object>hợp đồng thử việc hoặc hợp đồng lao động đã giao kết) (?P<outcome>mà không cần báo trước và không phải bồi thường)", unit["text"][action_start:action_end], re.IGNORECASE)
                        submatch = notification or cancellation
                        if submatch:
                            spans["object"] = (action_start + submatch.start("object"), action_start + submatch.end("object"))
                            if cancellation:
                                spans["outcome"] = (action_start + submatch.start("outcome"), action_start + submatch.end("outcome"))
                            action_end = action_start + submatch.end("verb")
                        spans["action"] = (action_start, action_end)
                        mode = {"phải": "obligation", "không được": "prohibition", "có quyền": "entitlement", "có thể": "permission"}[match.group("modality").casefold()]
                        cue = (base + match.start("modality"), base + match.end("modality"))
                        rule = "explicit-deontic"
                if rule:
                    unit_claims.append(build(unit, offset, end, spans, mode, cue, rule))
                else:
                    unmatched.append({"start": offset, "end": end, "text": text})
        if unit_claims:
            claims.extend(unit_claims)
        elif unit["unit_version_id"] in fallback_by_version:
            fallback = fallback_by_version[unit["unit_version_id"]]
            claims.append(fallback)
            for anchor in fallback_evidence:
                if anchor["unit_version_id"] == unit["unit_version_id"]:
                    evidence[anchor["evidence_id"]] = anchor
        reports.append({"unit_id": unit["unit_id"], "structured_claim_count": len(unit_claims), "fallback_candidate": not unit_claims and unit["unit_version_id"] in fallback_by_version, "unparsed_sentences": unmatched, "status": "needs_review"})
    return claims, sorted(evidence.values(), key=lambda row: row["evidence_id"]), reports
