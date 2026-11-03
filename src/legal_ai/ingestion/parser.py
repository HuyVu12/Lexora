"""Line-based hierarchy parser. All text retained; ambiguous headings audited."""

import re

from legal_ai.schemas.contract import VERSION, text_hash, unit_version

PATTERNS = [
    ("chapter", re.compile(r"^Chương\s+([IVXLCDM]+|\d+)\b", re.I)),
    ("section", re.compile(r"^Mục\s+(\d+)\b", re.I)),
    ("article", re.compile(r"^Điều\s+(\d+[a-zđ]?)\s*[.:]", re.I)),
    ("clause", re.compile(r"^(\d+)\.\s+")),
    ("point", re.compile(r"^([a-zđ])\)\s+", re.I)),
]
LEVEL = {kind: index for index, (kind, _) in enumerate(PATTERNS)}


def parse(normalized, document_id, document_version_id):
    text = normalized["text"]
    units, audits, stack, seen = [], [], [], set()
    offset = 0
    for line in text.splitlines(keepends=True):
        trimmed = line.lstrip(" \t\u00a0")
        candidate = next(((kind, pattern.match(trimmed)) for kind, pattern in PATTERNS if pattern.match(trimmed)), None)
        if candidate:
            kind, match = candidate
            level = LEVEL[kind]
            parents = [unit for unit in stack if LEVEL[unit["unit_type"]] < level]
            parent = parents[-1] if parents else None
            required = {"clause": "article", "point": "clause"}.get(kind)
            if required and (parent is None or parent["unit_type"] != required):
                audits.append({"code": "orphan_heading", "offset": offset, "line": trimmed.rstrip()})
            else:
                label = match.group(1).lower()
                path = (parent["unit_id"] if parent else document_id) + f"/{kind}-{label}"
                if path in seen:
                    audits.append({"code": "duplicate_heading", "offset": offset, "unit_id": path})
                else:
                    if kind in {"article", "clause"} and label.isdigit():
                        siblings = [u for u in units if u["parent_id"] == (parent["unit_id"] if parent else None) and u["unit_type"] == kind]
                        if siblings and siblings[-1]["label"].isdigit() and int(label) != int(siblings[-1]["label"]) + 1:
                            audits.append({"code": "sequence_gap", "offset": offset, "unit_id": path})
                    unit = {"schema_version": VERSION, "unit_id": path, "unit_version_id": "", "document_id": document_id, "document_version_id": document_version_id, "parent_id": parent["unit_id"] if parent else None, "unit_type": kind, "label": label, "text": "", "normalized_sha256": "", "source_start": offset, "source_end": 0, "source_locator": normalized["source_locator"]}
                    units.append(unit)
                    stack = parents + [unit]
                    seen.add(path)
        offset += len(line)
    for index, unit in enumerate(units):
        end = units[index + 1]["source_start"] if index + 1 < len(units) else len(text)
        unit.update(source_end=end, text=text[unit["source_start"]:end])
        unit["normalized_sha256"] = text_hash(unit["text"])
        unit["unit_version_id"] = unit_version(unit)
    unassigned_end = units[0]["source_start"] if units else len(text)
    return {"units": units, "audit": audits, "unassigned_text": text[:unassigned_end], "unassigned_span": [0, unassigned_end]}
