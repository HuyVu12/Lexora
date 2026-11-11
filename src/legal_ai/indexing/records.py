"""Index records for the retrieval conditions DK1 (fixed chunks), DK2 (structural units) and DK3/DK4 (LLM claims).

Every record carries the exact source span it was cut from (`text == document_text[source_start:source_end]`,
Unicode code point offsets into the normalized document text) and the canonical unit IDs it overlaps, so
Recall@K of every condition is measured on the same units. `index_text` is what the retriever reads; it is
a search aid, never evidence.

Both conditions prefix `index_text` with the document title, so the only difference between them is the
structure: DK1 cuts the text into windows of a fixed token count, DK2 keeps each leaf unit (Article without
Clauses, Clause without Points, or Point) whole and adds its Article/Clause path and the lead text of its
ancestors. A leaf longer than the token limit is split at sentence ends, each part keeping that context.
"""

import re
import unicodedata

from legal_ai.common.io import canonical, digest
from legal_ai.schemas.contract import text_hash

RECORD_VERSION = "index-record-v1"
TOKENIZER = "lexora-syllable-v1"
_TOKEN = re.compile(r"[^\W_]+|%", re.UNICODE)
_SENTENCE_END = re.compile(r"[.;:!?](?=\s)|\n")


def token_spans(text):
    """(start, end) offsets of the tokens of `text`: Unicode word runs and `%`, as the BM25 tokenizer reads them."""
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError("text must be NFC normalized")
    return [match.span() for match in _TOKEN.finditer(text)]


def _record(condition, document, start, end, text, index_text, unit_ids, tokens, part=None):
    key = [condition, document["document_version_id"], start, end]
    return {
        "record_version": RECORD_VERSION,
        "record_id": f"{condition.lower()}:{digest(canonical(key))[:16]}",
        "condition": condition,
        "document_id": document["document_id"],
        "document_version_id": document["document_version_id"],
        "source_start": start,
        "source_end": end,
        "text": text,
        "text_sha256": text_hash(text),
        "index_text": index_text,
        "unit_ids": unit_ids,
        "token_count": tokens,
        **({"part": part} if part else {}),
    }


def _check_texts(documents, units, texts):
    by_doc = {doc["document_id"]: doc for doc in documents}
    for document_id, text in texts.items():
        if document_id not in by_doc or text_hash(text) != by_doc[document_id]["document_version_id"]:
            raise ValueError(f"document text does not match its version: {document_id}")
    for unit in units:
        text = texts.get(unit["document_id"])
        if text is None or text[unit["source_start"]:unit["source_end"]] != unit["text"]:
            raise ValueError(f"unit text does not match its document span: {unit['unit_id']}")
    return by_doc


def _runs(units):
    """Contiguous runs of units per document, in source order; a run never crosses a gap or a document."""
    runs = []
    for unit in sorted(units, key=lambda u: (u["document_id"], u["source_start"])):
        last = runs[-1] if runs else None
        if last and last[-1]["document_id"] == unit["document_id"] and last[-1]["source_end"] == unit["source_start"]:
            last.append(unit)
        elif last and last[-1]["document_id"] == unit["document_id"] and unit["source_start"] < last[-1]["source_end"]:
            raise ValueError("overlapping units")
        else:
            runs.append([unit])
    return runs


def fixed_chunks(documents, units, texts, chunk_tokens=384, overlap_tokens=64):
    """DK1: windows of `chunk_tokens` tokens, `overlap_tokens` shared with the previous window."""
    if type(chunk_tokens) is not int or type(overlap_tokens) is not int or not 0 <= overlap_tokens < chunk_tokens:
        raise ValueError("need 0 <= overlap_tokens < chunk_tokens")
    by_doc = _check_texts(documents, units, texts)
    records = []
    for run in _runs(units):
        document = by_doc[run[0]["document_id"]]
        base = run[0]["source_start"]
        run_text = texts[document["document_id"]][base:run[-1]["source_end"]]
        spans = token_spans(run_text)
        step = chunk_tokens - overlap_tokens
        for first in range(0, len(spans), step):
            window = spans[first:first + chunk_tokens]
            last = first + chunk_tokens >= len(spans)
            # Windows cut at token edges; the first and last window of a run reach its ends so no text is lost.
            start = base if first == 0 else base + window[0][0]
            end = run[-1]["source_end"] if last else base + window[-1][1]
            text = texts[document["document_id"]][start:end]
            covered = [u["unit_id"] for u in run if u["source_start"] < end and start < u["source_end"]]
            records.append(_record("DK1", document, start, end, text, f"{document['title']}\n{text}", covered, len(window)))
            if last:
                break
    return records


def _path_label(unit):
    names = {"chapter": "Chương", "section": "Mục", "article": "Điều", "clause": "Khoản", "point": "Điểm"}
    # The parser stores Chapter numerals in lower case; Vietnamese statutes write them in capitals.
    label = unit["label"].upper() if unit["unit_type"] == "chapter" else unit["label"]
    return f"{names[unit['unit_type']]} {label}"


def unit_path(unit, by_id):
    """("Chương III > Mục 1 > Điều 24 > Khoản 1", ancestors) of a unit."""
    chain, current = [], by_id.get(unit["parent_id"])
    while current:
        chain.append(current)
        current = by_id.get(current["parent_id"])
    chain.reverse()
    return " > ".join(_path_label(u) for u in chain + [unit]), chain


def _sentence_parts(text, max_tokens):
    """Split `text` into consecutive (start, end) parts at sentence ends, each at most `max_tokens` tokens
    unless one sentence alone is longer. The parts cover the text without gaps."""
    cuts = [m.end() for m in _SENTENCE_END.finditer(text)]
    sentences, start = [], 0
    for cut in cuts + [len(text)]:
        if cut > start:
            sentences.append((start, cut))
            start = cut
    parts = []
    for start, end in sentences:
        if parts and len(token_spans(text[parts[-1][0]:end])) <= max_tokens:
            parts[-1] = (parts[-1][0], end)
        else:
            parts.append((start, end))
    return parts


def structural_records(documents, units, texts, max_tokens=384):
    """DK2: one record per leaf unit with its path and ancestor lead text; long leaves split by sentence."""
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")
    by_doc = _check_texts(documents, units, texts)
    by_id = {u["unit_id"]: u for u in units}
    parents = {u["parent_id"] for u in units}
    records = []
    for leaf in sorted((u for u in units if u["unit_id"] not in parents), key=lambda u: (u["document_id"], u["source_start"])):
        document = by_doc[leaf["document_id"]]
        path, chain = unit_path(leaf, by_id)
        context = "".join(u["text"] for u in chain if u["unit_type"] in {"article", "clause"})
        parts = _sentence_parts(leaf["text"], max_tokens) if len(token_spans(leaf["text"])) > max_tokens else [(0, len(leaf["text"]))]
        for number, (start, end) in enumerate(parts, 1):
            text = leaf["text"][start:end]
            index_text = f"{document['title']}\n{path}\n{context}{text}"
            part = {"number": number, "of": len(parts)} if len(parts) > 1 else None
            records.append(_record("DK2", document, leaf["source_start"] + start, leaf["source_start"] + end, text, index_text,
                                   [leaf["unit_id"]], len(token_spans(text)), part))
    return records


SLOT_LABELS = {"actor": "Chủ thể", "action": "Hành vi", "object": "Đối tượng", "beneficiary": "Bên thụ hưởng", "recipient": "Bên nhận",
               "conditions": "Điều kiện", "exceptions": "Ngoại lệ", "deadlines": "Thời hạn", "quantities": "Định lượng", "outcome": "Kết quả"}
MODALITY_LABELS = {"obligation": "nghĩa vụ", "prohibition": "điều cấm", "entitlement": "quyền", "permission": "được phép", "unknown": "chưa xác định"}


def serialize_claim(claim):
    """The fixed-order text of a knowledge-base claim: what DK3/DK4 retrieve and hand to the generator.
    Slot strings are shown as the model gave them (DK3) or as validated quotes (DK4); nothing is rephrased."""
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    modality = MODALITY_LABELS.get(claim.get("modality"), str(claim.get("modality")))
    cue = claim.get("modality_cue")
    lines = [f"Tính quy phạm: {modality}" + (f" ({cue})" if isinstance(cue, str) and cue else "")]
    for name, label in SLOT_LABELS.items():
        value = slots.get(name)
        if value not in (None, ""):
            lines.append(f"{label}: {value if isinstance(value, str) else canonical(value)}")
    return "\n".join(lines)


def claim_records(condition, documents, units, texts, claims):
    """DK3/DK4: one record per knowledge-base claim. The source span is the claim's sentence (so Recall@K maps
    to the same units as DK1/DK2); `index_text` and `context_text` carry the serialized claim, not the sentence."""
    by_doc = _check_texts(documents, units, texts)
    by_id = {u["unit_id"]: u for u in units}
    records = []
    for claim in claims:
        unit = by_id.get(claim.get("unit_id"))
        sentence = claim.get("sentence") or {}
        if unit is None or not unit["source_start"] <= sentence.get("start", -1) < sentence.get("end", -1) <= unit["source_end"]:
            raise ValueError(f"claim outside the corpus: {claim.get('claim_id')}")
        document = by_doc[unit["document_id"]]
        path, _ = unit_path(unit, by_id)
        body = serialize_claim(claim)
        start, end = sentence["start"], sentence["end"]
        row = _record(condition, document, start, end, texts[document["document_id"]][start:end], f"{document['title']}\n{path}\n{body}",
                      [unit["unit_id"]], len(token_spans(body)))
        key = [condition, document["document_version_id"], claim["claim_id"]]
        row.update(record_id=f"{condition.lower()}:{digest(canonical(key))[:16]}", claim_id=claim["claim_id"], context_text=body)
        records.append(row)
    return records


COMPACT_SLOTS = ("actor", "beneficiary", "conditions", "exceptions", "deadlines", "quantities", "outcome")
COMPACT_WORDS = 8


def compact_claim(claim):
    """One line with the norm's structure for the generator: modality and the slots that qualify the rule, each value
    cut to a few words. The values are verbatim parts of the source text printed just above, so nothing is lost; the
    line tells the generator who is bound, under which condition or exception and with which consequence."""
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    parts = [MODALITY_LABELS.get(claim.get("modality"), str(claim.get("modality")))]
    for name in COMPACT_SLOTS:
        value = slots.get(name)
        if isinstance(value, str) and value.strip():
            words = value.split()
            parts.append(f"{SLOT_LABELS[name]}: {' '.join(words[:COMPACT_WORDS])}{'…' if len(words) > COMPACT_WORDS else ''}")
    return " · ".join(parts)


def kb_unit_records(condition, documents, units, texts, claims, max_tokens=384, view="full"):
    """DK3/DK4 (`record: unit_with_claims`): the DK2 record of every leaf unit, its exact source text, path and lead
    text unchanged, followed by the serialized knowledge-base claims of that unit. A unit without a claim keeps its
    DK2 record, so the only difference to DK2 is the added norm structure (and between DK3 and DK4, which claims
    survived validation). `token_count` counts the source text and the claims, i.e. what the generator reads beyond
    the shared title and path.

    With `view="compact"` the generator reads `generator_text` instead: the DK2 text and one structure line per claim
    (`compact_claim`), while `index_text` keeps the full claims for searching; budgets count `generator_text`."""
    if view not in ("full", "compact"):
        raise ValueError("claims_view must be full or compact")
    by_id = {u["unit_id"]: u for u in units}
    attached = {}
    for claim in claims:
        unit = by_id.get(claim.get("unit_id"))
        sentence = claim.get("sentence") or {}
        if unit is None or not unit["source_start"] <= sentence.get("start", -1) < sentence.get("end", -1) <= unit["source_end"]:
            raise ValueError(f"claim outside the corpus: {claim.get('claim_id')}")
        attached.setdefault(unit["unit_id"], []).append(claim)
    records, used = [], set()
    for row in structural_records(documents, units, texts, max_tokens):
        unit_id = row["unit_ids"][0]
        # A long leaf split into parts gets each claim on the part that holds its sentence.
        mine = sorted((c for c in attached.get(unit_id, []) if row["source_start"] <= c["sentence"]["start"] < row["source_end"]),
                      key=lambda c: (c["sentence"]["start"], c["claim_id"]))
        bodies = [serialize_claim(c) for c in mine]
        block = "".join(f"\n[Quy phạm {n}]\n{body}" for n, body in enumerate(bodies, 1))
        base = row["index_text"].rstrip("\n")
        row = {**row, "condition": condition, "index_text": base + block,
               "record_id": f"{condition.lower()}:{row['record_id'].split(':', 1)[1]}",
               "token_count": row["token_count"] + sum(len(token_spans(b)) for b in bodies),
               "claim_ids": [c["claim_id"] for c in mine]}
        if view == "compact":
            lines = [compact_claim(c) for c in mine]
            row["generator_text"] = base + "".join(f"\n[Quy phạm {n}] {line}" for n, line in enumerate(lines, 1))
            row["token_count"] = len(token_spans(row["text"])) + sum(len(token_spans(line)) for line in lines)
        used.update(row["claim_ids"])
        records.append(row)
    missing = [c["claim_id"] for c in claims if c["claim_id"] not in used]
    if missing:
        raise ValueError(f"claims not attached to any record: {missing[:5]}")
    return records


def check_records(records, texts):
    """Raise if any record's text is not its exact source span or its hash does not match."""
    seen = set()
    for row in records:
        if row["record_id"] in seen:
            raise ValueError(f"duplicate record ID: {row['record_id']}")
        seen.add(row["record_id"])
        if texts[row["document_id"]][row["source_start"]:row["source_end"]] != row["text"] or text_hash(row["text"]) != row["text_sha256"]:
            raise ValueError(f"record text does not match its source span: {row['record_id']}")
    return records
