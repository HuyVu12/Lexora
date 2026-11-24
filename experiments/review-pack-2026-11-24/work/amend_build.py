"""Build data/amendment.json of the review pack from experiments/amendment-check-v3/check-sheet.csv.

Offline, no model. Reads the sheet, the edges (data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl), the corpus v3
units and the amending texts rebuilt by amend_texts.py (work/amend-texts/), and the drafted verdicts of amend_verdicts.py.
Run from the workspace root: python experiments/review-pack-2026-11-24/work/amend_build.py
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PACK = WORK.parent
sys.path.insert(0, str(WORK))
from amend_verdicts import FOLLOW, REPLACE, V  # noqa: E402

SHEET = ROOT / "experiments/amendment-check-v3/check-sheet.csv"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
UNITS = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b/units.jsonl"
TEXTS = WORK / "amend-texts"

KIND_VI = {"modify": "Sửa đổi", "add": "Bổ sung", "repeal": "Bãi bỏ", "replace_phrase": "Thay cụm từ", "expire": "Hết hiệu lực (Điều, khoản)",
           "expire_document": "Hết hiệu lực (cả văn bản)", "expire_subject": "Hết hiệu lực (theo nội dung)"}
OPTIONS = [
    {"value": "dung", "label": "Đúng", "hint": "Đúng đích, đúng loại, đúng phạm vi; dòng ngoài corpus thì đích nêu đúng và đúng là không có trong corpus"},
    {"value": "sai_dich", "label": "Sai đích", "hint": "Đơn vị khác, văn bản khác, hoặc đích có trong corpus mà ghi là không giải được"},
    {"value": "sai_loai", "label": "Sai loại hoặc phạm vi", "hint": "Đúng đích nhưng sai loại lệnh hoặc sai phạm vi, ví dụ chỉ bãi bỏ một đoạn mà ghi bãi bỏ cả điểm"},
    {"value": "khac", "label": "Khác", "hint": "Dòng không phải câu lệnh, sai ngày, hoặc không quyết được; ghi rõ ở ghi chú"},
]
INSTRUCTIONS = "\n".join([
    "Mỗi mục là một cạnh sửa đổi do quy tắc đọc từ câu lệnh trong văn bản sửa đổi.",
    "Đọc câu lệnh, rồi so với cột đích mà quy tắc đọc được.",
    "Kiểm số điểm, khoản, Điều và tên văn bản có khớp câu lệnh không.",
    "Dòng đã giải được: đơn vị đích phải đúng là đơn vị câu lệnh nhắm tới.",
    "Lệnh thay cụm từ: cụm cũ phải có trong đơn vị đích.",
    "Dòng không giải được hoặc ngoài corpus: kiểm đích nêu đúng và đúng là không có trong corpus.",
    "So ngày hiệu lực với câu hiệu lực của văn bản sửa đổi.",
    "Chỉ so chữ, không cần nhận định pháp lý.",
    "Gợi ý là của model; khi không chắc, chọn Khác và ghi lý do.",
])
EFFECT = re.compile(r"[^\n]*này có hiệu lực thi hành (?:kể )?từ ngày (\d+) tháng (\d+) năm (\d{4})[^\n]*")
NUMBER = re.compile(r"\d+/\d{4}/[A-ZĐa-zđ0-9]+(?:-[A-ZĐa-zđ0-9]+)*")


def short(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n].rstrip() + " ..."


def doc_label(document_id):
    if not document_id:
        return "(không đọc được)"
    parts = document_id.split("-")
    if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
        rest = "-".join(parts[2:]).upper().replace("ND-CP", "NĐ-CP").replace("BLDTBXH", "BLĐTBXH")
        return f"số {parts[0]}/{parts[1]}/{rest}"
    return document_id


def target_label(target):
    if not target:
        return ""
    bits = []
    if target.get("point"):
        bits.append(f"điểm {target['point']}")
    if target.get("clause"):
        bits.append(f"khoản {target['clause']}")
    if target.get("article"):
        bits.append(f"Điều {target['article']}")
    return " ".join(bits)


def effect_line(text):
    m = EFFECT.search(text)
    return (m.group(0).strip(), f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}") if m else ("", "")


def lead_context(text, start):
    """Article heading and the numbered lead line before an instruction, from the amending text."""
    before = text[:start].split("\n")
    current = text[text.rfind("\n", 0, start) + 1:text.find("\n", start) if text.find("\n", start) >= 0 else len(text)]
    lines = []
    for line in reversed(before[:-1]):
        if re.match(r"Điều\s+\d+[a-zđ]?\.\s", line):
            lines.append(line.strip())
            break
        if re.match(r"\s*[a-zđ]\)\s", current) and re.match(r"\s*\d+[a-zđ]?\.\s", line) and len(lines) == 0:
            lines.append(line.strip())
    return list(reversed(lines)), current.strip()


def present(phrases, text):
    return [p for p in phrases if p and p in text]


def main():
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig", newline="")))
    columns = list(rows[0].keys())
    edges = {e["edge_id"]: e for e in map(json.loads, EDGES.open(encoding="utf-8"))}
    units = {u["unit_id"]: u for u in map(json.loads, UNITS.open(encoding="utf-8"))}
    texts = {p.stem: p.read_text(encoding="utf-8") for p in TEXTS.glob("*.txt")}
    if len(rows) != 100 or set(V) != set(range(len(rows))):
        raise SystemExit("sheet rows and drafted verdicts do not match")
    items, problems = [], []
    for n, row in enumerate(rows):
        key, verdict, confidence, note = V[n]
        if row["edge_key"] != key:
            raise SystemExit(f"row {n}: edge_key {row['edge_key']} != {key}")
        edge = edges[key]
        text = texts[edge["amending_document_id"]]
        instruction = edge["instruction"]["text"]
        if text[edge["instruction"]["start"]:edge["instruction"]["end"]] != instruction:
            raise SystemExit(f"row {n}: instruction offsets do not match the rebuilt text")
        context, line = lead_context(text, edge["instruction"]["start"])
        eff_line, eff_date = effect_line(text)
        if eff_date != row["effective_from"]:
            problems.append((n, f"effective_from {row['effective_from']} != {eff_date}"))
        target = edge.get("target") or {}
        tlabel = target_label(target)
        tdoc = doc_label(edge.get("target_document_id"))
        status, kind = edge["status"], edge["kind"]
        phrases = [p[0] for p in edge.get("phrases") or []]
        tt = row["target_text"]

        # Generic reason, literal and short.
        if status in ("resolved", "resolved_parent") and kind == "replace_phrase":
            found = present(phrases, tt)
            reason = f"Câu lệnh thay cụm từ tại {tlabel}; cột target_text là {tlabel} của NĐ 152/2020 và có cụm cũ \"{found[0] if found else '?'}\"."
        elif status in ("resolved", "resolved_parent"):
            reason = f"Câu lệnh \"{short(instruction, 90)}\" nêu {tlabel}; cột target_text là \"{short(tt, 90)}\"."
            if row["new_wording_text"] and status == "resolved" and kind != "repeal":
                nw = row["new_wording_text"]
                quote = nw[nw.find("\""):] if "\"" in nw else nw
                reason += f" Lời văn mới bắt đầu \"{short(quote.strip(chr(34)), 80)}\", thay cho cùng đơn vị."
        elif kind == "expire_document":
            reason = (f"Câu tuyên bố cả văn bản {doc_label(edge.get('target_document_id')) if edge.get('target_document_id') else ''} hết hiệu lực; "
                      + ("văn bản không có trong corpus v3 nên trạng thái ngoài corpus là đúng." if status == "external" else "văn bản có trong corpus v3."))
        elif kind == "expire_subject":
            reason = "Câu nêu phạm vi hết hiệu lực theo nội dung, không nêu Điều, khoản; quy tắc để không giải được là đúng."
        elif status == "external":
            reason = f"Câu lệnh nhắm {tlabel} của văn bản {tdoc}, đúng như cột target_named; văn bản này không có trong corpus v3 nên ghi ngoài corpus là đúng."
        elif edge.get("reason") == "annex_target":
            reason = "Câu lệnh nhắm phụ lục hoặc mẫu, không phải Điều, khoản trong corpus; ghi không giải được là đúng."
        else:
            reason = f"Câu lệnh nêu {tlabel} của văn bản {tdoc}."
        reason = note if n in REPLACE else (reason + " " + note).strip()
        if eff_line and eff_date == row["effective_from"]:
            reason += f" Ngày hiệu lực {row['effective_from']} khớp câu hiệu lực của văn bản sửa đổi."

        highlight_instr = present([tlabel, f"Điều {target.get('article')}" if target.get("article") else "", "hết hiệu lực", "Bãi bỏ", "Sửa đổi, bổ sung",
                                   "Bổ sung", "Thay thế cụm từ", "Thay thế", "tên", "đoạn mở đầu", "đoạn", "cụm từ", "Phụ lục", "Mẫu số", "Nội dung về"]
                                  + phrases + NUMBER.findall(instruction)[:3], instruction)
        fields = [{"label": "Câu lệnh (cột instruction)", "text": row["instruction"] if row["instruction"] == instruction else instruction, "highlight": highlight_instr}]
        if context:
            fields.append({"label": "Tên Điều và câu dẫn trong văn bản sửa đổi", "text": "\n".join(context), "highlight": NUMBER.findall("\n".join(context))[:2]})
        if line and line != instruction and len(line) > len(instruction) + 3:
            fields.append({"label": "Cả dòng chứa câu lệnh", "text": short(line, 1500), "highlight": present([instruction[:60]], line)})
        if n in FOLLOW:
            after, picked = text[edge["instruction"]["end"]:].split("\n")[1:], []
            for later in after:
                if re.match(r"Điều\s+\d+[a-zđ]?\.\s", later) or len(picked) == FOLLOW[n]:
                    break
                if re.match(r"\s*[a-zđ]\)\s+(?:Sửa đổi|Bổ sung|Bãi bỏ|Thay thế)", later):
                    picked.append(short(later, 300))
            fields.append({"label": "Các điểm ngay sau câu lệnh (văn bản sửa đổi)", "text": "\n".join(picked), "highlight": []})
        fields.append({"label": "Đơn vị chứa câu lệnh (cột amending_unit)", "text": row["amending_unit"], "highlight": []})
        named = f"{row['target_named']}\nLoại: {row['kind']}\nTrạng thái: {status}" + (f"\nLý do của quy tắc: {row['reason']}" if row["reason"] else "")
        fields.append({"label": "Đích quy tắc đọc được (cột target_named, kind, status)", "text": named, "highlight": present([tlabel, "chỉ tên hoặc câu dẫn"], named)})
        if row["target_unit"] and not row["target_unit"].startswith("("):
            fields.append({"label": "Đơn vị đích (cột target_unit)", "text": row["target_unit"], "highlight": present([tlabel], row["target_unit"])})
        elif row["target_unit"].startswith("(đơn vị cha"):
            fields.append({"label": "Đơn vị đích (cột target_unit)", "text": row["target_unit"], "highlight": ["đơn vị cha gần nhất; đích chưa có trong văn bản"]})
        if tt:
            parent = units.get(edge.get("target_unit_id") or edge.get("anchor_unit_id") or "")
            fields.append({"label": "Nguyên văn đơn vị đích (cột target_text)", "text": short(tt, 1500), "highlight": present(phrases, tt)})
        if row["new_wording_text"]:
            label = "Lời văn mới (cột new_wording_text)" if kind not in ("expire", "expire_document", "expire_subject") or status == "resolved" else "Nguyên văn đơn vị chứa câu (cột new_wording_text)"
            fields.append({"label": label, "text": short(row["new_wording_text"], 1500), "highlight": present(["hết hiệu lực"], row["new_wording_text"])})
        fields.append({"label": "Ngày hiệu lực (cột effective_from) và câu hiệu lực của văn bản sửa đổi", "text": f"{row['effective_from']}\n{eff_line}",
                       "highlight": present([row["effective_from"]] + re.findall(r"ngày \d+ tháng \d+ năm \d{4}", eff_line), f"{row['effective_from']}\n{eff_line}")})
        if status in ("resolved", "resolved_parent"):
            question = "Đích (đúng điểm, khoản, Điều, văn bản), loại lệnh và phạm vi của cạnh có khớp câu lệnh không?"
        elif kind == "expire_subject":
            question = "Câu có chỉ nêu phạm vi theo nội dung, không nêu Điều, khoản không?"
        elif kind == "expire_document":
            question = "Câu có tuyên bố cả văn bản được nêu hết hiệu lực không, và văn bản đó có đúng là " + ("có" if status == "document" else "không có") + " trong corpus không?"
        else:
            question = "Đích có được nêu đúng như câu lệnh, và có đúng là không có trong corpus không?"
        quotes = [{"label": f"Câu lệnh, {short(row['amending_unit'].split(' [')[0], 90)}", "text": short(instruction, 500)}]
        if tt:
            quotes.append({"label": f"Đơn vị đích, {short(row['target_unit'].split(' [')[0], 90)}", "text": short(tt, 400)})
        items.append({
            "id": key,
            "group": status,
            "heading": f"{KIND_VI.get(kind, kind)}: {short(row['target_named'], 70)}",
            "question": question,
            "fields": fields,
            "suggestion": {"value": verdict, "reason": reason, "confidence": confidence, "quotes": quotes},
            "export": {c: row[c] for c in columns},
        })
    for option in OPTIONS:
        option["csv"] = {"verdict": option["value"]}
    data = {
        "task": "amendment",
        "title": "Cạnh sửa đổi corpus v3 (100 cạnh)",
        "instructions": INSTRUCTIONS,
        "drafted_by": "claude-opus-5-5 (agent trong phiên, 24/11/2026)",
        "source": "experiments/amendment-check-v3/check-sheet.csv (amendment-rules-v2, data/kb/amendments-scope-v3-v48feefc6d53b-v2)",
        "export_columns": columns,
        "options": OPTIONS,
        "items": items,
    }
    out = PACK / "data" / "amendment.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = Counter(i["suggestion"]["value"] for i in items)
    low = [i["id"] for i in items if i["suggestion"]["confidence"] == "thấp"]
    print(out, dict(counts), "low:", low, "problems:", problems)
    return {"counts": dict(counts), "low_confidence": low, "problems": problems,
            "by_confidence": dict(Counter(i["suggestion"]["confidence"] for i in items))}


if __name__ == "__main__":
    main()
