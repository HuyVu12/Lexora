"""NFC/newline normalization with conservative raw-character source spans."""

import unicodedata

from legal_ai.schemas.contract import NORMALIZATION_VERSION, text_hash


def normalize(raw: str, locator="text"):
    clusters = []
    pos = 0
    while pos < len(raw):
        start = pos
        if raw[pos] == "\r":
            pos += 2 if raw[pos:pos + 2] == "\r\n" else 1
            clusters.append(("\n", start, pos))
            continue
        value = raw[pos]
        pos += 1
        while pos < len(raw) and raw[pos] not in "\r\n":
            next_value = value + raw[pos]
            # Includes combining marks and starter-to-starter composition (e.g. Hangul).
            if unicodedata.combining(raw[pos]) or unicodedata.normalize("NFC", next_value) != unicodedata.normalize("NFC", value) + raw[pos]:
                value = next_value
                pos += 1
            else:
                break
        clusters.append((unicodedata.normalize("NFC", value), start, pos))
    text = "".join(value for value, _, _ in clusters)
    spans = [[start, end] for value, start, end in clusters for _ in value]
    return {"text": text, "normalization_version": NORMALIZATION_VERSION, "normalized_sha256": text_hash(text), "source_locator": locator, "raw_spans": spans}


def source_span(normalized, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(normalized["text"]):
        raise ValueError("invalid normalized span")
    spans = normalized["raw_spans"][start:end]
    return min(span[0] for span in spans), max(span[1] for span in spans)
