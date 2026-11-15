"""Check sheet for amendment edges (`amendment-check-v1`): two people compare every edge of an `amendment-build` run
with the source text, and the thesis reports how many edges are correct, wrong or unresolved (research plan WP4.2).

`make_sheet` writes one CSV row per edge, in the order of `edges.jsonl`, resolved or not: a stable edge key, status,
kind and effective date, the unit holding the amending instruction and the verbatim instruction, the target the rules
read from it and the corpus unit it resolved to (with its text), the unit holding the new wording (with its text), and
two empty columns for the checker: `verdict` and `note`. Nothing is hidden from the checker, so there is no key file:
judging an edge needs the whole edge. The CSV is UTF-8 with a BOM so spreadsheet apps read Vietnamese correctly.

Verdicts, one per row:
- `dung`: the instruction really amends what the row says (for an unresolved or external row: the named target is
  indeed not a unit of the corpus; for `expire_document`: the statement ends the whole named document; for
  `expire_subject`: the statement scopes by subject matter, not by named units);
- `sai_dich`: wrong target (another unit, another document, or a target that does exist in the corpus);
- `sai_loai`: right target, wrong kind (for example a repeal recorded as a modification);
- `khac`: anything else (not an amending instruction at all, a wrong date, cannot decide), explained in `note`.

`score_sheet` counts verdicts per status and kind; `agreement` compares two filled sheets of the same edges: raw
agreement and Cohen's kappa on the four verdicts and on correct / not correct, with the disagreeing edge keys.
Rules only, offline; the verdicts are human checks of text, never a legal judgment by the tool.
"""

import csv
import json
from pathlib import Path
import re

from legal_ai.common.io import read_jsonl
from legal_ai.research.questions import kappa

CHECK_VERSION = "amendment-check-v1"
VERDICTS = ("dung", "sai_dich", "sai_loai", "khac")
COLUMNS = ["edge_key", "status", "kind", "effective_from", "amending_unit", "instruction", "target_named", "target_unit",
           "target_text", "new_wording_unit", "new_wording_text", "reason", "verdict", "note"]
KIND_NAMES = {"modify": "modify (sửa đổi, bổ sung)", "add": "add (bổ sung)", "repeal": "repeal (bãi bỏ)",
              "replace_phrase": "replace_phrase (thay thế cụm từ)", "expire": "expire (hết hiệu lực: Điều, khoản được nêu)",
              "expire_document": "expire_document (hết hiệu lực: cả văn bản)",
              "expire_subject": "expire_subject (hết hiệu lực: theo nội dung, không nêu Điều, khoản)"}
SCOPE_NAMES = {"own_text": "; chỉ tên hoặc câu dẫn, không thay các điểm, khoản bên dưới", "phrase": "; chỉ đơn vị chứa cụm từ cũ"}
_LABELS = {"article": "Điều", "clause": "khoản", "point": "điểm"}
_NUMBER = re.compile(r"^.*?số\s+\d+/\d{4}/\S+")


def _short_title(document_id, documents):
    document = documents.get(document_id)
    if document is None:
        return document_id or "?"
    found = _NUMBER.match(document.get("title") or "")
    return found.group(0) if found else document.get("title") or document_id


def unit_path(unit_id, units, documents):
    """"điểm a khoản 3 Điều 3, Nghị định số 152/2020/NĐ-CP [unit ID]": labels and the document number, never invented."""
    parts, current = [], units.get(unit_id)
    while current:
        if current["unit_type"] in _LABELS:
            parts.append(f"{_LABELS[current['unit_type']]} {current['label']}")
        current = units.get(current["parent_id"])
    document = units[unit_id]["document_id"]
    return f"{' '.join(parts) or unit_id}, {_short_title(document, documents)} [{unit_id}]"


def _named(edge, documents):
    target = edge.get("target")
    if not target:
        return f"(không đọc được đích), {_short_title(edge.get('target_document_id'), documents)}"
    labels = [f"{_LABELS[key]} {target[key]}" for key in ("point", "clause", "article") if target.get(key)]
    return f"{' '.join(labels)}, {_short_title(edge.get('target_document_id'), documents)}"


def _instruction_unit(edge, units):
    """The unit holding the instruction: the linked amending unit, else the one leaf-most unit of the amending document
    whose text contains the instruction verbatim, else None (the amending article is not in the corpus)."""
    if edge.get("amending_unit_id") in units:
        return edge["amending_unit_id"]
    doc, text = edge["amending_document_id"], edge["instruction"]["text"]
    found = [u for u in units.values() if u["document_id"] in (doc, f"{doc}-sua-doi") and text in u["text"]]
    deepest = [u for u in found if not any(o is not u and o["unit_id"].startswith(u["unit_id"] + "/") for o in found)]
    return deepest[0]["unit_id"] if len(deepest) == 1 else None


def rows(edges, units, documents):
    """One check row per edge, in the order given."""
    out = []
    for edge in edges:
        amending = _instruction_unit(edge, units)
        target = edge.get("target_unit_id") or edge.get("anchor_unit_id")
        if edge["kind"] in ("expire_document", "expire_subject"):
            target_unit = "(cả văn bản)" if edge["kind"] == "expire_document" else "(không xác định được Điều, khoản bằng quy tắc)"
        elif edge.get("target_unit_id") in units:
            target_unit = unit_path(target, units, documents)
        elif target in units:
            target_unit = f"(đơn vị cha gần nhất; đích chưa có trong văn bản) {unit_path(target, units, documents)}"
        else:
            target_unit = "(không có trong corpus)"
        wording = edge.get("amending_unit_id")
        kind = KIND_NAMES.get(edge["kind"], edge["kind"])
        if SCOPE_NAMES.get(edge.get("scope")) and kind.endswith(")"):
            kind = kind[:-1] + SCOPE_NAMES[edge["scope"]] + ")"
        out.append({"edge_key": edge["edge_id"], "status": edge["status"], "kind": kind,
                    "effective_from": edge.get("effective_from") or "",
                    "amending_unit": unit_path(amending, units, documents) if amending else
                    f"(Điều sửa đổi không có trong corpus), {_short_title(edge['amending_document_id'], documents)}",
                    "instruction": edge["instruction"]["text"], "target_named": _named(edge, documents), "target_unit": target_unit,
                    "target_text": units[target]["text"].strip() if target in units else "",
                    "new_wording_unit": unit_path(wording, units, documents) if wording in units else "",
                    "new_wording_text": units[wording]["text"].strip() if wording in units else "",
                    "reason": edge.get("reason") or "", "verdict": "", "note": ""})
    return out


def make_sheet(edges_dir, sheet_path, bundle=None):
    """Write the check CSV of one `amendment-build` run; `bundle` defaults to the one its manifest names."""
    edges_dir = Path(edges_dir)
    manifest = json.loads((edges_dir / "manifest.json").read_text(encoding="utf-8"))
    bundle = Path(bundle or manifest["bundle"])
    units = {u["unit_id"]: u for u in read_jsonl(bundle / "units.jsonl")}
    documents = {d["document_id"]: d for d in read_jsonl(bundle / "documents.jsonl")}
    sheet = rows(read_jsonl(edges_dir / "edges.jsonl"), units, documents)
    if Path(sheet_path).exists():
        raise ValueError("sheet exists: write a new file so filled sheets are never overwritten")
    with Path(sheet_path).open("w", encoding="utf-8-sig", newline="") as handle:  # BOM so spreadsheet apps read UTF-8.
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(sheet)
    statuses = {}
    for row in sheet:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    return {"check_version": CHECK_VERSION, "edges": len(sheet), "by_status": dict(sorted(statuses.items())),
            "edge_version": manifest.get("edge_version"), "bundle": bundle.as_posix()}


def read_sheet(sheet_path):
    """{edge key: row} of a filled sheet; an empty verdict is None, an unknown one is an error."""
    found = {}
    with Path(sheet_path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            verdict = (row.get("verdict") or "").strip()
            if verdict and verdict not in VERDICTS:
                raise ValueError(f"{row['edge_key']}: verdict {verdict!r} is not one of {list(VERDICTS)}")
            if row["edge_key"] in found:
                raise ValueError(f"duplicate edge key {row['edge_key']}")
            found[row["edge_key"]] = row | {"verdict": verdict or None}
    return found


def score_rows(sheet):
    """Verdict counts overall, per status and per kind, and the share of checked edges found correct."""
    def group():
        return {"edges": 0, "checked": 0, "verdicts": {}}
    total, by_status, by_kind = group(), {}, {}
    for row in sheet.values():
        for bucket in (total, by_status.setdefault(row["status"], group()), by_kind.setdefault(row["kind"].split(" ")[0], group())):
            bucket["edges"] += 1
            if row["verdict"]:
                bucket["checked"] += 1
                bucket["verdicts"][row["verdict"]] = bucket["verdicts"].get(row["verdict"], 0) + 1
    for bucket in [total, *by_status.values(), *by_kind.values()]:
        bucket["correct_rate"] = {"value": bucket["verdicts"].get("dung", 0) / bucket["checked"] if bucket["checked"] else None,
                                  "n": bucket["checked"]}
    return {"check_version": CHECK_VERSION, **total, "by_status": dict(sorted(by_status.items())), "by_kind": dict(sorted(by_kind.items()))}


def score_sheet(sheet_path):
    return score_rows(read_sheet(sheet_path))


def agreement_rows(first, second):
    """Raw agreement and Cohen's kappa over edges both checkers labelled, on the four verdicts and on correct or not."""
    keys = [k for k in first if k in second and first[k]["verdict"] and second[k]["verdict"]]
    a, b = [first[k]["verdict"] for k in keys], [second[k]["verdict"] for k in keys]
    correct_a, correct_b = [x == "dung" for x in a], [x == "dung" for x in b]
    return {"n": len(keys), "only_in_one_sheet": len(set(first) ^ set(second)),
            "verdicts": {"raw_agreement": sum(x == y for x, y in zip(a, b)) / len(keys) if keys else None, "kappa": kappa(a, b)},
            "correct_or_not": {"raw_agreement": sum(x == y for x, y in zip(correct_a, correct_b)) / len(keys) if keys else None,
                               "kappa": kappa(correct_a, correct_b)},
            "disagreements": [{"edge_key": k, "first": first[k]["verdict"], "second": second[k]["verdict"]} for k in keys
                              if first[k]["verdict"] != second[k]["verdict"]]}


def agreement(first_sheet, second_sheet):
    return agreement_rows(read_sheet(first_sheet), read_sheet(second_sheet))
