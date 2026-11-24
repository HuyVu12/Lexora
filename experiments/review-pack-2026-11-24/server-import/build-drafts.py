"""Build the two question-drafts files (validity, link) for the shared annotation server from the model-drafted question files.

Offline. Output: validity-drafts.json (30) and link-drafts.json (35) next to this file. Question texts are copied unchanged
(every dated question already carries its date in the text); the as_of date, the stale units and the reason go into the rationale,
which only the annotator in proposal mode sees.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VALIDITY = ROOT / "experiments/question-drafts-validity-v1/questions.json"
LINK = ROOT / "experiments/runs/link-set-2026-11-23/questions.json"
CORPUS_LOCK = "2026-11-11"

def vn(date):
    y, m, d = date.split("-")
    return f"{d}/{m}/{y}"

GROUP_NOTE = {
    "expired_document": "Văn bản cũ (NĐ 12/2022) hết hiệu lực từ 10/09/2026 theo vbpl.vn; đơn vị tương ứng của NĐ 283/2026 là căn cứ hiện hành.",
    "unit_amendment": "Đơn vị gốc đã bị sửa đổi hoặc thay cụm từ; đáp án là đơn vị chứa lời văn mới, đơn vị bị sửa là lỗi thời ở ngày áp dụng (nếu ngày áp dụng sau ngày sửa có hiệu lực).",
    "past_date": "Câu ghi rõ ngày xảy ra việc; đáp án là quy định có hiệu lực ở ngày đó, không phải quy định hiện hành.",
    "control": "Câu đối chứng, không liên quan tới thay đổi hiệu lực.",
}

def validity():
    data = json.loads(VALIDITY.read_text(encoding="utf-8"))["questions"]
    out = []
    for q in data:
        parts = ["Đề xuất của model (Claude Opus 5.5, nháp 15/11/2026, dựng lại với amendment-rules-v2 ngày 16/11), không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.",
                 f"Ngày áp dụng: {vn(q['as_of'])}" + (" (ngày khóa corpus v3, câu không ghi ngày)." if q["as_of"] == CORPUS_LOCK else " (ngày nêu trong câu)."),
                 GROUP_NOTE[q["group"]]]
        if q["stale_unit_ids"]:
            parts.append("Đơn vị lỗi thời ở ngày áp dụng, KHÔNG chọn làm đáp án: " + ", ".join(q["stale_unit_ids"]) + ".")
        if q.get("not_yet_effective_unit_ids"):
            parts.append("Đơn vị chưa có hiệu lực ở ngày áp dụng, KHÔNG chọn làm đáp án: " + ", ".join(q["not_yet_effective_unit_ids"]) + ".")
        parts.append("Căn cứ của model: " + q["rationale"])
        out.append({"text": q["question"], "question_type": q["question_type"], "expected_status": q["expected_status"],
                    "relevant_unit_ids": q["relevant_unit_ids"], "rationale": " ".join(parts), "paraphrase_of": None, "source_question_id": q["question_id"]})
    return out

LINK_NOTE = {
    "a": "Loại a: luật dẫn nghị định hướng dẫn chi tiết.",
    "b": "Loại b: chế tài và thẩm quyền xử phạt.",
    "c": "Loại c: dẫn chiếu trong cùng văn bản.",
    "d": "Loại d: sửa đổi, bổ sung (chọn đơn vị sửa đổi cộng phần còn hiệu lực của đơn vị gốc).",
    "none": "Câu đối chứng: chỉ cần một đơn vị lá, không có đơn vị liên kết.",
}

def link():
    data = json.loads(LINK.read_text(encoding="utf-8"))["questions"]
    out = []
    for q in data:
        parts = ["Đề xuất của model (agent Claude, nháp 23/11/2026), không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.",
                 f"Ngày áp dụng: {vn(q['as_of'])} (ngày khóa corpus v3, câu không ghi ngày); mọi đơn vị đề xuất còn hiệu lực ngày này.",
                 LINK_NOTE[q["link_type"]]]
        if q["link_target_unit_ids"]:
            parts.append("Đơn vị liên kết B (cần để trả lời đủ, phải có trong nhãn): " + ", ".join(q["link_target_unit_ids"]) + ".")
        if q.get("stale_note"):
            parts.append("Lưu ý hiệu lực: " + q["stale_note"])
        parts.append("Đáp án tham chiếu của model: " + q["reference_answer"])
        out.append({"text": q["question"], "question_type": "lookup" if q["link_type"] == "none" else "synthesis", "expected_status": q["expected_status"],
                    "relevant_unit_ids": q["relevant_unit_ids"], "rationale": " ".join(parts), "paraphrase_of": None, "source_question_id": q["question_id"]})
    return out

if __name__ == "__main__":
    for name, items in (("validity-drafts.json", validity()), ("link-drafts.json", link())):
        (HERE / name).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, len(items))
