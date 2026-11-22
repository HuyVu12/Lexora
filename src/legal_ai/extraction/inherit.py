"""Lead-in inheritance of knowledge-base claims (`claims-inherit-v1`): deterministic, offline, never invented.

A Point (or a Clause under an Article) often states only part of a norm; the bearer, the verb phrase or the sanction
sits in the lead-in of its parent ("2. Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng đối với người sử dụng lao
động có một trong các hành vi sau đây:" over "a) Yêu cầu người lao động thử việc quá 01 lần ..."). The model is
told to copy values from the sentence only, so such claims carry an empty actor (61% of the scope-v3 claims).

`inherit` fills an EMPTY `actor`, `action` or `outcome` slot of a DK3 claim from the parent's lead-in, only when one
of the fixed rules below finds the value verbatim there:

- `leadin-subject`: "<subject> <cue> ...:" with a modal cue (phải, không được, có quyền, có các nghĩa vụ, có trách
  nhiệm, ...); the subject is the text before the cue, after one leading condition ("Hằng năm, ...", "Ngoài quy
  định tại ..., ..."), cut before " khi ...". The claim's modality must agree with the cue (or be `unknown`).
- `leadin-action`: the verb phrase after that cue, cut before a condition (" nếu", " khi", " trong trường hợp", ...)
  or an exception (", trừ") and without the list tail ("các quyền sau đây", "như sau"); at least two syllables.
- `leadin-sanction` (to `outcome`, the legal consequence): "Phạt tiền[ từ X đồng đến Y đồng]" followed by
  " đối với ..." or " khi có ...".
- `leadin-sanction-actor`: the bearer named after "đối với" in that sanction lead-in.

Anything ambiguous is left empty: a lead-in of more than one line or sentence, not ending in ":", with a second modal
cue, a subject with a comma outside one leading condition, a subject starting with a condition word or a thing noun
("Việc", "Nội dung", "Văn bản", ...), ending in "và"/"hoặc" or holding "thì"/"sau đây"/"dưới đây", a sanction
whose amount is not a plain "từ X đồng đến Y đồng" or carries a cap or per-person rate ("nhưng tối đa", "mỗi").
Each inherited slot keeps the model's claim id and carries its own evidence row (`1.0.0-pilot` contract: exact
quote, offsets local to the parent unit, the parent's normalized SHA-256) and the rule that found it under
`claim["inheritance"]`, so inherited values stay distinguishable from extracted ones.
"""

import re

from legal_ai.extraction.norms import body_start
from legal_ai.kb.references import evidence_at

VERSION = "claims-inherit-v1"
PARENT_TYPES = ("clause", "article")
SLOTS = ("actor", "action", "outcome")
MAX_SUBJECT_WORDS = 25
MAX_SANCTION_ACTOR_WORDS = 12

# Modal cues of a lead-in and the claim modalities each one licenses. Longer cues first; a bare "được" is left out
# on purpose ("được tính như sau", "được quy định như sau" are passive, not entitlements).
_ANY = {"entitlement", "permission", "obligation"}
LEAD_CUES = {
    "có các quyền và nghĩa vụ": _ANY, "có các quyền và trách nhiệm": _ANY, "có quyền và trách nhiệm": _ANY, "có quyền và nghĩa vụ": _ANY,
    "có các quyền": {"entitlement", "permission"}, "có quyền": {"entitlement", "permission"},
    "được quyền": {"entitlement", "permission"}, "có thể": {"permission", "entitlement"},
    "có các nghĩa vụ": {"obligation"}, "có nghĩa vụ": {"obligation"}, "có trách nhiệm": {"obligation"},
    "chịu trách nhiệm": {"obligation"}, "phải": {"obligation"},
    "không được": {"prohibition"}, "nghiêm cấm": {"prohibition"}, "bị cấm": {"prohibition"},
}


def _words_re(words):
    return "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True))


CUE = re.compile(rf"(?<!\w)(?:{_words_re(LEAD_CUES)})(?!\w)", re.IGNORECASE)
CONDITION_HEAD = re.compile(r"(?:trong|ngoài|khi|sau khi|trước khi|hằng năm|hàng năm|trường hợp|đối với|kể từ|căn cứ|theo|tùy|nếu|riêng|ngay|chậm nhất)(?!\w)",
                            re.IGNORECASE)
# Heads of subjects that name a thing or a process, not a bearer of the norm ("Việc đánh giá ... phải tuân thủ").
THING_HEAD = re.compile(r"(?:việc|nội dung|văn bản|điều lệ|hồ sơ|hợp đồng|mức|thời hạn|thời gian|tiền lương|quyết định|phương án|kế hoạch|báo cáo|giấy|đơn)(?!\w)",
                        re.IGNORECASE)
SUBJECT_STOP = re.compile(r"(?<!\w)(?:thì|sau đây|dưới đây)(?!\w)", re.IGNORECASE)
SUBJECT_CUT = re.compile(r"\s+khi(?!\w)", re.IGNORECASE)
TRAILING_ADVERB = re.compile(r"\s+(?:còn|cũng|đều|vẫn|mới|chỉ)$", re.IGNORECASE)
ACTION_CUT = re.compile(r"(?:\s+(?:nếu|khi|trong (?:các )?trường hợp|thuộc một trong)|,\s*trừ)(?!\w)", re.IGNORECASE)
LIST_TAIL = re.compile(r"(?:\s+(?:trong|thuộc|vào|với|ở|theo|đối với))?(?:\s+(?:một hoặc một số|một số|một)\s+trong)?(?:\s+(?:các|những))?"
                       r"(?:\s+(?:trường hợp|hành vi|nội dung|điều kiện|quy định|công việc|chế độ|giấy tờ|quyền|nghĩa vụ|trách nhiệm|"
                       r"nhiệm vụ|thông tin|biện pháp|yêu cầu|hồ sơ|tiêu chuẩn|khoản|nguyên tắc)(?: chủ yếu)?)?\s+(?:sau đây|như sau|sau)$", re.IGNORECASE)
NOT_A_VERB = re.compile(r"(?:và|hoặc|đối với|với|về|trong|theo|tại|sau|như|của|cho)(?!\w)", re.IGNORECASE)
SANCTION_HEAD = re.compile(r"Phạt(?!\w)")
SANCTION = re.compile(r"Phạt (?:cảnh cáo|tiền)(?: từ \S+(?: đồng)? đến \S+ đồng)?(?= đối với | khi có |$)")
# A cap or a per-person rate after the amount ("... đối với mỗi người lao động nhưng tối đa không quá ...") belongs to
# the sanction; cutting it off would misstate the fine, so such lead-ins inherit nothing.
SANCTION_QUALIFIER = re.compile(r"(?<!\w)(?:nhưng|tối đa|không quá|mỗi)(?!\w)", re.IGNORECASE)
SANCTION_ACTOR = re.compile(r" đối với (?P<actor>.+?)(?= (?:có một trong|có hành vi|có các hành vi|khi|vi phạm|thực hiện|không)(?!\w))")
NOT_AN_ACTOR = re.compile(r"(?:hành vi|các hành vi|một trong|vi phạm|trường hợp|mỗi)(?!\w)", re.IGNORECASE)
SENTENCE_BREAK = re.compile(r"[.;]\s+\S")


def lead_in(unit, by_id):
    """(parent, start, end): the parent's lead-in as offsets local to the parent text, or None.

    A Clause's text stops where its first Point starts and an Article's text is its heading plus the text before
    its first Clause, so the parent body (without the label or heading) is exactly the lead-in of its children."""
    parent = by_id.get(unit.get("parent_id")) if unit else None
    if parent is None or parent["unit_type"] not in PARENT_TYPES:
        return None
    text = parent["text"]
    start = body_start(parent)
    while start < len(text) and text[start].isspace():
        start += 1
    end = len(text.rstrip())
    return (parent, start, end) if end > start else None


def _words(text):
    return len(text.split())


def _subject(text):
    """(subject start, subject end, cue match) of "<subject> <cue> ..." in a lead-in sentence, or None."""
    head = CONDITION_HEAD.match(text)
    for match in CUE.finditer(text):
        before = text[:match.start()]
        if head:
            if ", " not in before:
                continue  # The cue sits inside the leading condition ("Trường hợp phải ngừng việc, ...").
            if before.count(", ") > 1:
                return None  # A comma inside the condition or a list of bearers: where the subject starts is unclear.
            start = before.index(", ") + 2
        else:
            start = 0
        subject = before[start:]
        cut = SUBJECT_CUT.search(subject)
        subject = TRAILING_ADVERB.sub("", (subject[:cut.start()] if cut else subject).rstrip())
        if (not subject or any(mark in subject for mark in ",;:()") or CONDITION_HEAD.match(subject) or THING_HEAD.match(subject)
                or SUBJECT_STOP.search(subject) or re.search(r"(?<!\w)(?:và|hoặc)$", subject) or _words(subject) > MAX_SUBJECT_WORDS):
            return None
        if CUE.search(text, match.end()):
            return None  # A second modal cue: which bearer or modality the Points continue is not clear.
        return start, start + len(subject), match
    return None


def analyse(parent, start, end):
    """Values a lead-in offers: ({slot: (start, end, rule)} with offsets local to the parent text, licensed
    modalities). A sanction lead-in licenses any modality (None); no value gives ({}, set())."""
    line = parent["text"][start:end]
    if "\n" in line or not line.endswith(":"):
        return {}, set()
    text = line[:-1].rstrip()
    if SENTENCE_BREAK.search(text):
        return {}, set()
    if SANCTION_HEAD.match(text):
        sanction = SANCTION.match(text)
        if sanction is None or SANCTION_QUALIFIER.search(text, sanction.end()):
            return {}, set()
        found = {"outcome": (start, start + sanction.end(), "leadin-sanction")}
        actor = SANCTION_ACTOR.match(text, sanction.end())
        if actor:
            value = actor.group("actor")
            if not NOT_AN_ACTOR.match(value) and _words(value) <= MAX_SANCTION_ACTOR_WORDS and not any(mark in value for mark in ";:()"):
                found["actor"] = (start + actor.start("actor"), start + actor.end("actor"), "leadin-sanction-actor")
        return found, None
    subject = _subject(text)
    if subject is None:
        return {}, set()
    subject_start, subject_end, cue = subject
    found = {"actor": (start + subject_start, start + subject_end, "leadin-subject")}
    rest = text[cue.end():]
    cut = ACTION_CUT.search(rest)
    phrase = LIST_TAIL.sub("", rest[:cut.start()] if cut else rest)
    action = phrase.strip()
    if _words(action) >= 2 and not NOT_A_VERB.match(action):
        offset = cue.end() + (len(phrase) - len(phrase.lstrip()))
        found["action"] = (start + offset, start + offset + len(action), "leadin-action")
    return found, LEAD_CUES[cue.group().casefold()]


def inherit(claims, units):
    """(claims, report): every claim in input order, the eligible ones with inherited slots and provenance."""
    by_id = {unit["unit_id"]: unit for unit in units}
    by_version = {unit["unit_version_id"]: unit for unit in units}
    cache, result = {}, []
    report = {"inheritance_version": VERSION, "claims": len(claims), "claims_with_lead_in": 0, "claims_changed": 0,
              "slots": {}, "skipped_modality": 0, "actor_before": 0, "actor_after": 0}
    for claim in claims:
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        report["actor_before"] += _filled(slots.get("actor"))
        place = lead_in(by_version.get(claim.get("unit_version_id")), by_id)
        added = {}
        if place is not None:
            report["claims_with_lead_in"] += 1
            parent, start, end = place
            if parent["unit_id"] not in cache:
                cache[parent["unit_id"]] = analyse(parent, start, end)
            found, modalities = cache[parent["unit_id"]]
            if found and modalities and claim.get("modality") not in modalities | {"unknown"}:
                report["skipped_modality"] += 1
                found = {}
            for name in SLOTS:
                if name in found and name in slots and not _filled(slots[name]):
                    local_start, local_end, rule = found[name]
                    added[name] = {"rule": rule, "evidence": evidence_at(parent, local_start, local_end),
                                   "span": [parent["source_start"] + local_start, parent["source_start"] + local_end]}
                    key = f"{name}:{rule}"
                    report["slots"][key] = report["slots"].get(key, 0) + 1
        if added:
            report["claims_changed"] += 1
            slots = slots | {name: entry["evidence"]["quote"] for name, entry in added.items()}
            claim = claim | {"slots": slots, "inheritance": {"version": VERSION, "parent_unit_id": parent["unit_id"], "slots": added}}
        report["actor_after"] += _filled(slots.get("actor"))
        result.append(claim)
    report["slots"] = dict(sorted(report["slots"].items()))
    return result, report


def _filled(value):
    return isinstance(value, str) and bool(value.strip())
