"""Line-based hierarchy parser. All text retained; ambiguous headings audited.

`lexora-parser-v2` adds three rules on top of the plain heading patterns:
- An article heading spelled with a known typo ("Điêu 38.") or the look-alike eth ("Ðiều") still opens the article,
  audited as `heading_variant`.
- A quotation that starts a line (the replaced text of an article that amends another document) is text of the unit
  that quotes it: its "Điều/khoản/điểm" lines open no unit. Quotes that hide such headings are audited as
  `quoted_text`; a quote that never closes is ignored and audited as `unclosed_quote`.
- A standalone "Phụ lục"/"PHỤ LỤC" line after the first article ends the structured body: appendix forms (whose
  "Điều 1." lines belong to a template) open no unit and are returned as `trailing_text`, audited as `appendix_start`.
"""

import re

from legal_ai.schemas.contract import VERSION, text_hash, unit_version

PARSER_VERSION = "lexora-parser-v2"
PATTERNS = [
    ("chapter", re.compile(r"^Chương\s+([IVXLCDM]+|\d+)\b", re.I)),
    ("section", re.compile(r"^Mục\s+(\d+)\b", re.I)),
    ("article", re.compile(r"^(Điều|Điêu|Ðiều)\s+(\d+[a-zđ]?)\s*[.:]", re.I)),
    ("clause", re.compile(r"^(\d+)\.\s+")),
    ("point", re.compile(r"^([a-zđ])\)\s+", re.I)),
]
LEVEL = {kind: index for index, (kind, _) in enumerate(PATTERNS)}
APPENDIX = re.compile(r"^(?:PHỤ LỤC|Phụ lục)(?:\s+(?:[IVXLCDM]+|\d+))?\s*$")
OPENING_QUOTES = ("“", '"')


def _heading(trimmed):
    return next(((kind, match) for kind, pattern in PATTERNS if (match := pattern.match(trimmed))), None)


def _quote_balanced(depth, straight, line):
    depth += line.count("“") - line.count("”")
    straight += line.count('"')
    return depth, straight, depth <= 0 and straight % 2 == 0


def _quoted_lines(lines):
    """Line indexes inside a quotation that opens a line, and audit entries for quotes that hide headings."""
    quoted, blocks, index = set(), [], 0
    while index < len(lines):
        trimmed = lines[index].lstrip(" \t ")
        if not trimmed.startswith(OPENING_QUOTES):
            index += 1
            continue
        depth, straight, closed = _quote_balanced(0, 0, trimmed)
        end = index
        while not closed and end + 1 < len(lines):
            end += 1
            depth, straight, closed = _quote_balanced(depth, straight, lines[end])
        if not closed:
            blocks.append(("unclosed_quote", index, index))
            index += 1
            continue
        inner = [trimmed.lstrip("“\"")] + [lines[i].lstrip(" \t ") for i in range(index + 1, end + 1)]
        if any(_heading(text) for text in inner):
            blocks.append(("quoted_text", index, end))
        quoted.update(range(index, end + 1))
        index = end + 1
    return quoted, blocks


def parse(normalized, document_id, document_version_id):
    text = normalized["text"]
    lines = text.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    quoted, blocks = _quoted_lines(lines)
    block_audits = {start: (code, end) for code, start, end in blocks}
    units, audits, stack, seen = [], [], [], set()
    body_end = len(text)
    for index, line in enumerate(lines):
        offset = starts[index]
        if index in block_audits:
            code, end = block_audits[index]
            entry = {"code": code, "offset": offset}
            if code == "quoted_text":
                entry["end"] = starts[end] + len(lines[end])
                if stack:
                    entry["unit_id"] = stack[-1]["unit_id"]
            audits.append(entry)
        if index in quoted:
            continue
        trimmed = line.lstrip(" \t ")
        if units and APPENDIX.match(trimmed.rstrip()):
            audits.append({"code": "appendix_start", "offset": offset})
            body_end = offset
            break
        candidate = _heading(trimmed)
        if not candidate:
            continue
        kind, match = candidate
        level = LEVEL[kind]
        parents = [unit for unit in stack if LEVEL[unit["unit_type"]] < level]
        parent = parents[-1] if parents else None
        required = {"clause": "article", "point": "clause"}.get(kind)
        if required and (parent is None or parent["unit_type"] != required):
            audits.append({"code": "orphan_heading", "offset": offset, "line": trimmed.rstrip()})
            continue
        label = match.group(match.lastindex).lower()
        path = (parent["unit_id"] if parent else document_id) + f"/{kind}-{label}"
        if path in seen:
            audits.append({"code": "duplicate_heading", "offset": offset, "unit_id": path})
            continue
        if kind == "article" and match.group(1).lower() != "điều":
            audits.append({"code": "heading_variant", "offset": offset, "unit_id": path, "word": match.group(1)})
        if kind in {"article", "clause"} and label.isdigit():
            siblings = [u for u in units if u["parent_id"] == (parent["unit_id"] if parent else None) and u["unit_type"] == kind]
            if siblings and siblings[-1]["label"].isdigit() and int(label) != int(siblings[-1]["label"]) + 1:
                audits.append({"code": "sequence_gap", "offset": offset, "unit_id": path})
        unit = {"schema_version": VERSION, "unit_id": path, "unit_version_id": "", "document_id": document_id, "document_version_id": document_version_id, "parent_id": parent["unit_id"] if parent else None, "unit_type": kind, "label": label, "text": "", "normalized_sha256": "", "source_start": offset, "source_end": 0, "source_locator": normalized["source_locator"]}
        units.append(unit)
        stack = parents + [unit]
        seen.add(path)
    for index, unit in enumerate(units):
        end = units[index + 1]["source_start"] if index + 1 < len(units) else body_end
        unit.update(source_end=end, text=text[unit["source_start"]:end])
        unit["normalized_sha256"] = text_hash(unit["text"])
        unit["unit_version_id"] = unit_version(unit)
    unassigned_end = units[0]["source_start"] if units else len(text)
    trailing_start = body_end if units else len(text)
    return {"parser_version": PARSER_VERSION, "units": units, "audit": audits,
            "unassigned_text": text[:unassigned_end], "unassigned_span": [0, unassigned_end],
            "trailing_text": text[trailing_start:], "trailing_span": [trailing_start, len(text)]}
