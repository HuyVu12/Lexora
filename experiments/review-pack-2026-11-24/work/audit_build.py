"""Build data/audit.json of the review pack: the blinded rejection audit (104 claims) with drafted labels.

Offline, no model. Reads only blinded inputs: experiments/runs/audit-rejections-v1/sheet.csv and the `items` column of
audit set a18ba17ef7635 in data/kb/vm-lexora-20261124.sqlite (opened read-only; the `key` column, audit_final and key.json
are never read), plus the corpus v1 units for the unit labels. Labels come from audit_verdicts.py.
Run from the workspace root: python experiments/review-pack-2026-11-24/work/audit_build.py
"""

import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PACK = WORK.parent
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(ROOT / "src"))
from audit_verdicts import A  # noqa: E402
from legal_ai.evaluation.rejection_audit import COLUMNS, LABELS  # noqa: E402

SHEET = ROOT / "experiments/runs/audit-rejections-v1/sheet.csv"
STORE = ROOT / "data/kb/vm-lexora-20261124.sqlite"
SET_ID = "a18ba17ef7635"
UNITS = ROOT / "data/normalized/experiment-scope-v1-veaeaad4a6edc/units.jsonl"
FIELDS = ("context", "unit_text", "sentence", "norm")
DOCS = {"45-2019-qh14": "Bộ luật Lao động 2019", "145-2020-nd-cp": "NĐ 145/2020/NĐ-CP", "12-2022-nd-cp": "NĐ 12/2022/NĐ-CP",
        "10-2020-tt-bldtbxh": "TT 10/2020/TT-BLĐTBXH", "293-2025-nd-cp": "NĐ 293/2025/NĐ-CP"}
OPTIONS = [
    {"value": "sai", "label": "Sai", "hint": "Nói điều luật không nói, mâu thuẫn, sai chủ thể, sai tính quy phạm, bỏ mất điều kiện, ngoại lệ hoặc phủ định làm đổi nghĩa"},
    {"value": "dien_dat", "label": "Đúng, diễn đạt lại", "hint": "Đúng nghĩa nhưng giá trị bị viết lại, rút gọn hoặc ghép từ nhiều chỗ, không còn nguyên văn"},
    {"value": "dung_ngu_canh", "label": "Đúng, mượn câu dẫn", "hint": "Đúng, nhưng có chữ lấy từ câu dẫn của khoản, tên Điều hoặc câu khác thay vì từ chính câu"},
    {"value": "dung", "label": "Đúng, nguyên văn", "hint": "Đúng và mọi chữ nằm nguyên văn trong câu"},
    {"value": "khong_ro", "label": "Không rõ", "hint": "Không quyết định được; ghi lý do vào ghi chú"},
]
INSTRUCTIONS = "\n".join([
    "Mỗi mục là một quy phạm do model trích từ một câu luật.",
    "Bảng che tên model và việc quy phạm bị loại hay được giữ.",
    "Đọc tên Điều, câu dẫn và câu được trích, rồi so từng ô của quy phạm.",
    "Hỏi lần lượt: tính quy phạm, chủ thể, có thêm điều luật không nói, có bỏ mất ý làm đổi nghĩa.",
    "Nếu đúng nghĩa, xem chữ lấy từ đâu: câu dẫn, viết lại, hay nguyên văn.",
    "Nhiều nhãn cùng đúng thì chọn nhãn đứng trước trong danh sách.",
    "Ô để trống không phải lỗi, trừ khi thiếu nó thì sai nghĩa.",
    "Gợi ý là của model; khi không chắc, chọn Không rõ và ghi lý do.",
])


def unit_label(unit_id):
    doc = unit_id.split("/")[0]
    bits = dict(re.findall(r"(article|clause|point)-([^/]+)", unit_id))
    parts = [f"điểm {bits['point']}" if "point" in bits else "", f"khoản {bits['clause']}" if "clause" in bits else "",
             f"Điều {bits['article']}" if "article" in bits else ""]
    return " ".join(p for p in parts if p) + f", {DOCS.get(doc, doc)}"


def app_items():
    db = sqlite3.connect(f"file:{STORE.as_posix()}?mode=ro", uri=True)
    try:
        row = db.execute("SELECT items FROM audit_sets WHERE id = ?", (SET_ID,)).fetchone()
    finally:
        db.close()
    return json.loads(row[0])


def main():
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig", newline="")))
    items_app = app_items()
    if [i["item_id"] for i in items_app] != [r["item_id"] for r in rows] or any(
            a[f] != r[f] for a, r in zip(items_app, rows) for f in FIELDS):
        raise SystemExit("sheet.csv and the app set differ")
    if set(A) != {r["item_id"] for r in rows}:
        raise SystemExit("drafted labels do not cover the sheet exactly")
    by_text = {}
    for unit in map(json.loads, UNITS.open(encoding="utf-8")):
        by_text.setdefault(unit["text"].strip(), []).append(unit["unit_id"])
    items, missing_hl = [], []
    for row in rows:
        label, confidence, reason, phrases = A[row["item_id"]]
        if label not in LABELS:
            raise SystemExit(f"{row['item_id']}: label {label}")
        candidates = by_text.get(row["unit_text"].strip(), [])
        article = re.match(r"Điều (\d+)", row["context"] or row["unit_text"])
        if len(candidates) > 1 and article:
            candidates = [c for c in candidates if f"/article-{article.group(1)}/" in c + "/"] or candidates
        unit = unit_label(candidates[0]) if candidates else "(không tìm được đơn vị)"
        texts = {f: row[f] for f in FIELDS}
        for p in phrases:
            if not any(p in t for t in texts.values()):
                missing_hl.append((row["item_id"], p))
        hl = lambda t: [p for p in phrases if p in t]  # noqa: E731
        fields = [{"label": "Đơn vị", "text": unit + (f"\n{candidates[0]}" if candidates else ""), "highlight": []}]
        if row["context"]:
            fields.append({"label": "Tên Điều và câu dẫn", "text": row["context"], "highlight": hl(row["context"])})
        if row["unit_text"].strip() != row["sentence"].strip():
            fields.append({"label": "Nguyên văn đơn vị", "text": row["unit_text"], "highlight": hl(row["unit_text"])})
        fields.append({"label": "Câu được trích xuất", "text": row["sentence"], "highlight": hl(row["sentence"])})
        fields.append({"label": "Quy phạm model đưa ra", "text": row["norm"], "highlight": hl(row["norm"])})
        first = row["norm"].split("\n")[0].replace("Tính quy phạm: ", "")
        items.append({
            "id": row["item_id"],
            "group": "",
            "heading": f"{unit} ({first})",
            "question": "Quy phạm có đúng với luật không (đọc cả câu dẫn), và nếu đúng thì chữ lấy từ đâu?",
            "fields": fields,
            "suggestion": {"value": label, "reason": reason, "confidence": confidence,
                           "quotes": [{"label": f"Câu, {unit}", "text": row["sentence"]}] + ([{"label": "Câu dẫn", "text": row["context"].split("\n")[-1]}] if row["context"] else [])},
            "export": {c: row.get(c, "") for c in COLUMNS},
        })
    for item in items:
        unit = item["fields"][0]["text"].split("\n")[0]
        m = re.search(r"Điều (\d+), (.+)$", unit)
        item["group"] = f"{m.group(2)} Điều {m.group(1)}" if m else unit
    data = {
        "task": "audit",
        "title": "Kiểm tra quy phạm bị loại (104 quy phạm, bảng mù)",
        "instructions": INSTRUCTIONS,
        "drafted_by": "claude-opus-5-5 (agent trong phiên, 24/11/2026), không đọc khóa (key.json, cột key, audit_final)",
        "source": f"experiments/runs/audit-rejections-v1/sheet.csv = bộ {SET_ID} trong data/kb/vm-lexora-20261124.sqlite; nhãn nhập cho huyvu qua scripts/review_pack/convert.py audit",
        "export_columns": list(COLUMNS),
        "options": [o | {"csv": {"label": o["value"]}} for o in OPTIONS],
        "items": items,
    }
    out = PACK / "data" / "audit.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = Counter(i["suggestion"]["value"] for i in items)
    low = [i["id"] for i in items if i["suggestion"]["confidence"] == "thấp"]
    print(out, dict(counts), "low:", len(low), "missing highlights:", missing_hl)
    return {"counts": dict(counts), "low_confidence": low, "by_confidence": dict(Counter(i["suggestion"]["confidence"] for i in items)),
            "missing_highlights": missing_hl}


if __name__ == "__main__":
    main()
