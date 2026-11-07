"""Index records for the retrieval conditions DK1 (fixed chunks) and DK2 (structural units).

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
        chain, current = [], by_id.get(leaf["parent_id"])
        while current:
            chain.append(current)
            current = by_id.get(current["parent_id"])
        chain.reverse()
        path = " > ".join(_path_label(u) for u in chain + [leaf])
        context = "".join(u["text"] for u in chain if u["unit_type"] in {"article", "clause"})
        parts = _sentence_parts(leaf["text"], max_tokens) if len(token_spans(leaf["text"])) > max_tokens else [(0, len(leaf["text"]))]
        for number, (start, end) in enumerate(parts, 1):
            text = leaf["text"][start:end]
            index_text = f"{document['title']}\n{path}\n{context}{text}"
            part = {"number": number, "of": len(parts)} if len(parts) > 1 else None
            records.append(_record("DK2", document, leaf["source_start"] + start, leaf["source_start"] + end, text, index_text,
                                   [leaf["unit_id"]], len(token_spans(text)), part))
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
