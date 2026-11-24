"""Build data/validity.json and data/link.json of the 24/11/2026 review pack, plus work/check-summary.json.

Suggestions are drafted by a Claude agent (Opus 5.5, in-session, 24/11/2026) from the frozen corpus v3 bundle only:
unit texts and document dates from data/normalized/experiment-scope-v3-v48feefc6d53b, unit status from
legal_ai.kb.validity (unit-status-v2) with the amendment-rules-v2 edges. No network, no model calls.

Run from the workspace root: python experiments/review-pack-2026-11-24/work/build_checks.py
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import Validity  # noqa: E402

PACK = ROOT / "experiments/review-pack-2026-11-24"
BUNDLE = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
EDGES = ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl"
VAL_DIR = ROOT / "experiments/question-drafts-validity-v1"
LINK_DIR = ROOT / "experiments/runs/link-set-2026-11-23"
DRAFTED_BY = "claude-opus-5-5 (agent trong phiên, 24/11/2026)"

docs = [json.loads(line) for line in open(BUNDLE / "documents.jsonl", encoding="utf-8")]
unit_list = [json.loads(line) for line in open(BUNDLE / "units.jsonl", encoding="utf-8")]
edges = [json.loads(line) for line in open(EDGES, encoding="utf-8")]
UNITS = {u["unit_id"]: u for u in unit_list}
DOCS = {d["document_id"]: d for d in docs}
V = Validity(docs, unit_list, edges)
STATUS_VI = {"in_force": "còn hiệu lực", "amended": "đã bị sửa đổi", "expired": "hết hiệu lực", "repealed": "bị bãi bỏ",
             "not_yet_effective": "chưa có hiệu lực", "unknown": "chưa rõ"}
SHORT_DOC = {"12-2022-nd-cp": "NĐ 12/2022", "283-2026-nd-cp": "NĐ 283/2026", "152-2020-nd-cp": "NĐ 152/2020",
             "70-2023-nd-cp": "NĐ 70/2023", "84-2015-qh13": "Luật ATVSLĐ 84/2015", "41-2024-qh15": "Luật BHXH 41/2024",
             "41-2024-qh15-sua-doi": "Luật BHXH 41/2024", "45-2019-qh14": "BLLĐ 45/2019", "145-2020-nd-cp": "NĐ 145/2020",
             "219-2025-nd-cp": "NĐ 219/2025", "10-2020-tt-bldtbxh": "TT 10/2020"}


def text(uid):
    return UNITS[uid]["text"].strip()


def label(uid):
    return V.describe(uid)


def doc_dates(doc_id):
    d = DOCS[doc_id]
    out = f"{d['title']}: hiệu lực từ {d['effective_from']}"
    if d.get("effective_to"):
        out += f", hết hiệu lực từ {d['effective_to']}"
    return out + " (theo vbpl.vn)"


def hl(field_text, phrases):
    """Keep only phrases that occur verbatim in the field text, in order, without duplicates."""
    seen, out = set(), []
    for p in phrases:
        if p and p in field_text and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def instruction_phrases(t):
    return re.findall(r"(?:Sửa đổi, bổ sung|Bổ sung|Thay thế cụm từ) [^:\"“]+?(?= như sau|:|\")", t)


def quote_parts(cell):
    return [re.sub(r"^\((?:cụm chữ chung của cặp|câu dẫn)\) ", "", p).strip() for p in cell.split("\n") if p.strip()]


# --------------------------------------------------------------------------------------------------------------
# Validity set
# --------------------------------------------------------------------------------------------------------------

ART7 = "283-2026-nd-cp/chapter-i/article-7/clause-1"
ART6 = "12-2022-nd-cp/chapter-i/article-6/clause-1"
ORG = "Mức phạt tiền đối với tổ chức bằng 02 lần mức phạt tiền đối với cá nhân."

# Per question of the expired_document group: situation phrase, decisive phrase of the answer unit, lead phrase, Article.
EXPIRED = {
    "hl-a01": ("15 công nhân", "từ 11 người đến 50 người lao động",
               "giao kết hợp đồng lao động không bằng văn bản với người lao động làm công việc có thời hạn từ đủ 01 tháng trở lên", "Điều 15"),
    "hl-a02": ("80%", "thấp hơn 85% mức lương của công việc đó", "Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng", "Điều 16"),
    "hl-a03": ("8 lao động", "Từ 20.000.000 đồng đến 30.000.000 đồng đối với vi phạm từ 01 người đến 10 người lao động",
               "trả lương cho người lao động thấp hơn mức lương tối thiểu do Chính phủ quy định", "Điều 23"),
    "hl-a04": ("60 công nhân", "từ 51 người đến 100 người lao động",
               "huy động người lao động làm thêm giờ vượt quá số giờ theo quy định của pháp luật", "Điều 24"),
    "hl-a05": ("chậm đóng bảo hiểm xã hội bắt buộc", "tối đa không quá 75.000.000 đồng",
               "Phạt tiền từ 12% đến 15% tổng số tiền chậm đóng bảo hiểm xã hội bắt buộc", "Điều 43"),
    "hl-a06": ("giữ bản gốc bằng đại học", "Giữ bản chính giấy tờ tùy thân, văn bằng hoặc chứng chỉ của người lao động",
               "Phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng", "Điều 15"),
    "hl-a07": ("trừ 500.000 đồng tiền lương", "Dùng hình thức phạt tiền hoặc cắt lương thay việc xử lý kỷ luật lao động",
               "Phạt tiền từ 20.000.000 đồng đến 40.000.000 đồng", "Điều 25"),
    "hl-a08": ("25 nhân viên", "Không có nội quy lao động bằng văn bản khi sử dụng từ 10 lao động trở lên",
               "Phạt tiền từ 5.000.000 đồng đến 10.000.000 đồng", "Điều 25"),
    "hl-a09": ("con 8 tháng tuổi", "Không cho lao động nữ trong thời gian nuôi con dưới 12 tháng tuổi nghỉ 60 phút mỗi ngày",
               "Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng", "Điều 26"),
    "hl-a10": ("không bố trí cho nhân viên nghỉ hằng năm", "nghỉ hằng tuần hoặc nghỉ hằng năm hoặc nghỉ lễ, tết",
               "Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng", "Điều 24"),
}

# Hand-written reasons per sheet row (index in check-sheet.csv). Rows not listed use the templates below.
# value: co | khong | khong_chac ; conf: cao | vừa | thấp ; extra: highlight phrases.
VAL_ROWS = {
    16: dict(conf="vừa", reason=(
        "NĐ 283/2026 có hiệu lực từ 2026-09-10, trước ngày áp dụng 2026-11-11. "
        "Khoản 3 Điều 43 ghi \"Phạt tiền từ 12% đến 15% tổng số tiền chậm đóng bảo hiểm xã hội bắt buộc tại thời điểm lập biên bản vi phạm hành chính nhưng tối đa không quá 75.000.000 đồng\", trả lời cả cách tính và mức tối đa. "
        "Lưu ý: khoản 1 cùng Điều ghi \"Phạt cảnh cáo đối với các hành vi quy định tại khoản 3 Điều này khi số tiền vi phạm ... dưới 400.000 đồng\", chưa có trong tập đáp án; đơn vị đúng nhưng tập đáp án có thể thiếu khoản 1."),
        quotes=[("khoản 1 Điều 43 NĐ 283/2026", "283-2026-nd-cp/chapter-iii/article-43/clause-1")]),
    40: dict(reason=(
        "Luật BHXH 41/2024 có hiệu lực từ 2025-07-01, trước 2026-11-11. Khoản 1 Điều 139 ghi \"Sửa đổi, bổ sung một số điều của Luật An toàn, vệ sinh lao động số 84/2015/QH13\" và điểm b \"Sửa đổi, bổ sung khoản 1 Điều 43\"; "
        "lời văn mới nêu đối tượng là người lao động \"theo quy định tại các điểm a, b, c, d, đ, e, i và l khoản 1 Điều 2\" của Luật Bảo hiểm xã hội, đúng điều câu hỏi hỏi."),
        extra=["các điểm a, b, c, d, đ, e, i và l khoản 1 Điều 2", "Sửa đổi, bổ sung khoản 1 Điều 43"]),
    41: dict(conf="vừa", reason=(
        "Luật BHXH 41/2024 có hiệu lực từ 2025-07-01, còn hiệu lực tại 2026-11-11. "
        "Đơn vị chỉ là câu dẫn \"Người lao động là công dân Việt Nam thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc bao gồm:\"; danh sách nằm ở các điểm con. "
        "Lời văn mới của khoản 1 Điều 43 dẫn tới \"các điểm a, b, c, d, đ, e, i và l khoản 1 Điều 2\", nên đơn vị này cần. "
        "Lưu ý: chỉ số đánh giá mở một khoản thành mọi điểm con, kể cả g, h, k, m, n không thuộc danh sách; nếu muốn chặt hơn thì thay bằng tám điểm."),
        extra=["Người lao động là công dân Việt Nam thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc bao gồm:"]),
    55: dict(reason=(
        "NĐ 152/2020 có hiệu lực từ 2021-02-15, hết hiệu lực từ 2026-11-15 theo vbpl.vn, nên còn áp dụng tại 2026-11-11 (4 ngày trước khi hết). "
        "Điều 22 thuộc Chương III (người lao động Việt Nam làm cho tổ chức, cá nhân nước ngoài); khoản 2 Điều 35 NĐ 219/2025 chỉ chấm dứt \"Nội dung về lao động nước ngoài làm việc tại Việt Nam\", nên không chạm Điều này. "
        "Điểm a: \"Tổ chức được Bộ Ngoại giao phân cấp, ủy quyền, giao nhiệm vụ, đặt hàng hoặc đấu thầu\"; không có cạnh sửa đổi điểm a."),
        extra=["Tổ chức được Bộ Ngoại giao phân cấp, ủy quyền, giao nhiệm vụ, đặt hàng hoặc đấu thầu"]),
    80: dict(reason=(
        "BLLĐ 45/2019 có hiệu lực từ 2021-01-01, không có cạnh sửa đổi khoản này. "
        "Nguyên văn \"Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng; thời gian nghỉ trước khi sinh không quá 02 tháng.\" trả lời cả hai ý. "
        "Khoản 1 Điều 53 Luật BHXH 41/2024 chỉ dẫn lại \"theo quy định tại khoản 1 Điều 139 của Bộ luật Lao động\", không nhắc lại con số, nên không cần thêm."),
        extra=["06 tháng", "không quá 02 tháng"]),
    83: dict(conf="vừa", reason=(
        "BLLĐ 45/2019 có hiệu lực từ 2021-01-01. Khoản 1 Điều 46 nêu trường hợp \"các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34\" (có khoản 3: hai bên thỏa thuận chấm dứt), "
        "điều kiện \"làm việc thường xuyên cho mình từ đủ 12 tháng trở lên\" và mức \"mỗi năm làm việc được trợ cấp một nửa tháng tiền lương\". "
        "Lưu ý theo quy ước 15/11 (quy định nhắc lại ở hai văn bản thì giữ cả hai): khoản 1 Điều 8 NĐ 145/2020 nhắc lại \"chi trả trợ cấp thôi việc theo quy định tại Điều 46 của Bộ luật Lao động đối với người lao động đã làm việc thường xuyên cho mình từ đủ 12 tháng trở lên\", chưa có trong tập đáp án; khoản 3 Điều 8 (trừ thời gian đã tham gia bảo hiểm thất nghiệp) cũng ảnh hưởng số năm tính trợ cấp."),
        extra=["mỗi năm làm việc được trợ cấp một nửa tháng tiền lương", "các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34", "từ đủ 12 tháng trở lên"],
        quotes=[("khoản 1 Điều 8 NĐ 145/2020", "145-2020-nd-cp/chapter-iii/section-2/article-8/clause-1")]),
}

AMEND_ANS = {  # row: decisive phrase of the new wording
    43: "mức trợ cấp một lần bằng 03 tháng mức trợ cấp đang hưởng. Hồ sơ, trình tự giải quyết trợ cấp một lần thực hiện theo quy định của Luật Bảo hiểm xã hội",
    45: "thực hiện theo quy định tại Điều 75 của Luật Bảo hiểm xã hội",
    47: "thực hiện theo quy định tại khoản 1 Điều 90 của Luật Bảo hiểm xã hội",
    50: "Tiền sinh lời của hoạt động đầu tư từ quỹ theo quy định tại Điều 120 và Điều 121 của Luật Bảo hiểm xã hội",
    53: "Chi tổ chức và hoạt động bảo hiểm tai nạn lao động, bệnh nghề nghiệp thực hiện theo quy định của Luật Bảo hiểm xã hội.",
    56: "Tổ chức được Ủy ban nhân dân cấp tỉnh phân cấp, uỷ quyền, giao nhiệm vụ, đặt hàng hoặc đấu thầu.",
    58: "thì báo cáo Sở Lao động - Thương binh và Xã hội",
    60: "Người đứng đầu chi nhánh, văn phòng đại diện hoặc địa điểm kinh doanh của doanh nghiệp.",
    62: "đổi tên doanh nghiệp mà không thay đổi mã số doanh nghiệp",
    74: "Trong thời hạn 05 ngày làm việc",
}
AMEND_ANS_EXTRA = {74: ["Giấy phép lao động có kích thước khổ A4 (21 cm x 29,7 cm), gồm 2 trang"], 58: ["Sửa đổi, bổ sung điểm b khoản 4 Điều 27"]}

AMEND_OLD = {  # stale row: (old phrase in the stale unit, new phrase in the amending unit)
    42: ("các điểm a, b, c, d, đ, e và h khoản 1 Điều 2", "các điểm a, b, c, d, đ, e, i và l khoản 1 Điều 2"),
    44: ("theo quy định tại khoản 2, khoản 3 Điều 109 và khoản 4 Điều 110 của Luật bảo hiểm xã hội", "theo quy định của Luật Bảo hiểm xã hội"),
    46: ("thực hiện theo quy định tại Điều 64 của Luật bảo hiểm xã hội", "thực hiện theo quy định tại Điều 75 của Luật Bảo hiểm xã hội"),
    48: ("thực hiện theo quy định tại khoản 1 Điều 111 của Luật bảo hiểm xã hội", "thực hiện theo quy định tại khoản 1 Điều 90 của Luật Bảo hiểm xã hội"),
    52: ("theo quy định tại Điều 90 và Điều 91 của Luật bảo hiểm xã hội", "theo quy định tại Điều 120 và Điều 121 của Luật Bảo hiểm xã hội"),
    54: ("Chi phí quản lý bảo hiểm tai nạn lao động, bệnh nghề nghiệp", "Chi tổ chức và hoạt động bảo hiểm tai nạn lao động, bệnh nghề nghiệp"),
    57: ("Tổ chức được Sở Lao động - Thương binh và Xã hội phân cấp", "Tổ chức được Ủy ban nhân dân cấp tỉnh phân cấp"),
    59: ("Tổ chức được Sở Lao động - Thương binh và Xã hội phân cấp", "Tổ chức được Ủy ban nhân dân cấp tỉnh phân cấp"),
    61: ("Giám đốc điều hành là người đứng đầu và trực tiếp điều hành đơn vị trực thuộc cơ quan, tổ chức, doanh nghiệp.",
         "Người đứng đầu chi nhánh, văn phòng đại diện hoặc địa điểm kinh doanh của doanh nghiệp."),
    63: ("Thay đổi họ và tên, quốc tịch, số hộ chiếu, địa điểm làm việc ghi trong giấy phép lao động còn thời hạn.",
         "đổi tên doanh nghiệp mà không thay đổi mã số doanh nghiệp"),
    75: ("Mẫu giấy phép lao động do Bộ Lao động - Thương binh và Xã hội in và phát hành thống nhất.",
         "Giấy phép lao động có kích thước khổ A4 (21 cm x 29,7 cm), gồm 2 trang"),
}

PAST_ANS = {  # past_date answers in the old (then applicable) wording
    64: ("Chậm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp",
         "Phạt tiền từ 12% đến 15% tổng số tiền phải đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp"),
    68: ("từ 11 người đến 50 người lao động", "huy động người lao động làm thêm giờ vượt quá số giờ theo quy định của pháp luật"),
    72: ("có ít nhất 3 năm kinh nghiệm làm việc trong chuyên ngành được đào tạo phù hợp với vị trí công việc", "Chuyên gia là người lao động nước ngoài"),
    76: ("mức trợ cấp một lần bằng 03 tháng mức trợ cấp đang hưởng", "theo quy định tại khoản 2, khoản 3 Điều 109 và khoản 4 Điều 110 của Luật bảo hiểm xã hội"),
}
PAST_SITUATION = {64: "biên bản lập ngày 20/5/2025", 68: "30 công nhân, xử phạt 15/8/2024", 72: "hồ sơ nộp 01/6/2022",
                  76: "đề nghị giải quyết ngày 01/3/2025"}

CONTROL_ANS = {
    78: "12 ngày làm việc đối với người làm công việc trong điều kiện bình thường",
    79: "Ít nhất 45 ngày nếu làm việc theo hợp đồng lao động không xác định thời hạn",
    81: "Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên",
    82: "Hai bên thỏa thuận chấm dứt hợp đồng lao động.",
}

ROLE_SLUG = {"đáp án": "dap-an", "lỗi thời": "loi-thoi", "chưa có hiệu lực": "chua-hieu-luc"}


def counterpart(reason):
    ids = re.findall(r"\[([^\]\s]+/[^\]\s]+)\]", reason)
    return ids[-1] if ids else None


def amending_instruction(uid):
    t = text(uid)
    found = instruction_phrases(t)
    return found[0] if found else t.split("\n")[0]


def validity_suggestion(i, r):
    """(value, confidence, reason, extra highlight phrases, quote unit ids) for one sheet row."""
    qid, role, uid, as_of, group = r["question_id"], r["role"], r["unit_id"], r["as_of"], r["group"]
    doc = UNITS[uid]["document_id"]
    d = DOCS[doc]
    spec = VAL_ROWS.get(i, {})
    value, conf, extra, quotes = spec.get("value", "co"), spec.get("conf", "cao"), list(spec.get("extra", [])), list(spec.get("quotes", []))
    status = V.status(uid, as_of)
    if spec.get("reason"):
        return value, conf, spec["reason"], extra, quotes
    other = counterpart(r["reason"])
    if role == "chưa có hiệu lực":
        reason = (f"{SHORT_DOC.get(doc, doc)} có hiệu lực từ {d['effective_from']} theo vbpl.vn, muộn hơn ngày áp dụng {as_of}, "
                  f"nên đơn vị chưa có hiệu lực tại ngày đó (máy tính lại: {STATUS_VI[status]}).")
        return value, conf, reason, extra, quotes
    if uid == ART7 and role == "đáp án":
        art = EXPIRED[qid][3]
        reason = (f"NĐ 283/2026 có hiệu lực từ 2026-09-10, trước {as_of}. Câu hỏi về công ty nên cần câu \"{ORG}\" của khoản 1 Điều 7. "
                  f"Hành vi của câu nằm ở {art} NĐ 283/2026, không thuộc danh sách ngoại lệ của khoản này (Điều 8; Điều 9; khoản 3 Điều 10; khoản 3, 4, 5, 6 Điều 19; ...), nên mức trong {art} là mức cho cá nhân.")
        return value, conf, reason, [ORG], quotes
    if uid == ART6 and role == "lỗi thời":
        reason = (f"NĐ 12/2022 hết hiệu lực từ 2026-09-10 theo vbpl.vn, trước {as_of}. "
                  f"Khoản 1 Điều 6 NĐ 12/2022 và khoản 1 Điều 7 NĐ 283/2026 cùng có câu \"{ORG}\", nên là cặp tương ứng.")
        return value, conf, reason, [ORG], quotes
    if uid == ART6 and role == "đáp án":
        art = {"hl-c01": "khoản 5 Điều 39", "hl-c02": "khoản 4 Điều 18"}[qid]
        reason = (f"NĐ 12/2022 có hiệu lực từ 2022-01-17 đến 2026-09-10, nên áp dụng tại {as_of}. Câu hỏi về doanh nghiệp nên cần câu \"{ORG}\". "
                  f"{art} không thuộc danh sách ngoại lệ của khoản này (danh sách chỉ có \"khoản 8 Điều 39\" ở Điều 39 và không có Điều 18).")
        return value, conf, reason, [ORG], quotes
    if group == "expired_document" and role == "đáp án":
        situation, phrase, lead, art = EXPIRED[qid]
        reason = (f"NĐ 283/2026 có hiệu lực từ 2026-09-10, trước {as_of}; máy tính lại: {STATUS_VI[status]}. "
                  f"Câu hỏi nêu \"{situation}\"; câu dẫn ghi \"{lead}\" và đơn vị ghi \"{phrase}\", khớp tình huống.")
        return value, conf, reason, [phrase, lead], quotes
    if group == "expired_document" and role == "lỗi thời":
        parts = quote_parts(r["quotes"])
        shared = parts[0]
        lead = parts[1] if len(parts) > 1 else None
        reason = (f"NĐ 12/2022 hết hiệu lực từ 2026-09-10 theo vbpl.vn, trước {as_of}. Hai đơn vị trong cặp cùng có cụm \"{shared}\"")
        reason += f" và câu dẫn \"{lead}\", nên mô tả cùng một hành vi." if lead else ", nên mô tả cùng một hành vi."
        if qid == "hl-a02":
            reason += " Lời văn có đổi: NĐ 283/2026 thêm \"thấp hơn thỏa thuận hoặc\"; hành vi trả lương thử việc dưới 85% vẫn giống nhau."
        if qid == "hl-a05":
            reason += (" Lời văn có đổi: NĐ 12/2022 tính trên \"tổng số tiền phải đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp\", "
                       "NĐ 283/2026 tính trên \"tổng số tiền chậm đóng bảo hiểm xã hội bắt buộc\"; hành vi chậm đóng vẫn có ở cả hai.")
        return value, conf, reason, [p for p in parts], quotes
    if i in AMEND_ANS:
        phrase = AMEND_ANS[i]
        instr = amending_instruction(uid)
        target = other
        reason = (f"{SHORT_DOC.get(doc, doc)} có hiệu lực từ {d['effective_from']} theo vbpl.vn, trước ngày áp dụng {as_of}. "
                  f"Đơn vị ghi \"{instr}\" (thay {label(target)}) và lời văn mới \"{phrase}\" trả lời điều câu hỏi hỏi.")
        if i == 58:
            reason += " Nơi nhận báo cáo không đổi (Sở Lao động - Thương binh và Xã hội); lời văn mới đổi tổ chức báo cáo thành tổ chức do Ủy ban nhân dân cấp tỉnh giao."
        if i == 74:
            reason += " Tại 2024-05-10 NĐ 219/2025 (hiệu lực từ 2025-08-07) chưa có hiệu lực, nên không có văn bản thay sau."
        return value, conf, reason, [phrase, instr] + AMEND_ANS_EXTRA.get(i, []), quotes
    if i in AMEND_OLD:
        old, new = AMEND_OLD[i]
        instr = amending_instruction(other)
        od = DOCS[UNITS[other]["document_id"]]
        reason = (f"Đơn vị sửa ({label(other)}) ghi \"{instr}\", đúng số khoản, điểm, Điều của đơn vị này; "
                  f"{SHORT_DOC.get(od['document_id'])} có hiệu lực từ {od['effective_from']}, trước ngày áp dụng {as_of}. "
                  f"Lời văn cũ \"{old}\" đã được thay bằng \"{new}\" (máy tính lại: {STATUS_VI[status]}).")
        return value, conf, reason, [old], quotes
    if i in PAST_ANS:
        phrase, lead = PAST_ANS[i]
        end = f" đến {d['effective_to']}" if d.get("effective_to") else ""
        reason = (f"Câu hỏi có ngày ({PAST_SITUATION[i]}), nên xét tại {as_of}. {SHORT_DOC.get(doc, doc)} có hiệu lực từ {d['effective_from']}{end} theo vbpl.vn; "
                  f"máy tính lại: {STATUS_VI[status]}. Nguyên văn \"{phrase}\" trả lời câu hỏi.")
        if i == 72:
            reason += " NĐ 70/2023 (sửa điểm này) chỉ có hiệu lực từ 2023-09-18, NĐ 219/2025 từ 2025-08-07, đều sau ngày đó."
        if i == 76:
            reason += " Điểm đ khoản 1 Điều 139 Luật BHXH 41/2024 (sửa khoản này) chỉ có hiệu lực từ 2025-07-01, sau ngày đó."
        if i == 64:
            reason += " NĐ 283/2026 chỉ có hiệu lực từ 2026-09-10."
        if i == 68:
            reason += " 30 người thuộc mức từ 11 đến 50 người."
        return value, conf, reason, [phrase, lead], quotes
    if i in CONTROL_ANS:
        phrase = CONTROL_ANS[i]
        reason = (f"BLLĐ 45/2019 có hiệu lực từ 2021-01-01 theo vbpl.vn, không có cạnh sửa đổi đơn vị này; máy tính lại: {STATUS_VI[status]}. "
                  f"Nguyên văn \"{phrase}\" trả lời câu hỏi.")
        if i == 82:
            reason += " Khoản 1 Điều 46 (dòng sau) nêu trợ cấp khi chấm dứt theo \"các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34\", có khoản 3 này."
        return value, conf, reason, [phrase], quotes
    if i in (49, 51):
        phrase = {49: "Khoản đóng thuộc trách nhiệm của người sử dụng lao động", 51: "Các nguồn thu hợp pháp khác."}[i]
        reason = (f"Luật ATVSLĐ 84/2015 có hiệu lực từ 2016-07-01; cạnh sửa đổi của Luật BHXH 41/2024 chỉ chạm điểm b khoản 2 Điều 44, không chạm điểm này; máy tính lại: {STATUS_VI[status]}. "
                  f"Nguyên văn \"{phrase}\" là một nguồn hình thành Quỹ mà câu hỏi hỏi.")
        return value, conf, reason, [phrase], quotes
    raise KeyError(f"row {i} ({qid}, {role}, {uid}) has no suggestion")


VAL_QUESTION = {
    "đáp án": "Đơn vị này có chứa thông tin câu hỏi hỏi và có áp dụng tại ngày áp dụng không?",
    "lỗi thời": "Đơn vị này có đúng là lỗi thời tại ngày áp dụng (văn bản hết hiệu lực hoặc đã bị sửa đúng chỗ) không?",
    "chưa có hiệu lực": "Ngày hiệu lực của văn bản chứa đơn vị này có muộn hơn ngày áp dụng không?",
}


def build_validity():
    rows = list(csv.DictReader(open(VAL_DIR / "check-sheet.csv", encoding="utf-8-sig")))
    assert len(rows) == 84, len(rows)
    columns = list(rows[0].keys())
    items = []
    for i, r in enumerate(rows):
        value, conf, reason, extra, quote_ids = validity_suggestion(i, r)
        qid, role, uid, as_of = r["question_id"], r["role"], r["unit_id"], r["as_of"]
        doc = UNITS[uid]["document_id"]
        status = V.status(uid, as_of)
        assert status == r["status_at_as_of"], (i, status, r["status_at_as_of"])
        qparts = quote_parts(r["quotes"])
        phrases = extra + qparts
        situation = []
        if qid in EXPIRED:
            situation = [EXPIRED[qid][0]]
        situation += re.findall(r"\d{1,2}/\d{1,2}/\d{4}|[Tt]háng \d{1,2}/\d{4}|[Nn]ăm \d{4}|hiện nay|hiện hành|đang có hiệu lực|lúc đó|thời điểm đó|khi đó", r["question"])
        fields = [{"label": f"Câu hỏi (ngày áp dụng {as_of})", "text": r["question"], "highlight": hl(r["question"], situation)}]
        unit_text = r["unit_text"]
        fields.append({"label": f"Đơn vị kiểm, vai trò \"{role}\": {label(uid)}", "text": unit_text,
                       "highlight": hl(unit_text, phrases + instruction_phrases(unit_text))})
        if r["context"].strip():
            fields.append({"label": "Tên Điều và câu dẫn của đơn vị", "text": r["context"], "highlight": hl(r["context"], phrases)})
        fields.append({"label": "Ngày hiệu lực và trạng thái máy tính",
                       "text": f"{doc_dates(doc)}.\nTrạng thái tại {as_of} (unit-status-v2): {STATUS_VI[status]}.",
                       "highlight": hl(doc_dates(doc), [DOCS[doc]["effective_from"], DOCS[doc].get("effective_to") or ""])})
        other = counterpart(r["reason"])
        if other and other in UNITS:
            od = UNITS[other]["document_id"]
            parent = UNITS.get(UNITS[other]["parent_id"])
            ctx = ""
            if parent and parent["unit_type"] in ("clause", "point") or (parent and UNITS[other]["unit_type"] == "point"):
                ctx = f"(câu dẫn) {parent['text'].strip()}\n"
            otext = ctx + text(other)
            fields.append({"label": f"Đơn vị đối ứng: {label(other)} ({doc_dates(od)})", "text": otext,
                           "highlight": hl(otext, phrases + instruction_phrases(otext) + ([AMEND_OLD[i][1]] if i in AMEND_OLD else []))})
        sugg_quotes = []
        for p in hl(unit_text, extra + qparts)[:2]:
            sugg_quotes.append({"label": label(uid), "text": p})
        for qlabel, quid in quote_ids:
            sugg_quotes.append({"label": qlabel, "text": text(quid)})
        items.append({
            "id": f"{qid}|{ROLE_SLUG[role]}|{uid}",
            "group": qid,
            "heading": f"{qid} · {role} · {label(uid)}",
            "question": VAL_QUESTION[role],
            "fields": fields,
            "suggestion": {"value": value, "reason": reason, "confidence": conf, "quotes": sugg_quotes},
            "export": dict(r),
        })
    task = {
        "task": "validity",
        "title": "Bộ hiệu lực v1: kiểm từng đơn vị đáp án, lỗi thời, chưa có hiệu lực",
        "instructions": "\n".join([
            "Mỗi mục là một dòng của bảng kiểm: một đơn vị của một câu hỏi, với vai trò đáp án, lỗi thời hoặc chưa có hiệu lực.",
            "Chỉ so chữ và ngày, không cần nhận định pháp lý.",
            "Dòng đáp án: đơn vị có chứa điều câu hỏi hỏi (mức phạt, thời hạn, điều dẫn chiếu) và văn bản có hiệu lực tại ngày áp dụng.",
            "Dòng lỗi thời của NĐ 12/2022: hai đơn vị trong cặp có cùng cụm chữ và cùng hành vi; NĐ 12/2022 hết hiệu lực từ 2026-09-10.",
            "Dòng lỗi thời do sửa đổi: câu \"Sửa đổi, bổ sung ...\" ở đơn vị đối ứng nêu đúng số khoản, điểm, Điều và có hiệu lực trước ngày áp dụng.",
            "Dòng chưa có hiệu lực: ngày hiệu lực của văn bản muộn hơn ngày áp dụng.",
            "Chọn Đúng nếu dòng đúng, Sai nếu sai, Không chắc nếu không tự kiểm được.",
            "Khi chọn Sai hoặc thấy tập đáp án thiếu đơn vị, ghi lý do ngắn ở ô ghi chú.",
            "Câu không ghi ngày được hiểu là hỏi tại 11/11/2026 (quy ước 15/11/2026).",
        ]),
        "drafted_by": DRAFTED_BY,
        "export_columns": columns,
        "options": [
            {"value": "co", "label": "Đúng", "hint": "Dòng đúng: vai trò và trạng thái khớp nguyên văn và ngày", "csv": {"annotator_agrees": "co"}},
            {"value": "khong", "label": "Sai", "hint": "Đơn vị không chứa thông tin, sai cặp, sai ngày hoặc sai chỗ sửa", "csv": {"annotator_agrees": "khong"}},
            {"value": "khong_chac", "label": "Không chắc", "hint": "Không tự kiểm được; ghi lý do ở ghi chú", "csv": {"annotator_agrees": ""}},
        ],
        "items": items,
    }
    return task


# --------------------------------------------------------------------------------------------------------------
# Link-dependent set
# --------------------------------------------------------------------------------------------------------------

LINK_OPTIONS = [
    {"value": "can_B_gold_dung", "label": "Cần B, gold đúng", "hint": "Thiếu B thì không trả lời đủ; danh sách đáp án đủ, không thừa",
     "csv": {"needs_B (co/khong)": "co", "gold_ok (co/khong)": "co"}},
    {"value": "can_B_gold_sai", "label": "Cần B, gold sai", "hint": "Thiếu B thì không trả lời đủ; danh sách đáp án thiếu, thừa hoặc lỗi thời (ghi ở ghi chú)",
     "csv": {"needs_B (co/khong)": "co", "gold_ok (co/khong)": "khong"}},
    {"value": "khong_can_B_gold_dung", "label": "Không cần B, gold đúng", "hint": "A hoặc phần khác đã đủ; danh sách đáp án vẫn đúng (câu đối chứng chọn mục này)",
     "csv": {"needs_B (co/khong)": "khong", "gold_ok (co/khong)": "co"}},
    {"value": "khong_can_B_gold_sai", "label": "Không cần B, gold sai", "hint": "A hoặc phần khác đã đủ; danh sách đáp án thiếu hoặc thừa (ghi ở ghi chú)",
     "csv": {"needs_B (co/khong)": "khong", "gold_ok (co/khong)": "khong"}},
    {"value": "khong_chac", "label": "Không chắc", "hint": "Không tự quyết được; ghi lý do ở ghi chú; hai cột để trống", "csv": {"needs_B (co/khong)": "", "gold_ok (co/khong)": ""}},
]

U = {  # short aliases for related units shown to the reviewer
    "bl107_2a": "45-2019-qh14/chapter-vii/section-1/article-107/clause-2/point-a",
    "bl108": "45-2019-qh14/chapter-vii/section-1/article-108",
    "bl129_1": "45-2019-qh14/chapter-viii/section-2/article-129/clause-1",
    "bl21_4": "45-2019-qh14/chapter-iii/section-1/article-21/clause-4",
    "bl41": "45-2019-qh14/chapter-iii/section-3/article-41",
    "nd89_1d": "145-2020-nd-cp/chapter-x/article-89/clause-1/point-d",
    "bl41_2": "45-2019-qh14/chapter-iii/section-3/article-41/clause-2",
    "nd63_2": "283-2026-nd-cp/chapter-v/section-1/article-63/clause-2",
    "nd63_5": "283-2026-nd-cp/chapter-v/section-1/article-63/clause-5",
    "nd63_8": "283-2026-nd-cp/chapter-v/section-1/article-63/clause-8",
    "nd63_10": "283-2026-nd-cp/chapter-v/section-1/article-63/clause-10",
    "nd63_13": "283-2026-nd-cp/chapter-v/section-1/article-63/clause-13",
    "lu45_3": "84-2015-qh13/chapter-iii/section-3/article-45/clause-3",
    "bl105_2": "45-2019-qh14/chapter-vii/section-1/article-105/clause-2",
    "nd219_35_2": "219-2025-nd-cp/chapter-v/article-35/clause-2",
    "nd219_5_2": "219-2025-nd-cp/chapter-i/article-5/clause-2",
    "nd219_22_5": "219-2025-nd-cp/chapter-iii/section-1/article-22/clause-5",
    "bl192_1": "45-2019-qh14/chapter-xiv/section-3/article-192/clause-1",
    "bh53_1": "41-2024-qh15/chapter-v/section-2/article-53/clause-1",
}

N219 = ("Khoản 2 Điều 35 NĐ 219/2025 (hiệu lực từ 2025-08-07) ghi \"Nội dung về lao động nước ngoài làm việc tại Việt Nam quy định tại Nghị định số 152/2020/NĐ-CP ... "
        "được sửa đổi, bổ sung tại Nghị định số 70/2023/NĐ-CP ... hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực\". ")
N219_TAIL = ("Theo quy ước 15/11 (đơn vị hết hiệu lực là lỗi thời), tại 2026-11-11 cả A và B là lỗi thời; máy vẫn báo A \"đã bị sửa đổi\" và B \"còn hiệu lực\" "
             "vì cạnh expire_subject của câu này chưa được áp dụng (hạn chế đã ghi ngày 16/11). Ngày hết hiệu lực 2026-11-15 của cả NĐ 152/2020 không thay đổi điều này. "
             "Hướng sửa: đặt as_of trước 2025-08-07 như bộ hiệu lực, hoặc bỏ câu.")

LINK = {
    "l00": dict(v="can_B_gold_dung", c="vừa", rel=["bl21_4"], hl=["thực hiện theo quy định tại khoản 1 Điều 21 của Bộ luật Lao động", "Nhà nước nắm giữ từ 50% vốn điều lệ", "Chính phủ quy định nội dung của hợp đồng lao động đối với người lao động được thuê làm giám đốc trong doanh nghiệp có vốn nhà nước"],
                r=("Khoản 1 Điều 21 BLLĐ là danh sách chung; khoản 4 cùng Điều ghi \"Chính phủ quy định nội dung của hợp đồng lao động đối với người lao động được thuê làm giám đốc trong doanh nghiệp có vốn nhà nước\", "
                   "nên chỉ có A thì chưa biết danh sách này có áp cho giám đốc ở doanh nghiệp Nhà nước nắm từ 50% vốn trở xuống không. "
                   "B (Điều 6 NĐ 145/2020) trả lời: \"thực hiện theo quy định tại khoản 1 Điều 21 của Bộ luật Lao động\". "
                   "Gold gồm 10 điểm của khoản 1 Điều 21 và Điều 6, đủ. Câu hỏi dùng từ gần tên Điều 6, như README đã nêu.")),
    "l01": dict(v="can_B_gold_dung", c="cao", hl=["được kéo dài thời hiệu xử lý bồi thường thiệt hại nhưng không quá 60 ngày", "Không xử lý bồi thường thiệt hại", "Nghỉ ốm đau, điều dưỡng"],
                r=("Phần hai của câu hỏi (kéo dài thời hiệu) chỉ có ở B: \"được kéo dài thời hiệu xử lý bồi thường thiệt hại nhưng không quá 60 ngày\". "
                   "Phần một có ở A: điểm a khoản 4 Điều 122 BLLĐ (\"Nghỉ ốm đau, điều dưỡng\") và khoản 2 Điều 72 NĐ 145/2020 (\"Không xử lý bồi thường thiệt hại\").")),
    "l02": dict(v="can_B_gold_dung", c="vừa", hl=["tiền lương bình quân của 06 tháng liền kề theo hợp đồng lao động trước khi chấm dứt hợp đồng lao động cuối cùng", "theo quy định tại khoản 2 Điều 20"],
                r=("Chỉ B nói lương tính trợ cấp: \"tiền lương bình quân của 06 tháng liền kề theo hợp đồng lao động trước khi chấm dứt hợp đồng lao động cuối cùng\". "
                   "Hai điểm của khoản 2 Điều 20 BLLĐ chỉ mô tả việc ký tiếp hợp đồng (B dẫn \"khoản 2 Điều 20\"); là bối cảnh, có thể coi là thừa nhẹ nhưng không sai.")),
    "l03": dict(v="can_B_gold_dung", c="vừa", rel=["bl41"], hl=["sa thải trái quy định của pháp luật", "có nghĩa vụ thực hiện quy định tại Điều 41 của Bộ luật Lao động", "đơn phương chấm dứt hợp đồng lao động trái pháp luật", "ít nhất bằng 02 tháng tiền lương theo hợp đồng lao động"],
                r=("Điều 41 BLLĐ có tên \"Nghĩa vụ của người sử dụng lao động khi đơn phương chấm dứt hợp đồng lao động trái pháp luật\", không nói tới sa thải. "
                   "B là cầu nối: \"Trường hợp người sử dụng lao động quyết định xử lý kỷ luật lao động theo hình thức sa thải trái quy định của pháp luật thì ... có nghĩa vụ thực hiện quy định tại Điều 41\". "
                   "B là cả Điều 73, câu đầu về khiếu nại không cần, nhưng Điều 73 không chia khoản nên chấp nhận được. Khoản 1 và 3 Điều 41 nêu đủ các khoản tiền.")),
    "l04": dict(v="can_B_gold_sai", c="vừa", rel=["bl129_1"], hl=["làm hư hỏng dụng cụ, thiết bị hoặc có hành vi khác gây thiệt hại tài sản", "làm mất dụng cụ, thiết bị, tài sản", "xác định cụ thể các hành vi, hình thức xử lý kỷ luật lao động, trách nhiệm vật chất", "làm hỏng hoặc làm mất"],
                note="Thiếu khoản 1 Điều 129 BLLĐ (làm hư hỏng).",
                r=("Câu hỏi nói \"làm hỏng hoặc làm mất\". Gold chỉ có khoản 2 Điều 129 BLLĐ (\"làm mất dụng cụ, thiết bị, tài sản\"); "
                   "trường hợp làm hỏng nằm ở khoản 1 Điều 129 (\"làm hư hỏng dụng cụ, thiết bị hoặc có hành vi khác gây thiệt hại tài sản\"), chưa có trong gold. "
                   "B cần cho phần thỏa thuận sẵn: \"xác định cụ thể các hành vi, hình thức xử lý kỷ luật lao động, trách nhiệm vật chất\" và \"ghi trong hợp đồng lao động\".")),
    "l05": dict(v="khong_can_B_gold_sai", c="vừa", rel=["bl107_2a", "bl108"], hl=["Phải được sự đồng ý của người lao động", "người lao động không được từ chối", "mà không cần hỏi ý kiến"],
                note="B không cần; thiếu điểm a khoản 2 Điều 107 BLLĐ.",
                r=("Điểm a khoản 2 Điều 107 BLLĐ đã ghi \"Phải được sự đồng ý của người lao động\", và câu dẫn Điều 108 nêu ngoại lệ mà \"người lao động không được từ chối\". "
                   "Hai đơn vị BLLĐ này đủ trả lời có hay không; B (khoản 1 Điều 59 NĐ 145/2020: thời gian, địa điểm, công việc làm thêm) chỉ thêm chi tiết nội dung cần đồng ý. "
                   "Gold thiếu điểm a khoản 2 Điều 107. README đã nêu câu này dùng từ gần với B.")),
    "l06": dict(v="can_B_gold_dung", c="vừa", hl=["thì ghi thành mục riêng trong hợp đồng lao động", "thưởng theo quy định tại Điều 104 của Bộ luật Lao động"],
                r=("Chỉ B trả lời: thưởng theo Điều 104 \"thì ghi thành mục riêng trong hợp đồng lao động\". Khoản 1, 2 Điều 104 BLLĐ chỉ định nghĩa thưởng và quy chế thưởng (bối cảnh). "
                   "Hiệu lực: TT 10/2020 có hiệu lực từ 2021-01-01, không có ngày hết hiệu lực và không có cạnh sửa đổi nào trong corpus, nên máy coi là còn hiệu lực tại 2026-11-11; "
                   "trường legal_status là unknown (mọi văn bản trong corpus đều vậy). Agent không xác minh được thêm từ corpus.")),
    "l07": dict(v="can_B_gold_dung", c="cao", hl=["thời gian bị tạm đình chỉ công việc theo Điều 128 của Bộ luật Lao động", "trả đủ tiền lương cho thời gian bị tạm đình chỉ công việc"],
                r=("Chỉ B trả lời phần trợ cấp: thời gian làm việc thực tế gồm \"thời gian bị tạm đình chỉ công việc theo Điều 128 của Bộ luật Lao động\". "
                   "A (khoản 2, 4 Điều 128 BLLĐ) cho bối cảnh: nhận lại làm việc và trả đủ lương thời gian bị đình chỉ.")),
    "l08": dict(v="can_B_gold_dung", c="vừa", hl=["điểm d khoản này, người sử dụng lao động có trách nhiệm trả trợ cấp thôi việc", "mà không cần lý do nhưng phải báo trước ít nhất 15 ngày", "mỗi năm làm việc được trợ cấp một nửa tháng tiền lương", "từ đủ 12 tháng trở lên"],
                r=("Khoản 1 Điều 46 BLLĐ chỉ liệt kê các khoản của Điều 34; quyền nghỉ không cần lý do, báo trước 15 ngày của người giúp việc là quy định riêng ở điểm d khoản 1 Điều 89 NĐ 145/2020. "
                   "B (điểm e) nối hai bên: khi chấm dứt theo \"điểm d khoản này, người sử dụng lao động có trách nhiệm trả trợ cấp thôi việc\" theo Điều 46. "
                   "Khoản 1, 3 Điều 46 cho mức và lương tính; đủ. Điều kiện \"từ đủ 12 tháng trở lên\" vẫn áp dụng, câu hỏi không nêu thời gian làm việc.")),
    "l09": dict(v="can_B_gold_sai", c="vừa", rel=["nd89_1d", "bl41_2"], hl=["không đúng quy định tại điểm d khoản này", "trong những ngày không báo trước", "phải báo trước ít nhất 15 ngày", "ít nhất bằng 02 tháng tiền lương theo hợp đồng lao động"],
                note="Thiếu điểm d khoản 1 Điều 89 NĐ 145/2020 (thời hạn báo trước); có thể thêm khoản 2, 3 Điều 41 BLLĐ.",
                r=("B cần: định nghĩa chấm dứt trái pháp luật và khoản tiền \"tương ứng với tiền lương theo hợp đồng lao động trong những ngày không báo trước\". "
                   "Nhưng B dẫn \"không đúng quy định tại điểm d khoản này\" (báo trước ít nhất 15 ngày và các trường hợp không phải báo trước); đơn vị đó không có trong gold nên không xác định được việc trái pháp luật và số ngày không báo trước. "
                   "Nếu chủ nhà không nhận lại người giúp việc thì khoản 2 hoặc 3 Điều 41 BLLĐ cũng liên quan.")),
    "l10": dict(v="can_B_gold_dung", c="cao", hl=["Không bảo đảm việc làm cho người lao động theo quy định tại Điều 140 của Bộ luật Lao động", "với mức lương không thấp hơn mức lương trước khi nghỉ thai sản", "Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng"],
                r=("Mức phạt chỉ có ở B: \"Không bảo đảm việc làm cho người lao động theo quy định tại Điều 140 của Bộ luật Lao động\" thuộc khoản 2 Điều 26 NĐ 283/2026, câu dẫn \"Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng\" "
                   "(câu dẫn không thuộc gold nhưng hiện cùng B trong ngữ cảnh). A (Điều 140 BLLĐ) cho nội dung nghĩa vụ.")),
    "l11": dict(v="can_B_gold_dung", c="cao", hl=["Huy động người lao động làm thêm giờ mà không được sự đồng ý của người lao động, trừ trường hợp theo quy định tại Điều 108", "Phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng"],
                r=("Mức phạt chỉ có ở B (điểm b khoản 3 Điều 24 NĐ 283/2026, câu dẫn \"Phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng\"): "
                   "\"Huy động người lao động làm thêm giờ mà không được sự đồng ý của người lao động, trừ trường hợp theo quy định tại Điều 108\". "
                   "A (khoản 1, 2 Điều 108 BLLĐ) là ngoại lệ được dẫn. Câu hỏi dùng từ gần với B nhưng B vẫn bắt buộc vì A không có mức phạt.")),
    "l12": dict(v="can_B_gold_sai", c="vừa", rel=["nd63_2", "nd63_8", "nd63_10", "nd63_13"], hl=["các điểm c, d, đ, e khoản 3 Điều 19", "Chương II", "Ai có quyền xử phạt"],
                note="Thiếu các khoản 2, 8, 10, 13 Điều 63 NĐ 283/2026, hoặc sửa câu hỏi thành \"Cục trưởng cục nào\".",
                r=("B (khoản 9 Điều 63 NĐ 283/2026) đúng: Cục trưởng Cục Việc làm xử phạt \"các điểm c, d, đ, e khoản 3 Điều 19\". "
                   "Nhưng câu hỏi \"Ai có quyền xử phạt\" có nhiều người: khoản 2 Điều 63 (\"Chủ tịch Ủy ban nhân dân các cấp\", hành vi tại Chương II), khoản 8 (\"Giám đốc Sở Nội vụ\", Chương II), "
                   "khoản 10 (Trưởng đoàn kiểm tra do Cục trưởng Cục Việc làm thành lập, cũng ghi \"các điểm c, d, đ, e khoản 3 Điều 19\"), khoản 13 (Trưởng đoàn kiểm tra do Bộ trưởng Bộ Nội vụ thành lập). "
                   "Điều 19 thuộc Chương II. Gold chỉ có khoản 9.")),
    "l13": dict(v="can_B_gold_dung", c="cao", hl=["Cho tổ chức, cá nhân khác sử dụng Giấy phép hoạt động dịch vụ", "gửi 01 bản quyết định xử phạt đến Bộ trưởng Bộ Nội vụ", "điểm a, b, c khoản 10 Điều 49", "Phạt tiền từ 180.000.000 đồng đến 200.000.000 đồng"],
                r=("Hành vi và mức phạt ở A (điểm b khoản 10 Điều 49 NĐ 283/2026, câu dẫn \"Phạt tiền từ 180.000.000 đồng đến 200.000.000 đồng\"). "
                   "Nơi nhận quyết định chỉ có ở B: \"gửi 01 bản quyết định xử phạt đến Bộ trưởng Bộ Nội vụ\" với hành vi tại \"điểm a, b, c khoản 10 Điều 49\", có điểm b.")),
    "l14": dict(v="can_B_gold_dung", c="thấp", hl=["có hiệu lực thi hành kể từ ngày Nghị định sửa đổi, bổ sung một số điều của Nghị định số 189/2025/NĐ-CP", "Phạt tiền đến 75.000.000 đồng"],
                note="Phụ thuộc nghị định sửa đổi NĐ 189/2025 không có trong corpus.",
                r=("Phần \"có hiệu lực từ khi nào\" chỉ có ở B: \"có hiệu lực thi hành kể từ ngày Nghị định sửa đổi, bổ sung một số điều của Nghị định số 189/2025/NĐ-CP ... có hiệu lực thi hành\". "
                   "Nghị định sửa đổi đó không có trong corpus, nên không biết tại 2026-11-11 thẩm quyền này đã có hiệu lực chưa; phần một (\"Phạt tiền đến 75.000.000 đồng\") có thể chưa áp dụng. "
                   "Đơn vị gold đúng với câu hỏi, nhưng đáp án chỉ nêu được điều kiện; cân nhắc giữ câu kèm ghi chú hoặc bỏ câu.")),
    "l15": dict(v="can_B_gold_dung", c="vừa", hl=["Hành vi tái phạm quy định về đóng bảo hiểm xã hội bắt buộc quy định tại Điều 44", "phải chuyển hồ sơ liên quan đến hành vi có dấu hiệu tội phạm", "nộp số tiền bằng 0,03%/ngày"],
                r=("Phần khắc phục ở A (điểm a, b khoản 3 Điều 44 NĐ 283/2026: đóng đủ số tiền trốn đóng và \"nộp số tiền bằng 0,03%/ngày\"). "
                   "Phần tái phạm cần B (điểm l khoản 2 Điều 4: \"Hành vi tái phạm quy định về đóng bảo hiểm xã hội bắt buộc quy định tại Điều 44\"); hệ quả \"phải chuyển hồ sơ liên quan đến hành vi có dấu hiệu tội phạm\" nằm ở câu dẫn khoản 2 Điều 4 "
                   "(hiện cùng B, không thuộc gold) và chỉ áp dụng khi có dấu hiệu tội phạm.")),
    "l16": dict(v="can_B_gold_sai", c="vừa", rel=["nd63_5", "nd63_2", "nd63_8"], hl=["điểm a khoản 9 Điều 49", "các điểm a, b, c, d, e, g, h khoản 9 Điều 49", "Chương IV", "lực lượng nào"],
                note="Ít nhất thiếu khoản 5 Điều 63 NĐ 283/2026 (Công an nhân dân).",
                r=("B đúng: Bộ đội Biên phòng xử phạt hành vi tại \"điểm a khoản 9 Điều 49\". "
                   "Nhưng khoản 5 Điều 63 NĐ 283/2026 (Công an nhân dân) cũng ghi \"các điểm a, b, c, d, e, g, h khoản 9 Điều 49\"; khoản 2 (Chủ tịch Ủy ban nhân dân các cấp) và khoản 8 (Giám đốc Sở Nội vụ) có thẩm quyền với Chương IV, nơi có Điều 49. "
                   "Câu hỏi \"lực lượng nào\" nên ít nhất có thêm khoản 5.")),
    "l17": dict(v="can_B_gold_dung", c="cao", hl=["Ngoài các quyền và nghĩa vụ quy định tại Điều 6 của Bộ luật này", "kể cả các nghĩa vụ chung"],
                r=("Câu dẫn Điều 56 BLLĐ: \"Ngoài các quyền và nghĩa vụ quy định tại Điều 6 của Bộ luật này, doanh nghiệp cho thuê lại lao động có các quyền và nghĩa vụ sau đây\", và câu hỏi hỏi cả nghĩa vụ chung, nên cần B (điểm a-đ khoản 2 Điều 6). "
                   "Điều 56 có đúng 6 khoản, khoản 2 Điều 6 có đúng 5 điểm, gold có đủ.")),
    "l18": dict(v="can_B_gold_dung", c="cao", hl=["Trong thời hạn 12 giờ", "các điều 200, 201 và 202", "Lấy ý kiến về đình công", "Ra quyết định đình công và thông báo đình công", "Tiến hành đình công"],
                r=("Phần một ở A (Điều 211 BLLĐ: \"Trong thời hạn 12 giờ\", Chủ tịch Ủy ban nhân dân cấp huyện chủ trì gặp các bên). "
                   "Câu hỏi hỏi thêm các bước đình công đúng, chỉ có ở B (khoản 1-3 Điều 200: lấy ý kiến, ra quyết định và thông báo, tiến hành đình công). Gold đủ theo nguyên văn corpus.")),
    "l19": dict(v="can_B_gold_dung", c="vừa", hl=["được ngân sách nhà nước đóng bảo hiểm y tế", "đang hưởng chế độ quy định tại Điều 23 của Luật này", "nghỉ việc hưởng trợ cấp tai nạn lao động, bệnh nghề nghiệp hằng tháng"],
                r=("Chỉ B nói ai đóng: \"Người đang trong thời gian hưởng trợ cấp hằng tháng thì được ngân sách nhà nước đóng bảo hiểm y tế\" (khoản 6 Điều 23 Luật BHXH 41/2024). A (điểm b khoản 2 Điều 10) chỉ nói được hưởng bảo hiểm y tế. "
                   "Lưu ý câu hỏi hơi mơ hồ: \"trợ cấp hằng tháng từ bảo hiểm xã hội\" có thể hiểu cả trợ cấp tai nạn lao động hằng tháng (A cũng nhắc), trong khi B chỉ nói trợ cấp hằng tháng của Điều 23. "
                   "Nên sửa câu hỏi cho rõ (người chưa đủ điều kiện hưởng lương hưu đang hưởng trợ cấp hằng tháng).")),
    "l20": dict(v="can_B_gold_dung", c="cao", hl=["20 ngày nếu thai từ đủ 05 tuần tuổi đến dưới 13 tuần tuổi", "chia cho 30 ngày", "bằng 100% mức bình quân tiền lương"],
                r=("Số ngày nghỉ chỉ có ở B: \"20 ngày nếu thai từ đủ 05 tuần tuổi đến dưới 13 tuần tuổi\" (thai 8 tuần thuộc mức này). "
                   "A cho cách tính: \"bằng 100% mức bình quân tiền lương\" (khoản 1 Điều 59) và với Điều 52 thì mức mỗi ngày \"chia cho 30 ngày\" (khoản 3 Điều 59). Gold đủ.")),
    "l21": dict(v="can_B_gold_dung", c="vừa", hl=["thì được bảo lưu thời gian đóng bảo hiểm xã hội", "Đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 của Bộ luật Lao động", "từ đủ 15 năm trở lên"],
                r=("Bảo lưu ở A (Điều 71 Luật BHXH 41/2024: \"thì được bảo lưu thời gian đóng bảo hiểm xã hội\"). Điều kiện lương hưu cần B: \"Đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 của Bộ luật Lao động\", "
                   "câu dẫn khoản 1 Điều 64 \"từ đủ 15 năm trở lên\" (hiện cùng B). Tuổi cụ thể nằm ở khoản 2 Điều 169 BLLĐ, không có trong gold; nếu muốn đáp án nêu số tuổi thì cần thêm. "
                   "Nguyên văn Điều 71 trong corpus bị lặp hai lần (lỗi tách), không ảnh hưởng nội dung.")),
    "l22": dict(v="can_B_gold_dung", c="cao", hl=["Ngoài các quyền và nghĩa vụ theo quy định tại Điều 5 của Bộ luật này"],
                r=("Câu dẫn Điều 58 BLLĐ: \"Ngoài các quyền và nghĩa vụ theo quy định tại Điều 5 của Bộ luật này, người lao động thuê lại có các quyền và nghĩa vụ sau đây\", "
                   "nên nghĩa vụ đủ gồm khoản 1, 2 Điều 58 và điểm a, b, c khoản 2 Điều 5 (B). Khoản 3-5 Điều 58 là quyền, không cần.")),
    "l23": dict(v="khong_can_B_gold_dung", c="vừa", hl=["được tính là thời gian làm việc có hưởng lương", "không tính vào thời gian quy định tại khoản 2 Điều 176 của Bộ luật này", "thời gian làm công việc đại diện mà công ty dành cho ban lãnh đạo tổ chức đại diện"],
                note="A tự trả lời đủ; câu không đo được việc cần liên kết.",
                r=("A (khoản 2 Điều 70 BLLĐ) tự trả lời cả hai ý: \"được tính là thời gian làm việc có hưởng lương\" và \"không tính vào thời gian quy định tại khoản 2 Điều 176 của Bộ luật này\". "
                   "Câu hỏi đã tả sẵn nội dung của B (\"thời gian làm công việc đại diện mà công ty dành cho ban lãnh đạo tổ chức đại diện\"), nên B chỉ giải thích thêm. "
                   "Danh sách gold không sai, nhưng câu này không đo được việc cần liên kết.")),
    "l24": dict(v="can_B_gold_dung", c="cao", rel=["bl192_1"], hl=["Trong thời hạn 05 ngày làm việc", "hòa giải viên lao động phải kết thúc việc hòa giải", "hết thời hạn hòa giải quy định tại khoản 2 Điều 188"],
                r=("Thời hạn chỉ có ở B: \"Trong thời hạn 05 ngày làm việc\" ... \"hòa giải viên lao động phải kết thúc việc hòa giải\". Câu dẫn khoản 2 Điều 192 dẫn \"hết thời hạn hòa giải quy định tại khoản 2 Điều 188\"; điểm a, b là hai lựa chọn. "
                   "Có thể thêm khoản 1 Điều 192 (thủ tục theo khoản 2-6 Điều 188) nhưng không bắt buộc. "
                   "Lưu ý: README của bộ ghi \"câu l24 (B gồm hai đơn vị của Điều 45)\", thực ra đó là câu l25; B của l24 chỉ có một đơn vị.")),
    "l25": dict(v="can_B_gold_sai", c="vừa", rel=["lu45_3"], hl=["Trên tuyến đường đi từ nơi ở đến nơi làm việc", "Suy giảm khả năng lao động từ 5% trở lên", "đủ điều kiện hưởng theo quy định tại Điều 45 và Điều 46", "không được hưởng chế độ"],
                note="Thiếu khoản 3 Điều 45 Luật ATVSLĐ 84/2015.",
                r=("Quỹ trả phí giám định cho \"các trường hợp đủ điều kiện hưởng theo quy định tại Điều 45 và Điều 46\" (A), nên cần B. Cả hai đơn vị B đều cần: điểm c khoản 1 (tai nạn trên đường đi làm) và khoản 2 (\"Suy giảm khả năng lao động từ 5% trở lên\"). "
                   "Nhưng khoản 3 Điều 45 (người lao động \"không được hưởng chế độ\" khi thuộc nguyên nhân tại khoản 1 Điều 40) cũng là điều kiện và chưa có trong gold.")),
    "l26": dict(v="can_B_gold_sai", c="vừa", rel=["nd219_35_2"], hl=["Chủ tịch Ủy ban nhân dân cấp tỉnh", "Sở Lao động - Thương binh và Xã hội", "hết hiệu lực thi hành"],
                note="A và B lỗi thời từ 2025-08-07 theo khoản 2 Điều 35 NĐ 219/2025.",
                r=("Theo cặp A/B: khoản 1 Điều 5 NĐ 152/2020 ghi \"Chủ tịch Ủy ban nhân dân cấp tỉnh\", NĐ 70/2023 thay bằng \"Sở Lao động - Thương binh và Xã hội\", nên B cần. " + N219 +
                   "Điều 5 (tuyển người lao động nước ngoài) thuộc phần này. " + N219_TAIL + " Agent không tìm thấy quy định kê khai của nhà thầu tương ứng trong NĐ 219/2025.")),
    "l27": dict(v="can_B_gold_sai", c="vừa", rel=["nd219_35_2", "nd219_22_5"], hl=["trong vòng 3 ngày làm việc kể từ ngày người lao động nước ngoài bắt đầu làm việc", "trước ít nhất 3 ngày dự kiến làm việc", "hết hiệu lực thi hành"],
                note="A và B lỗi thời từ 2025-08-07; quy định hiện hành khác (khoản 5 Điều 22 NĐ 219/2025).",
                r=("Theo cặp A/B: NĐ 70/2023 bổ sung khoản 3 Điều 6 NĐ 152/2020: báo cáo \"trong vòng 3 ngày làm việc kể từ ngày người lao động nước ngoài bắt đầu làm việc\", nên B cần. " + N219 +
                   "Điều 6 (báo cáo sử dụng người lao động nước ngoài) thuộc phần này. " + N219_TAIL +
                   " Quy định cùng chủ đề trong NĐ 219/2025 khác hẳn: khoản 5 Điều 22 yêu cầu \"trước ít nhất 3 ngày dự kiến làm việc, người sử dụng lao động phải thông báo\".")),
    "l28": dict(v="can_B_gold_sai", c="vừa", rel=["nd219_35_2", "nd219_5_2"], hl=["dịch ra tiếng Việt và công chứng hoặc chứng thực", "dịch ra tiếng Việt và có chứng thực", "dịch ra tiếng Việt và chứng thực theo quy định của pháp luật", "hết hiệu lực thi hành"],
                note="A và B lỗi thời từ 2025-08-07; khoản 2 Điều 5 NĐ 219/2025 ghi \"dịch ra tiếng Việt và chứng thực\".",
                r=("Theo cặp A/B: NĐ 70/2023 thay \"dịch ra tiếng Việt và có chứng thực\" bằng \"dịch ra tiếng Việt và công chứng hoặc chứng thực\" tại điểm e khoản 3 Điều 8, nên B cần. " + N219 +
                   "Điều 8 (xác nhận không thuộc diện cấp giấy phép lao động) thuộc phần này. " + N219_TAIL +
                   " Quy định hiện hành trong NĐ 219/2025 khác đáp án: khoản 2 Điều 5 ghi \"Giấy tờ đã được hợp pháp hóa lãnh sự phải được dịch ra tiếng Việt và chứng thực theo quy định của pháp luật\" (không có \"công chứng\").")),
    "l29": dict(v="can_B_gold_sai", c="vừa", rel=["nd219_35_2", "nd219_5_2"], hl=["dịch ra tiếng Việt và công chứng hoặc chứng thực", "dịch ra tiếng Việt và chứng thực theo quy định của pháp luật", "hết hiệu lực thi hành"],
                note="A và B lỗi thời từ 2025-08-07; khoản 2 Điều 5 NĐ 219/2025 ghi \"dịch ra tiếng Việt và chứng thực\".",
                r=("Theo cặp A/B: NĐ 70/2023 thay \"dịch ra tiếng Việt và chứng thực\" bằng \"dịch ra tiếng Việt và công chứng hoặc chứng thực\" tại khoản 10 Điều 9, nên B cần. " + N219 +
                   "Điều 9 (hồ sơ cấp giấy phép lao động) thuộc phần này. " + N219_TAIL +
                   " Quy định hiện hành trong NĐ 219/2025 khác đáp án: khoản 2 Điều 5 ghi \"Giấy tờ đã được hợp pháp hóa lãnh sự phải được dịch ra tiếng Việt và chứng thực theo quy định của pháp luật\" (không có \"công chứng\").")),
    "l30": dict(v="khong_can_B_gold_dung", c="cao", hl=["ít nhất phải bằng 85% mức lương của công việc đó"],
                r="Câu đối chứng. Điều 26 BLLĐ (hiệu lực từ 2021-01-01, không có cạnh sửa đổi): \"ít nhất phải bằng 85% mức lương của công việc đó\", đủ trả lời một mình."),
    "l31": dict(v="khong_can_B_gold_dung", c="cao", hl=["Không quá 60 ngày", "từ cao đẳng trở lên"],
                r="Câu đối chứng. Khoản 2 Điều 25 BLLĐ: \"Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên\", đủ trả lời một mình."),
    "l32": dict(v="khong_can_B_gold_dung", c="cao", hl=["Ít nhất 45 ngày"],
                r="Câu đối chứng. Điểm a khoản 1 Điều 35 BLLĐ: \"Ít nhất 45 ngày nếu làm việc theo hợp đồng lao động không xác định thời hạn\", đủ trả lời một mình."),
    "l33": dict(v="khong_can_B_gold_dung", c="cao", hl=["Tết Âm lịch: 05 ngày", "được nghỉ làm việc, hưởng nguyên lương"],
                r="Câu đối chứng. Điểm b khoản 1 Điều 112 BLLĐ: \"Tết Âm lịch: 05 ngày\"; câu dẫn khoản 1 (hiện cùng đơn vị) nói \"được nghỉ làm việc, hưởng nguyên lương\". Đủ một mình."),
    "l34": dict(v="khong_can_B_gold_sai", c="vừa", rel=["bl105_2"], hl=["không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần", "không quá 10 giờ trong 01 ngày"],
                note="Có thể thiếu khoản 2 Điều 105 BLLĐ (10 giờ/ngày khi quy định theo tuần).",
                r=("Câu đối chứng, không cần B. Khoản 1 Điều 105 BLLĐ: \"không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần\". "
                   "Khoản 2 cùng Điều: nếu quy định theo tuần thì \"không quá 10 giờ trong 01 ngày\"; câu hỏi \"tối đa ... mỗi ngày\" nên cần thêm khoản 2, hoặc sửa câu hỏi cho rõ (theo ngày).")),
}


def parent_leads(gold_ids):
    """Immediate parents of gold units that are not gold themselves (their lead-in is printed next to the unit)."""
    out = []
    for g in gold_ids:
        p = UNITS[g].get("parent_id")
        if p in UNITS and p not in gold_ids and p not in out and UNITS[p]["unit_type"] in ("article", "clause", "point"):
            out.append(p)
    return out


def build_link():
    rows = list(csv.DictReader(open(LINK_DIR / "check-sheet.csv", encoding="utf-8-sig")))
    assert len(rows) == 35, len(rows)
    columns = list(rows[0].keys())
    qs = {q["question_id"]: q for q in json.load(open(LINK_DIR / "questions.json", encoding="utf-8"))["questions"]}
    items = []
    for r in rows:
        qid = r["question_id"]
        q, spec = qs[qid], LINK[qid]
        phrases = spec["hl"]
        gold = q["relevant_unit_ids"]
        btargets = q.get("link_target_unit_ids", [])
        as_of = q["as_of"]
        kind = {"a": "luật dẫn văn bản hướng dẫn", "b": "chế tài, thẩm quyền xử phạt", "c": "dẫn chiếu trong cùng văn bản",
                "d": "sửa đổi, bổ sung", "none": "đối chứng"}.get(q.get("link_type"), q.get("link_type"))
        fields = [{"label": f"Câu hỏi (ngày áp dụng {as_of}, loại {q.get('link_type')}: {kind})", "text": r["question"], "highlight": hl(r["question"], phrases)}]
        fields.append({"label": f"Đơn vị A: {r['A_label']}", "text": r["A_text"], "highlight": hl(r["A_text"], phrases)})
        leads = parent_leads(gold)
        if leads:
            lt = "\n".join(f"[{label(p)}] {text(p)}" for p in leads)
            fields.append({"label": "Câu dẫn hoặc tên Điều chứa các đơn vị trên (không thuộc gold, hiện cùng đơn vị trong ngữ cảnh)", "text": lt, "highlight": hl(lt, phrases)})
        if r["B_text"].strip():
            fields.append({"label": f"Đơn vị B: {r['B_label']}", "text": r["B_text"], "highlight": hl(r["B_text"], phrases)})
        else:
            fields.append({"label": "Đơn vị B", "text": r["B_label"], "highlight": []})
        fields.append({"label": "Đáp án tham chiếu (phần trong ngoặc kép phải có trong A, B hoặc câu dẫn của chúng)", "text": r["reference_answer"], "highlight": []})
        if q.get("stale_note"):
            fields.append({"label": "Ghi chú lỗi thời của bộ (stale_note)", "text": q["stale_note"], "highlight": []})
        doc_ids = []
        for g in gold + [U[k] for k in spec.get("rel", [])]:
            d = UNITS[g]["document_id"]
            if d not in doc_ids:
                doc_ids.append(d)
        status_lines = [f"{label(g)}: {STATUS_VI[V.status(g, as_of)]}" for g in gold]
        dt = "\n".join(doc_dates(d) for d in doc_ids) + f"\nTrạng thái máy tính tại {as_of} (unit-status-v2):\n" + "\n".join(status_lines)
        fields.append({"label": "Ngày hiệu lực và trạng thái", "text": dt, "highlight": hl(dt, ["hết hiệu lực từ 2026-11-15", "đã bị sửa đổi", "hiệu lực từ 2025-08-07"])})
        if spec.get("rel"):
            rt = "\n".join(f"[{label(U[k])}] {text(U[k])}" for k in spec["rel"])
            fields.append({"label": "Đơn vị liên quan agent tìm thấy (ngoài gold)", "text": rt, "highlight": hl(rt, phrases)})
        quotes = []
        for uid in gold + [U[k] for k in spec.get("rel", [])] + leads:
            for p in phrases:
                if p in text(uid) and len(quotes) < 4 and not any(x["text"] == p for x in quotes):
                    quotes.append({"label": label(uid), "text": p})
        export = dict(r)
        items.append({
            "id": qid,
            "group": f"loại {q.get('link_type')}",
            "heading": f"{qid} · {r['question'][:90]}{'...' if len(r['question']) > 90 else ''}",
            "question": "Câu hỏi có cần đơn vị B mới trả lời đủ không, và danh sách đáp án (A và B) có đủ, không thừa không?",
            "fields": fields,
            "suggestion": {"value": spec["v"], "reason": spec["r"], "confidence": spec["c"], "quotes": quotes,
                           **({"note": spec["note"]} if spec.get("note") else {})},
            "export": export,
        })
    task = {
        "task": "link",
        "title": "Bộ cần liên kết v1: có cần B không, gold có đúng không",
        "instructions": "\n".join([
            "Mỗi mục là một câu hỏi; một lần chọn trả lời luôn hai cột needs_B và gold_ok của phiếu.",
            "Đọc câu hỏi, đơn vị A, câu dẫn của chúng và đơn vị B.",
            "Cần B: thiếu B thì không trả lời đủ câu hỏi.",
            "Gold đúng: danh sách đáp án (A và B) đủ, không thiếu, không thừa, không có đơn vị lỗi thời tại ngày áp dụng.",
            "Đáp án tham chiếu: mọi phần trong ngoặc kép phải có trong A, B hoặc câu dẫn hiện cùng chúng.",
            "Câu đối chứng (l30-l34) không có B, chọn Không cần B.",
            "Câu loại d (l26-l29) dựa trên NĐ 152/2020: xem ô Đơn vị liên quan về khoản 2 Điều 35 NĐ 219/2025.",
            "Khi chọn gold sai, ghi đơn vị thiếu hoặc thừa ở ô ghi chú.",
        ]),
        "drafted_by": DRAFTED_BY,
        "export_columns": columns,
        "options": LINK_OPTIONS,
        "items": items,
    }
    return task


def check_task(task):
    values = {o["value"] for o in task["options"]}
    for o in task["options"]:
        assert set(o["csv"]) <= set(task["export_columns"]), o
    ids = [i["id"] for i in task["items"]]
    assert len(set(ids)) == len(ids)
    for it in task["items"]:
        assert it["suggestion"]["value"] in values, it["id"]
        assert it["suggestion"]["confidence"] in ("cao", "vừa", "thấp"), it["id"]
        for f in it["fields"]:
            for h in f["highlight"]:
                assert h in f["text"], (it["id"], h)
        blob = json.dumps(it, ensure_ascii=False)
        assert "\u2014" not in blob, it["id"]
    assert "\u2014" not in task["instructions"]


def main():
    validity, link = build_validity(), build_link()
    for task in (validity, link):
        check_task(task)
        (PACK / "data" / f"{task['task']}.json").write_text(json.dumps(task, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary = {"drafted_by": DRAFTED_BY, "sets": {}}
    for task in (validity, link):
        counts = Counter(i["suggestion"]["value"] for i in task["items"])
        conf = Counter(i["suggestion"]["confidence"] for i in task["items"])
        summary["sets"][task["task"]] = {
            "items": len(task["items"]),
            "suggested": dict(sorted(counts.items())),
            "confidence": dict(sorted(conf.items())),
            "low_confidence_ids": [i["id"] for i in task["items"] if i["suggestion"]["confidence"] == "thấp"],
            "medium_confidence_ids": [i["id"] for i in task["items"] if i["suggestion"]["confidence"] == "vừa"],
            "not_default_ids": [i["id"] for i in task["items"] if i["suggestion"]["value"] not in ("co", "can_B_gold_dung")],
        }
    summary["sets"]["link"]["problems"] = {qid: LINK[qid].get("note") for qid in LINK if LINK[qid].get("note")}
    summary["sets"]["validity"]["problems"] = {
        "hl-a05|dap-an|283-2026-nd-cp/chapter-iii/article-43/clause-3": "Tập đáp án có thể thiếu khoản 1 Điều 43 NĐ 283/2026 (cảnh cáo khi số tiền dưới 400.000 đồng).",
        "hl-b01|dap-an|41-2024-qh15/chapter-i/article-2/clause-1": "Đơn vị là câu dẫn; chỉ số mở thành mọi điểm a-n, rộng hơn danh sách a, b, c, d, đ, e, i, l.",
        "hl-d05|dap-an|45-2019-qh14/chapter-iii/section-3/article-46/clause-1": "Theo quy ước 15/11 (2) có thể cần thêm khoản 1 Điều 8 NĐ 145/2020.",
    }
    (PACK / "work" / "check-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {"suggested": v["suggested"], "low": v["low_confidence_ids"]} for k, v in summary["sets"].items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
