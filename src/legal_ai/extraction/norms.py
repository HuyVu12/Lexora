"""Conservative, review-only semantic extraction for a small set of grammars.

Rules bind exact source spans. A sentence with a normative cue that no grammar
covers becomes a cue-sentence candidate with unknown slots; a sentence without
any cue stays in the extraction report. No general legal inference, entity
resolution, or assertion of completeness.
"""

import re

from legal_ai.common.io import canonical, digest
from legal_ai.kb.references import evidence_at
from legal_ai.schemas.contract import VERSION

RUN = "norm-rules-v2"
# Every run whose claims carry typed slots (graph shows Entity/Action nodes, not generic slots).
SEMANTIC_RUNS = ("norm-rules-v1:", "norm-rules-v2:", "norm-llm-v1:", "manual-v1:")
MODAL_CUES = {"phải": "obligation", "có trách nhiệm": "obligation", "có nghĩa vụ": "obligation",
              "không được": "prohibition", "có quyền": "entitlement", "có thể": "permission"}
MODAL = re.compile(r"(?P<actor>.+?)\s+(?P<modality>không được|có quyền|có trách nhiệm|có nghĩa vụ|có thể|phải)\s+(?P<action>.+)", re.IGNORECASE)
PREFIX = re.compile(r"^(?P<condition>(?P<kind>Trong trường hợp|Trong thời gian|Trong thời hạn|Chậm nhất|Khi|Sau khi|Trước khi)\s+[^,]+),\s*", re.IGNORECASE)
DEADLINE_PREFIXES = {"trong thời hạn", "chậm nhất"}
BOUND = re.compile(r"(?P<quantity>Không quá\s+\d+\s+ngày(?:\s+làm việc)?)\s+đối với\s+(?P<condition>.+)", re.IGNORECASE)
SALARY = re.compile(r"(?P<object>Tiền lương) của (?P<beneficiary>người lao động) (?P<condition>trong thời gian thử việc) do hai bên thỏa thuận nhưng (?P<quantity>ít nhất (?P<modality>phải) (?P<action>bằng \d+% mức lương của công việc đó))", re.IGNORECASE)
# A cue only marks a sentence for review; it never sets the modality by itself
# ("không phải", "không bắt buộc phải" negate the cue).
CUE = re.compile(r"\b(?:phải|không được|có quyền|có thể|có trách nhiệm|có nghĩa vụ|được quyền|nghiêm cấm|bị cấm|bắt buộc|không áp dụng|không quá)\b", re.IGNORECASE)
SLOT_NAMES = ("actor", "action", "beneficiary", "recipient", "object", "outcome", "conditions", "exceptions", "quantities", "deadlines", "scope")


def is_semantic(run_id):
    # A cue sentence only marks text for review; like unit-cue candidates it carries no typed slots.
    return isinstance(run_id, str) and run_id.startswith(SEMANTIC_RUNS) and not run_id.endswith(":cue-sentence")


def body_start(unit):
    text = unit["text"]
    heading = re.match(r"^Điều\s+\d+[^\n]*\n", text, re.IGNORECASE)
    if heading:
        return heading.end()
    label = re.match(r"^\s*(?:\d+\.|[a-zđ]\))\s+", text, re.IGNORECASE)
    return label.end() if label else 0


def sentences(unit):
    """(start, end, text) of each sentence in a unit body, without labels or trailing punctuation.

    Sentences are delimited without splitting decimal numbers; newlines also bound
    a sentence so one rule cannot consume another paragraph.
    """
    start = body_start(unit)
    result = []
    for line in re.finditer(r"[^\n]+", unit["text"][start:]):
        line_start = start + line.start()
        for piece in re.finditer(r".+?(?:\.(?=\s|$)|$)", line.group()):
            raw = piece.group()
            left = len(raw) - len(raw.lstrip())
            text = raw.strip().rstrip(".;:").rstrip()
            if text:
                offset = line_start + piece.start() + left
                result.append((offset, offset + len(text), text))
    return result


def leaf_units(units):
    parents = {unit["parent_id"] for unit in units}
    return [unit for unit in units if unit["unit_id"] not in parents]


class ClaimBuilder:
    """Builds contract claims whose every slot is an exact span of a source unit."""

    def __init__(self, units):
        self.by_id = {unit["unit_id"]: unit for unit in units}
        self.evidence = {}

    def anchor(self, unit, start, end):
        row = evidence_at(unit, start, end)
        self.evidence[row["evidence_id"]] = row
        return row["evidence_id"]

    def build(self, unit, sentence, spans, modality, modality_span, *, run, rule, key_extra=None, parent_object=None):
        sentence_start, sentence_end = sentence
        slots = {name: {"state": "unknown", "text": None, "evidence_ids": []} for name in SLOT_NAMES}
        ids = [self.anchor(unit, sentence_start, sentence_end)]
        for name, (start, end) in spans.items():
            if end <= start:
                continue
            eid = self.anchor(unit, start, end)
            slots[name] = {"state": "present", "text": unit["text"][start:end], "evidence_ids": [eid]}
            ids.append(eid)
        versions = [unit["unit_version_id"]]
        parent = self.by_id.get(unit["parent_id"])
        if parent and parent["text"].strip():
            # Keep the entire nearest parent as context, never silently discard
            # its conditions or try to reinterpret them as an inferred predicate.
            eid = self.anchor(parent, 0, len(parent["text"]))
            slots["scope"] = {"state": "present", "text": parent["text"], "evidence_ids": [eid]}
            ids.append(eid)
            versions.append(parent["unit_version_id"])
            if parent_object:
                match = re.search(parent_object, parent["text"][body_start(parent):], re.IGNORECASE)
                if match:
                    start = body_start(parent) + match.start()
                    end = body_start(parent) + match.end()
                    eid = self.anchor(parent, start, end)
                    slots["object"] = {"state": "present", "text": parent["text"][start:end], "evidence_ids": [eid]}
                    ids.append(eid)
        modality_ids = []
        if modality_span:
            eid = self.anchor(unit, *modality_span)
            modality_ids.append(eid)
            ids.append(eid)
        key = [run, rule, unit["unit_version_id"], sentence_start, sentence_end] + ([key_extra] if key_extra is not None else [])
        return {"schema_version": VERSION, "claim_id": digest(canonical(key)), "source_unit_version_ids": versions,
                "modality": modality, "modality_evidence_ids": modality_ids, "slots": slots, "evidence_ids": sorted(set(ids)),
                "extraction_run_id": run + ":" + rule,
                "extraction_scope": "matched source sentence only + nearest parent context; unparsed text and unknown qualifiers require review",
                "completeness": "unknown"}


def match_sentence(unit, offset, text):
    """Return (spans, modality, cue_span, rule) for one sentence, or None when no grammar applies."""
    salary = SALARY.fullmatch(text)
    if salary:
        spans = {name + "s" if name == "condition" else name: (offset + salary.start(name), offset + salary.end(name)) for name in ("beneficiary", "condition", "quantity", "action", "object")}
        spans["quantities"] = spans.pop("quantity")
        return spans, "obligation", (offset + salary.start("modality"), offset + salary.end("modality")), "salary-bound"
    bound = BOUND.fullmatch(text)
    if bound:
        return {"quantities": (offset + bound.start("quantity"), offset + bound.end("quantity")),
                "conditions": (offset + bound.start("condition"), offset + bound.end("condition"))}, "unknown", None, "duration-bound"
    prefix = PREFIX.match(text)
    actor_offset = prefix.end() if prefix else 0
    match = MODAL.fullmatch(text[actor_offset:])
    if not match or len(match.group("actor")) > 100 or re.search(r"\b(?:không|nhưng|thì|trừ|nếu|khi|trường hợp)\b|,", match.group("actor"), re.IGNORECASE):
        return None
    if match.group("modality").casefold() == "có thể" and re.match(r"bị\b", match.group("action"), re.IGNORECASE):
        return None
    spans = {}
    base = offset + actor_offset
    spans["actor"] = (base + match.start("actor"), base + match.end("actor"))
    action_start, action_end = base + match.start("action"), base + match.end("action")
    if prefix:
        slot = "deadlines" if prefix.group("kind").casefold() in DEADLINE_PREFIXES else "conditions"
        spans[slot] = (offset + prefix.start("condition"), offset + prefix.end("condition"))
    action = unit["text"][action_start:action_end]
    exception = re.search(r",\s*(trừ\s+.+)$", action, re.IGNORECASE)
    if exception:
        spans["exceptions"] = (action_start + exception.start(1), action_end)
        action_end = action_start + exception.start()
    # A whole explicit deadline phrase is retained; neither trigger nor
    # calendar/working-day basis is inferred.
    deadline = re.search(r"\s+(trong\s+\d+\s+ngày(?:\s+làm việc)?)$", unit["text"][action_start:action_end], re.IGNORECASE)
    if deadline and "deadlines" not in spans:
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
    cue = (base + match.start("modality"), base + match.end("modality"))
    return spans, MODAL_CUES[match.group("modality").casefold()], cue, "explicit-deontic"


def extract_norms(units):
    builder = ClaimBuilder(units)
    claims, reports = [], []
    for unit in leaf_units(units):
        structured, cue_sentences, unmatched = [], [], []
        for start, end, text in sentences(unit):
            found = match_sentence(unit, start, text)
            if found:
                spans, mode, cue, rule = found
                structured.append(builder.build(unit, (start, end), spans, mode, cue, run=RUN, rule=rule,
                                                parent_object=r"\bThời gian thử việc\b" if rule == "duration-bound" else None))
            elif CUE.search(text):
                # Mark the sentence for review; slots and modality stay unknown.
                claims.append(builder.build(unit, (start, end), {}, "unknown", None, run=RUN, rule="cue-sentence"))
                cue_sentences.append({"start": start, "end": end, "text": text})
            else:
                unmatched.append({"start": start, "end": end, "text": text})
        claims.extend(structured)
        reports.append({"unit_id": unit["unit_id"], "unit_version_id": unit["unit_version_id"],
                        "structured_claim_count": len(structured), "cue_sentences": cue_sentences,
                        "fallback_candidate": bool(cue_sentences) and not structured,
                        "unparsed_sentences": unmatched, "status": "needs_review"})
    return claims, sorted(builder.evidence.values(), key=lambda row: row["evidence_id"]), reports
