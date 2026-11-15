"""Build cases.jsonl in this folder: MODEL REVIEW of the case scenario set on corpus v3 (15/11/2026), not human labels.

Every decision (units kept, dropped, added; issues dropped; as_of) is written out below with its reason; unit IDs and
quotes are in cases_quotes.py. Run check-cases.py afterwards. Usage: python build-cases.py
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases_quotes import Q, U  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "cases.jsonl"
UNITS = {json.loads(l)["unit_id"]: json.loads(l) for l in (ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b/units.jsonl").open(encoding="utf-8")}
PREV = {json.loads(l)["question_id"]: json.loads(l) for l in (ROOT / "experiments/label-review-2026-11-12/cases.jsonl").open(encoding="utf-8")}
QS = json.loads((ROOT / "experiments/runs/dryrun-cases-v1/questions.json").read_text(encoding="utf-8"))["questions"]
DRAFTS = {d["text"]: d for d in json.loads((ROOT / "experiments/question-drafts-cases-v1/drafts.json").read_text(encoding="utf-8"))}
EXCLUDED = ["k01", "k09", "k15", "k17", "k24", "k25", "k26", "k40", "k41"]
LOCK = "2026-11-11"
KEY = {v: k for k, v in U.items()}
sys.path.insert(0, str(ROOT / "src"))
from legal_ai.kb.validity import Validity  # noqa: E402
_B = ROOT / "data/normalized/experiment-scope-v3-v48feefc6d53b"
VALIDITY = Validity([json.loads(l) for l in (_B / "documents.jsonl").open(encoding="utf-8")], list(UNITS.values()),
                    [json.loads(l) for l in (ROOT / "data/kb/amendments-scope-v3-v48feefc6d53b/edges.jsonl").open(encoding="utf-8")])

PRE2021 = ("Không có văn bản nào trong corpus v3 có hiệu lực tại ngày đó cho các vấn đề này, nên `as_of` để trống; "
           "đơn vị là quy định tương ứng hiện hành và được kiểm hiệu lực tại ngày khóa corpus v3 (2026-11-11, `checked_at`) "
           "theo quy ước 15/11 cho câu không ghi ngày.")

R = {}


def rec(qid, as_of, src, final, dropped=None, added=None, issues_dropped=None, outside=None, conf="medium", note="", changed=""):
    R[qid] = dict(as_of=as_of, src=src, final=final, dropped=dropped or {}, added=added or {}, issues_dropped=issues_dropped or {},
                  outside=outside or [], conf=conf, note=note, changed=changed)


# ---------------------------------------------------------------- records
rec("k00", "2021-09-15",
    "case-research-v1 c01, facts: \"Ngày 01/8/2021 trường thông báo chấm dứt hợp đồng từ 15/9/2021\" (ngày chấm dứt có hiệu lực).",
    [("a36_1c", "Bản án viện dẫn điểm c khoản 1 Điều 36 BLLĐ 2019"),
     ("a36_2a", "Bản án viện dẫn điểm a khoản 2 Điều 36 BLLĐ 2019 (đã báo trước đủ 45 ngày)"),
     ("a30_1h", "Bản án viện dẫn điểm h khoản 1 Điều 30 (người lao động không đồng ý tạm hoãn)"),
     ("a48_1", "Bản án viện dẫn Điều 48: đã thanh toán đủ các khoản"),
     ("a48_3a", "Bản án viện dẫn Điều 48; facts ghi trường đã chốt sổ bảo hiểm")],
    dropped={"a46_1": "Hồ sơ không ghi bản án viện dẫn Điều 46; tòa chỉ kết luận đã thanh toán đủ các khoản theo Điều 48. Quy ước 15/11 chỉ giữ căn cứ tòa dựa vào."},
    outside=["Khoản 1 Điều 6 Thông tư liên tịch 06/2015/TTLT-BGDĐT-BNV (thẩm quyền, vị trí việc làm tại trường công lập)"],
    conf="high",
    note="Mọi đơn vị là căn cứ bản án nêu đích danh (điểm c khoản 1, điểm a khoản 2 Điều 36, điểm h khoản 1 Điều 30, Điều 48). Vấn đề \"Trợ cấp thôi việc\" tòa chỉ xét qua kết luận đã thanh toán đủ theo Điều 48, không viện dẫn Điều 46; nếu người gán đọc bản án và thấy tòa dẫn Điều 46 thì thêm lại khoản 1 Điều 46. Thẩm quyền ký quyết định tại trường công lập cần văn bản ngoài corpus.",
    changed="Bỏ khoản 1 Điều 46 vì bản án không viện dẫn; các đơn vị khác giữ nguyên.")

K02_FINAL = [("a42_2a", "Tòa xác nhận công ty đã chứng minh lý do kinh tế (suy thoái kinh tế, giảm đơn hàng) theo Điều 42"),
             ("a42_6", "Căn cứ quyết định: khoản 6 Điều 42 (không thông báo Ủy ban nhân dân cấp tỉnh)"),
             ("a42_4", "Bản án viện dẫn Điều 42, Điều 44: công ty phải lập phương án sử dụng lao động"),
             ("a44_2", "Bản án viện dẫn Điều 44: trao đổi với tổ chức đại diện người lao động"),
             ("a41_1", "Bản án viện dẫn Điều 41: lương những ngày không được làm việc, 02 tháng lương, đóng bảo hiểm"),
             ("a104_1", "Bản án viện dẫn Điều 104 để bác yêu cầu thưởng tháng 13")]
K02 = dict(dropped={"a39": "Bản án không viện dẫn Điều 39 (căn cứ ghi: Điều 36, 41, khoản 6 Điều 42, Điều 44, 90, 104 BLLĐ 2019 và Luật BHXH 2014); Điều 39 chỉ là định nghĩa nên bỏ theo quy ước chỉ giữ căn cứ tòa dựa vào.",
                     "b13_4": "Luật BHXH 41/2024 có hiệu lực từ 01/07/2025, sau ngày xảy ra sự việc (03/01/2023): validity.py trả về not_yet_effective. Tòa áp dụng Luật BHXH 2014 (Điều 18, 19, 21, 22), văn bản này không có trong corpus v3 nên không có đơn vị thay thế; nghĩa vụ đóng bảo hiểm cho thời gian không được làm việc đã nằm trong khoản 1 Điều 41."},
           issues_dropped={"Trợ cấp mất việc làm": "Tòa không xét trợ cấp mất việc làm; hậu quả được giải quyết bằng bồi thường theo Điều 41 (lượt 12/11 cũng đã bỏ khoản 1 Điều 47 vì lý do này)."},
           outside=["Điều 18, 19, 21, 22 Luật BHXH 2014 (luật áp dụng ngày 03/01/2023; không có trong corpus v3, Luật BHXH 2024 khi đó chưa có hiệu lực)"])
K02_NOTE = ("Căn cứ quyết định: khoản 6 Điều 42 (không thông báo Ủy ban nhân dân cấp tỉnh) và Điều 41. Điểm a khoản 2 Điều 42 là lý do kinh tế tòa chấp nhận; khoản 4 Điều 42 và khoản 2 Điều 44 theo Điều 44 được viện dẫn; khoản 1 Điều 104 để bác thưởng tháng 13. "
            "Phần Luật BHXH 2014 tòa viện dẫn không có trong corpus. Điều 36 và Điều 90 được viện dẫn chung, không xác định được điểm, khoản nên không gán.")
K02_CHANGED = "Bỏ Điều 39 (bản án không viện dẫn) và khoản 4 Điều 13 Luật BHXH 2024 (chưa có hiệu lực ngày 03/01/2023); bỏ vấn đề trợ cấp mất việc làm khỏi danh sách vì tòa không xét."
K02_SRC = "case-research-v1 c03, facts: \"Ngày 03/12/2022 công ty thông báo và ra quyết định cho thôi việc từ 03/01/2023\"."
rec("k02", "2023-01-03", K02_SRC, K02_FINAL, conf="medium", note=K02_NOTE, changed=K02_CHANGED, **K02)
rec("k38", "2023-01-03", K02_SRC, K02_FINAL, conf="medium", note="Diễn đạt lại của k02 (cùng vụ c03), nhãn giống k02. " + K02_NOTE, changed=K02_CHANGED, **K02)

rec("k03", None,
    "Sự việc tháng 6-7/2019 (facts c04: thông báo ngừng việc từ 01/7/2019); tòa áp dụng Điều 36 Bộ luật Lao động 2012, không có trong corpus v3 (BLLĐ 2019 có hiệu lực từ 01/01/2021). " + PRE2021,
    [("a34_3", "Điều 36 BLLĐ 2012 (các trường hợp chấm dứt), case-research ghi tương ứng Điều 34 BLLĐ 2019; tòa kết luận người lao động đã đồng ý nghỉ")],
    dropped={"a14_1": "Bản án chỉ viện dẫn Điều 36 BLLĐ 2012 và khoản 1 Điều 308 BLTTDS; tòa không xét hình thức hợp đồng.",
             "a14_2": "Bản án chỉ viện dẫn Điều 36 BLLĐ 2012 và khoản 1 Điều 308 BLTTDS; tòa không xét hiệu lực của hợp đồng bằng lời nói.",
             "a46_1": "Tòa dùng việc đã nhận trợ cấp thôi việc làm chứng cứ của thỏa thuận, không viện dẫn quy định về trợ cấp thôi việc."},
    issues_dropped={"Hình thức hợp đồng lao động": "Kết quả và căn cứ của bản án không có nhận định về hiệu lực của hợp đồng bằng lời nói.",
                    "Thông báo chấm dứt bằng văn bản": "Tòa không xét nghĩa vụ thông báo bằng văn bản (lượt 12/11 đã bỏ khoản 1 Điều 45 vì lý do này)."},
    outside=["Điều 36 Bộ luật Lao động 2012 (luật áp dụng)", "Khoản 1 Điều 308 Bộ luật Tố tụng dân sự 2015 (chứng minh)"],
    conf="low",
    note="Sự việc 2019 theo BLLĐ 2012, không có trong corpus v3; khoản 3 Điều 34 BLLĐ 2019 là quy định tương ứng theo ghi chú case-research, chưa đối chiếu được với chữ của luật cũ. Vấn đề \"Trợ cấp thôi việc đã nhận\" tòa xét như chứng cứ, không có điều luật nội dung. Người gán nên cân nhắc loại câu nếu bộ chỉ giữ câu có luật áp dụng nằm trong corpus.",
    changed="Bỏ khoản 1, khoản 2 Điều 14 và khoản 1 Điều 46 (bản án không dựa vào); bỏ hai vấn đề tòa không xét; hạ tin cậy xuống thấp vì luật áp dụng (BLLĐ 2012) không có trong corpus.")

rec("k04", "2022-04-01",
    "case-research-v1 c05, facts: \"ngày 21/3/2022 chị nộp đơn xin thôi việc từ 01/4/2022 và công ty ra quyết định chấm dứt từ ngày đó\".",
    [("a34_1", "Bản án viện dẫn khoản 1 Điều 34 BLLĐ 2019"),
     ("a34_3", "Bản án viện dẫn khoản 3 Điều 34: chấm dứt theo đơn xin thôi việc được công ty chấp thuận"),
     ("a20_2b", "Bản án viện dẫn điểm b khoản 2 Điều 20 khi xét hợp đồng cũ có chuyển thành không xác định thời hạn"),
     ("a45_1", "Bản án viện dẫn Điều 45; facts: công ty thông báo chấm dứt khi hết hạn ngày 02/3/2022")],
    dropped={"a25": "Hồ sơ không ghi bản án viện dẫn Điều 25; tòa chỉ nhận định việc ký lại hợp đồng là không đúng quy định, không nêu điều luật.",
             "nd12_10_2a": "Tòa không xét xử phạt hành chính nên vấn đề chế tài bị bỏ. Đơn vị vẫn có hiệu lực ngày 01/04/2022 (NĐ 12/2022 hiệu lực từ 17/01/2022), bỏ vì không phải căn cứ tòa dùng."},
    issues_dropped={"Chế tài hành chính khi thử việc quá một lần": "Bản án không xét xử phạt hành chính."},
    conf="medium",
    note="Căn cứ bản án: khoản 1, khoản 3 Điều 34, điểm b khoản 2 Điều 20, Điều 45. Vấn đề \"Thử việc lần hai\" được giữ vì tòa có nhận định việc ký lại là không đúng quy định, nhưng hồ sơ không ghi điều luật cho nhận định đó; người gán nên mở bản án (đường dẫn trong case-research c05) và thêm câu dẫn Điều 25 nếu tòa viện dẫn nó.",
    changed="Bỏ Điều 25 và điểm a khoản 2 Điều 10 NĐ 12/2022 vì bản án không dựa vào; bỏ vấn đề chế tài hành chính khỏi danh sách.")

rec("k05", "2021-06-15",
    "case-research-v1 c06, facts: nghỉ việc từ 01/3/2021 và \"đến 15/6/2021 ký hợp đồng lao động trực tiếp với chính nhà máy\" (hành vi bị cho là vi phạm thỏa thuận).",
    [("a5_1a", "Bản án viện dẫn Điều 5 BLLĐ 2019: quyền tự do lựa chọn việc làm"),
     ("a10_1", "Bản án viện dẫn Điều 10 BLLĐ 2019")],
    dropped={"a21_2": "Tòa không viện dẫn khoản 2 Điều 21; căn cứ bản án là Điều 35 Hiến pháp, Điều 5, Điều 10 BLLĐ 2019 và khoản 2 Điều 308 BLTTDS."},
    issues_dropped={"Điều kiện thỏa thuận bảo vệ bí mật kinh doanh": "Tòa không xét điều kiện của thỏa thuận bảo mật; tòa chỉ kết luận công ty không chứng minh được việc lộ bí mật, thuộc vấn đề \"Điều kiện để đòi bồi thường\"."},
    outside=["Điều 35 Hiến pháp 2013", "Khoản 2 Điều 308 Bộ luật Tố tụng dân sự 2015 (nghĩa vụ chứng minh)", "Bộ luật Dân sự (phạt vi phạm, bồi thường)"],
    conf="medium",
    note="Căn cứ nội dung trong corpus: điểm a khoản 1 Điều 5 và khoản 1 Điều 10 BLLĐ 2019. \"Điều kiện để đòi bồi thường\" tòa giải quyết bằng nghĩa vụ chứng minh (BLTTDS), không có đơn vị trong corpus. Thỏa thuận ký năm 2019 nhưng hành vi và tranh chấp xảy ra năm 2021, tòa áp dụng BLLĐ 2019.",
    changed="Bỏ khoản 2 Điều 21 (tòa không viện dẫn) và vấn đề điều kiện thỏa thuận bảo mật.")

rec("k06", "2022-10-01",
    "case-research-v1 c07, facts: nghỉ từ 19/8/2022 đến 30/9/2022, \"đi làm lại 12 ngày trong tháng 10/2022 thì nhận quyết định chấm dứt\"; ngày quyết định không ghi, lấy 01/10/2022 (mọi ngày trong tháng 10/2022 cho cùng kết quả hiệu lực).",
    [("a36_1e", "Bản án ghi điểm c khoản 1 Điều 36, nhưng tình tiết tự ý bỏ việc từ 05 ngày làm việc liên tục thuộc điểm e (ghi chú case-research c07)"),
     ("a36_3", "Bản án viện dẫn khoản 3 Điều 36; chữ khoản 3 chỉ miễn báo trước cho điểm d và e"),
     ("a29_1", "Bản án viện dẫn Điều 29: việc điều chuyển đã được người lao động đồng ý")],
    dropped={"a29_2": "Tòa dựa vào sự đồng ý của người lao động (khoản 1 Điều 29); hồ sơ không có nhận định về thời hạn báo trước khi điều chuyển (khoản 2)."},
    conf="high",
    note="Bản án viết điểm c khoản 1 Điều 36 nhưng chữ của khoản 3 Điều 36 (bản án cũng viện dẫn) chỉ miễn báo trước cho điểm d và e, và tình tiết là tự ý bỏ việc từ 05 ngày làm việc liên tục, nên chọn điểm e. Điều 20 viện dẫn chung, câu hỏi không hỏi loại hợp đồng.",
    changed="Bỏ khoản 2 Điều 29 vì tòa chỉ dựa vào sự đồng ý theo khoản 1.")

rec("k07", "2024-02-01",
    "case-research-v1 c08, facts: \"tháng 02/2024 bị ra quyết định chấm dứt hợp đồng vì lý do tái cấu trúc\"; ngày không ghi, lấy 01/02/2024.",
    [("a42_1a", "Bản án viện dẫn Điều 42; công ty quyết định thay đổi cơ cấu"),
     ("a42_3", "Bản án viện dẫn Điều 42, Điều 44: phương án sử dụng lao động khi thay đổi cơ cấu"),
     ("a42_4", "Bản án viện dẫn Điều 42: tòa xác định công ty chứng minh lý do kinh tế"),
     ("a42_6", "Bản án viện dẫn Điều 42: trao đổi với tổ chức đại diện người lao động, thông báo trước"),
     ("a44_1c", "Bản án viện dẫn Điều 44; tòa chấp nhận phương án dù người bị cắt giảm được chọn ngẫu nhiên theo trạm, chuyền"),
     ("a44_2", "Bản án viện dẫn Điều 44: trao đổi ý kiến khi xây dựng phương án")],
    dropped={"a47_1": "Bản án viện dẫn Điều 46, không viện dẫn Điều 47, và người lao động không yêu cầu trợ cấp; tòa không xét trợ cấp mất việc làm.",
             "a42_5": "Khoản 5 Điều 42 chỉ dẫn chiếu trợ cấp mất việc làm, vấn đề tòa không xét."},
    issues_dropped={"Trợ cấp mất việc làm": "Người lao động yêu cầu hủy quyết định, nhận lại làm việc và bồi thường, không yêu cầu trợ cấp; bản án viện dẫn Điều 46 nhưng hồ sơ ghi không rõ công ty đã trả trợ cấp nào."},
    outside=["Điều 12, 14 Nghị quyết 326/2016/UBTVQH14 (án phí)"],
    conf="medium",
    note="Tòa kết luận công ty chứng minh lý do kinh tế và làm đúng Điều 42, Điều 44. Hồ sơ nêu cả thay đổi cơ cấu và lý do kinh tế nên giữ cả khoản 3 và khoản 4 Điều 42. Về tiêu chí lựa chọn, tòa chấp nhận cách chọn ngẫu nhiên; điểm c khoản 1 Điều 44 là nội dung phương án gần nhất, không có quy định nào trong corpus bắt buộc tiêu chí. Điều 13, 90, 94, 95 viện dẫn chung, không gán. Người gán có thể xem bản án để biết vì sao tòa dẫn Điều 46.",
    changed="Bỏ khoản 1 Điều 47 và khoản 5 Điều 42; bỏ vấn đề trợ cấp mất việc làm khỏi danh sách vì tòa không xét.")

rec("k08", "2022-06-13",
    "case-research-v1 c09, facts: \"Ngày 12/5/2022 công ty thông báo đơn phương chấm dứt từ 13/6/2022\".",
    [("a16_2", "Bản án viện dẫn khoản 2 Điều 16 BLLĐ 2019"),
     ("a36_1g", "Bản án viện dẫn điểm g khoản 1 Điều 36"),
     ("a36_2b", "Bản án viện dẫn điểm b khoản 2 Điều 36"),
     ("a20_1b", "Bản án viện dẫn Điều 20; áp thời hạn báo trước 30 ngày tức coi là hợp đồng xác định thời hạn 01 năm")],
    outside=["Điều 38, 592 Bộ luật Dân sự 2015; điểm c khoản 2 Điều 84 Nghị định 15/2020; khoản 1 Điều 3 Luật An toàn thông tin mạng (yêu cầu về dữ liệu cá nhân)"],
    conf="medium",
    note="Căn cứ bản án: khoản 2 Điều 16, điểm g khoản 1 và điểm b khoản 2 Điều 36. Điểm b khoản 1 Điều 20 suy từ việc bản án viện dẫn Điều 20 và áp thời hạn báo trước 30 ngày. Điều 38, 41, 48 viện dẫn để bác yêu cầu, không gắn với câu hỏi.",
    changed="Không đổi đơn vị; thêm ngày áp dụng.")

rec("k10", None,
    "Sự việc 2016-2018 (facts c11: xin nghỉ từ 01/8/2018); tòa áp dụng Điều 43, Điều 62 BLLĐ 2012, không có trong corpus v3; case-research ghi tương ứng Điều 40, Điều 62 BLLĐ 2019. " + PRE2021,
    [("a62_1", "Điều 62 BLLĐ 2012, tương ứng Điều 62 BLLĐ 2019 (case-research)"),
     ("a62_2c", "Điều 62 BLLĐ 2012: cam kết làm việc 05 năm sau khóa học"),
     ("a62_2d", "Điều 62 BLLĐ 2012: chi phí đào tạo và trách nhiệm hoàn trả"),
     ("a62_3", "Điều 62 BLLĐ 2012: phạm vi chi phí đào tạo (học phí, sinh hoạt phí, bảo hiểm)", "a62_3_items"),
     ("a40_3", "Điều 43 BLLĐ 2012, tương ứng khoản 3 Điều 40 BLLĐ 2019 (case-research)")],
    outside=["Điều 43, 62 Bộ luật Lao động 2012 (luật áp dụng)", "Điều 3, 357, 418 Bộ luật Dân sự 2015 (phạt vi phạm, lãi chậm trả; căn cứ không chấp nhận mức gấp 04 lần)"],
    conf="low",
    note="Theo BLLĐ 2012 tòa áp dụng nghĩa vụ hoàn trả chi phí đào tạo (Điều 43, Điều 62). Khi đặt sang BLLĐ 2019 cần lưu ý: khoản 1 Điều 35 cho người lao động quyền đơn phương chấm dứt khi báo trước, nên khoản 3 Điều 40 chỉ áp dụng nếu việc nghỉ là trái pháp luật; nghĩa vụ hoàn trả theo hợp đồng đào tạo (điểm d khoản 2 Điều 62) vẫn đứng. Mức gấp 04 lần và cam kết trả nợ thuộc BLDS, ngoài corpus. Người gán nên cân nhắc loại câu vì luật áp dụng không có trong corpus.",
    changed="Giữ nguyên đơn vị; hạ tin cậy xuống thấp vì tòa áp dụng BLLĐ 2012, không có trong corpus v3.")

rec("k11", "2024-01-01",
    "case-research-v1 c12, facts: \"Một tuần sau khi sang nước ngoài (đầu năm 2024), anh tự ý rời ký túc xá, bỏ khóa học\"; ngày không ghi, lấy 01/01/2024.",
    [("a40_3", "Bản án viện dẫn khoản 3 Điều 40 BLLĐ 2019"),
     ("a62_2c", "Bản án viện dẫn Điều 62: cam kết làm việc ít nhất 01 năm sau đào tạo"),
     ("a62_2d", "Bản án viện dẫn Điều 62: chi phí đào tạo và trách nhiệm hoàn trả"),
     ("a62_3", "Bản án viện dẫn Điều 62: chi phí đào tạo ở nước ngoài gồm đi lại, sinh hoạt (vé máy bay, visa, ăn ở)")],
    dropped={"a36_1e": "Bản án không viện dẫn; tòa không xét quyết định sa thải mà coi đây là người lao động đơn phương chấm dứt trái pháp luật (Điều 40).",
             "a125_4": "Bản án không viện dẫn; tòa không xét quyết định sa thải.",
             "a40_2": "Công ty đã rút yêu cầu nửa tháng lương và tiền vi phạm báo trước; tòa đình chỉ phần này nên khoản 2 Điều 40 không được áp dụng."},
    issues_dropped={"Lựa chọn giữa đơn phương chấm dứt và sa thải": "Tòa không xét quyết định sa thải của công ty; tòa chỉ giải quyết yêu cầu hoàn trả chi phí đào tạo theo Điều 40, Điều 62."},
    outside=["Điều 418, 419 Bộ luật Dân sự 2015 (phạt gấp 02 lần chi phí đào tạo)"],
    conf="medium",
    note="Căn cứ bản án: khoản 2, khoản 3 Điều 40 và Điều 62; phần khoản 2 Điều 40 đã bị rút nên không gán. Điểm b khoản 1 Điều 20 và khoản 1 Điều 187 viện dẫn cho loại hợp đồng và thẩm quyền, câu hỏi không hỏi. Bản án sơ thẩm, có thể đã bị kháng cáo.",
    changed="Bỏ điểm e khoản 1 Điều 36, khoản 4 Điều 125 (tòa không viện dẫn) và khoản 2 Điều 40 (yêu cầu đã rút); bỏ vấn đề lựa chọn chấm dứt hay sa thải.")

K12_FINAL = [("a13_1", "Bản án viện dẫn Điều 13: thỏa thuận miệng có trả công là hợp đồng lao động"),
             ("a25_3", "Bản án viện dẫn khoản 3 Điều 25: thử việc tối đa 30 ngày với công nhân kỹ thuật"),
             ("a27_1", "Bản án viện dẫn khoản 1 Điều 27: hết thử việc phải thông báo kết quả"),
             ("a36_2b", "Bản án viện dẫn điểm b khoản 2 Điều 36: 30 ngày lương vi phạm báo trước"),
             ("a41_1", "Bản án viện dẫn Điều 41: lương 9 tháng không được làm việc, 02 tháng lương, tiền vi phạm báo trước, truy đóng bảo hiểm")]
K12_ID = {"Từ chối làm thêm giờ": "Tòa không xét quyền từ chối làm thêm giờ.",
          "Phạt tiền thay xử lý kỷ luật": "Tòa không xét việc đề nghị phạt tiền; kết luận là công ty đơn phương chấm dứt trái pháp luật."}
K12_DROP = {"a39": "Bản án không viện dẫn Điều 39 (căn cứ: Điều 13, khoản 2 Điều 15, khoản 3 Điều 25, khoản 1 Điều 27, điểm b khoản 2 Điều 36, Điều 41).",
            "a127_2": "Tòa không viện dẫn và không xét việc đề nghị phạt 01 triệu đồng; vấn đề này bị bỏ khỏi danh sách."}
K12_NOTE = ("Căn cứ bản án: Điều 13, khoản 3 Điều 25, khoản 1 Điều 27, điểm b khoản 2 Điều 36 và Điều 41 (tiền vi phạm báo trước nằm ở đoạn cuối khoản 1 Điều 41). Khoản 2 Điều 15 viện dẫn chung, không gán. "
            "Tòa tính tiền lương bồi thường gồm lương cơ bản và phụ cấp gắn với công việc nhưng hồ sơ không ghi điều luật cho cách tính này.")
K12_SRC = "case-research-v1 c14, facts: \"Ngày 29/11/2022 vì mệt anh xin không tăng ca ... Hôm sau công ty cho anh chọn bị phạt 1 triệu đồng hoặc viết đơn xin thôi việc\" (30/11/2022)."
rec("k12", "2022-11-30", K12_SRC, K12_FINAL, dropped=K12_DROP, issues_dropped=K12_ID, outside=["Khoản 2 Điều 92 Bộ luật Tố tụng dân sự 2015"], conf="medium", note=K12_NOTE,
    changed="Bỏ Điều 39 (không viện dẫn) và khoản 2 Điều 127 (tòa không xét); bỏ hai vấn đề tòa không xét.")
rec("k39", "2022-11-30", K12_SRC, K12_FINAL, dropped={"a39": K12_DROP["a39"]}, issues_dropped=K12_ID, outside=["Khoản 2 Điều 92 Bộ luật Tố tụng dân sự 2015"], conf="medium",
    note="Diễn đạt lại của k12 (cùng vụ c14), chỉ hỏi các khoản phải trả; nhãn giống k12. " + K12_NOTE,
    changed="Bỏ Điều 39 (bản án không viện dẫn); bỏ hai vấn đề tòa không xét; nhãn nay giống k12.")

rec("k13", "2023-04-01",
    "case-research-v1 c15, facts: \"Tháng 4/2023 đội sản xuất bốc thăm lô cạo mới ... rồi nhận thông báo công ty chấm dứt hợp đồng\"; ngày không ghi, lấy 01/04/2023.",
    [("a20_1b", "Bản án viện dẫn điểm b khoản 1 Điều 20"),
     ("a34_1", "Bản án viện dẫn khoản 1 Điều 34: chấm dứt do hết hạn"),
     ("a39", "Bản án viện dẫn Điều 39 để kết luận không đơn phương chấm dứt trái pháp luật"),
     ("a45_1", "Bản án viện dẫn khoản 1 Điều 45"),
     ("a177_4", "Bản án viện dẫn khoản 4 Điều 177: không thuộc trường hợp thành viên ban lãnh đạo tổ chức đại diện")],
    dropped={"a20_2c": "Bản án không phân tích số lần ký hợp đồng liên tiếp (ghi chú case-research c15); vấn đề bị bỏ.",
             "a14_1": "Tòa không xét nghĩa vụ giao một bản hợp đồng; vấn đề bị bỏ."},
    issues_dropped={"Giới hạn số lần ký hợp đồng xác định thời hạn": "Bản án không phân tích việc số lần ký liên tiếp đã vượt giới hạn hay chưa (notes c15).",
                    "Nghĩa vụ giao một bản hợp đồng": "Kết quả bản án không có nhận định về việc không giao bản hợp đồng."},
    conf="medium",
    note="Căn cứ bản án: điểm b khoản 1 Điều 20, khoản 1 Điều 34, Điều 39, khoản 1 Điều 45, khoản 4 Điều 177. Câu hỏi còn hỏi cách ký liên tiếp và việc không giao bản hợp đồng, nhưng tòa không xét hai điểm này nên chúng không có đơn vị.",
    changed="Bỏ điểm c khoản 2 Điều 20 và khoản 1 Điều 14 cùng hai vấn đề tòa không xét.")

rec("k14", "2023-01-01",
    "case-research-v1 c16, facts: \"Từ 01/01/2023 đơn vị thay đổi mô hình hoạt động, giải thể ban quản lý nhà khách và ra quyết định chấm dứt hợp đồng\".",
    [("a36_1c", "Bản án viện dẫn điểm c khoản 1 Điều 36 BLLĐ 2019"),
     ("a36_2a", "Bản án viện dẫn điểm a khoản 2 Điều 36"),
     ("a42_1a", "Bản án viện dẫn Điều 42; tình tiết giải thể ban quản lý nhà khách, thay đổi mô hình"),
     ("a47_1", "Bản án viện dẫn Điều 47: trợ cấp mất việc làm"),
     ("n8_2", "Nhắc lại khoản 1 Điều 47 trong NĐ 145/2020 (quy ước 15/11 về quy định nhắc lại)")],
    added={"n8_2": ("Khoản 2 Điều 8 NĐ 145/2020 nêu cùng quy tắc với khoản 1 Điều 47 BLLĐ mà bản án viện dẫn (trả trợ cấp mất việc làm cho người làm thường xuyên từ đủ 12 tháng bị mất việc theo khoản 11 Điều 34); quy ước 15/11 chọn cả hai đơn vị.", "a47_1")},
    dropped={"a137_1b": "Bản án không phân tích việc bố trí làm đêm khi nuôi con dưới 12 tháng; Điều 137 chỉ là căn cứ gợi ý (notes c16).",
             "a98_1a": "Tòa buộc trả 600.000 đồng tiền làm thêm giờ nhưng Điều 98 không có trong danh sách căn cứ của bản án.",
             "a107_2b": "Tòa không xét giới hạn làm thêm giờ; Điều 107 không có trong căn cứ."},
    issues_dropped={"Bảo vệ lao động nuôi con dưới 12 tháng tuổi": "Vấn đề chỉ có trong lời trình bày của nguyên đơn, bản án không phân tích riêng (notes c16)."},
    outside=["Nghị định 34/2012/NĐ-CP (phụ cấp công vụ)"],
    conf="medium",
    note="Tòa viện dẫn cả điểm c khoản 1 Điều 36 và Điều 42 cho việc chấm dứt, điểm a khoản 2 Điều 36 cho báo trước và Điều 47 cho trợ cấp mất việc làm. Điều 42 viện dẫn chung; tình tiết giải thể bộ phận khớp điểm a khoản 1 Điều 42. Vấn đề tiền làm thêm giờ được giữ vì tòa buộc trả 600.000 đồng, nhưng hồ sơ không ghi điều luật; người gán nên xem bản án để quyết định có thêm điểm a khoản 1 Điều 98 không. Điều 41 viện dẫn để bác yêu cầu, không gán.",
    changed="Bỏ điểm b khoản 1 Điều 137, điểm a khoản 1 Điều 98, điểm b khoản 2 Điều 107 (không phải căn cứ bản án); thêm khoản 2 Điều 8 NĐ 145/2020 (nhắc lại khoản 1 Điều 47); bỏ vấn đề bảo vệ lao động nuôi con nhỏ.")

rec("k16", None,
    "Sự việc tháng 7-8/2011 (facts c18); tòa áp dụng khoản 1, khoản 4 Điều 30 BLLĐ 1994 về nội dung, không có trong corpus v3; case-research ghi quy định tương ứng hiện nay là Điều 18, 49-51 BLLĐ 2019. " + PRE2021,
    [("a18_1", "Khoản 1 Điều 30 BLLĐ 1994 (giao kết trực tiếp), tương ứng khoản 1 Điều 18 BLLĐ 2019 theo lượt 12/11 và case-research"),
     ("a49_1b", "Tòa tuyên vô hiệu vì không đúng người lao động giao kết; case-research ghi tương ứng Điều 49 BLLĐ 2019")],
    dropped={"a18_4b": "Tòa tuyên vô hiệu vì không đúng người giao kết, không xét điều kiện giao kết với người chưa thành niên.",
             "a50": "Hồ sơ không ghi tòa viện dẫn quy định về thẩm quyền tuyên bố vô hiệu; vấn đề bị bỏ.",
             "n10_1": "Tòa không giải quyết hậu quả hợp đồng vô hiệu vì nguyên đơn không yêu cầu."},
    issues_dropped={"Giao kết với người chưa thành niên": "Tòa không xét điều kiện giao kết với người chưa thành niên; căn cứ tuyên vô hiệu là không đúng người giao kết.",
                    "Thẩm quyền tuyên bố vô hiệu và xử lý hợp đồng vô hiệu": "Tòa không giải quyết hậu quả của hợp đồng vô hiệu vì nguyên đơn không yêu cầu, và hồ sơ không ghi căn cứ về thẩm quyền."},
    outside=["Khoản 1, khoản 4 Điều 30 Bộ luật Lao động 1994 (luật áp dụng)", "Khoản 2, 7 Điều 188 và Điều 190 BLLĐ 2019 (hòa giải, thời hiệu; tòa viện dẫn về tố tụng, câu hỏi không hỏi)"],
    conf="low",
    note="Sự việc 2011 theo BLLĐ 1994, không có trong corpus. Chỉ còn một vấn đề được tòa xét; hai trong ba ý của câu hỏi (ai có quyền tuyên vô hiệu, điều kiện để tiếp tục sử dụng) không có căn cứ từ bản án. Đề nghị người gán cân nhắc loại câu này.",
    changed="Bỏ điểm b khoản 4 Điều 18, Điều 50 và khoản 1 Điều 10 NĐ 145/2020 cùng hai vấn đề tòa không xét; hạ tin cậy xuống thấp vì luật áp dụng (BLLĐ 1994) không có trong corpus.")

rec("k18", None,
    "Sự việc tháng 8/2020 (facts c20); tòa giám đốc thẩm áp dụng BLLĐ 2012, không có trong corpus v3; case-research ghi quy định tương ứng là Điều 8, 122, 125, 128, 177 BLLĐ 2019. " + PRE2021,
    [("a177_3", "Khoản 7 Điều 192 BLLĐ 2012, tương ứng Điều 177 BLLĐ 2019 (case-research)"),
     ("a128_1", "Khoản 1 Điều 129 BLLĐ 2012, tương ứng Điều 128 BLLĐ 2019 (case-research)"),
     ("a8_2", "Khoản 2 Điều 8 BLLĐ 2012, tương ứng Điều 8 BLLĐ 2019 (case-research)"),
     ("a124_3", "Điều 125 BLLĐ 2012 (hình thức kỷ luật): điều chuyển thực chất là cách chức")],
    outside=["Khoản 7 Điều 192, Điều 123, 125, khoản 1 Điều 129, khoản 2 Điều 8 Bộ luật Lao động 2012 (luật áp dụng)", "Điều 325, 337, 342, 343 Bộ luật Tố tụng dân sự 2015"],
    conf="low",
    note="Ánh xạ: khoản 7 Điều 192 BLLĐ 2012 sang khoản 3 Điều 177 (thỏa thuận bằng văn bản với ban lãnh đạo tổ chức đại diện khi chuyển làm công việc khác, kỷ luật sa thải), khoản 1 Điều 129 sang khoản 1 Điều 128, khoản 2 Điều 8 giữ số. Case-research ghi \"Điều 125\" BLLĐ 2019 là tương ứng, nhưng Điều 125 BLLĐ 2019 là các trường hợp sa thải; hình thức cách chức nằm ở Điều 124, nên giữ khoản 3 Điều 124 như lượt 12/11. Ánh xạ chưa đối chiếu được với chữ BLLĐ 2012 vì văn bản này không có trong corpus.",
    changed="Giữ nguyên đơn vị; hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.")

rec("k19", "2022-01-01",
    "case-research-v1 c21, facts: \"Tháng 01/2022 anh yêu cầu phòng lao động hòa giải\"; phần còn thời hiệu là từ 04/2021 đến hết 2021, khi BLLĐ 2019 và NĐ 145/2020 đã có hiệu lực; ngày không ghi, lấy 01/01/2022.",
    [("a98_1a", "Bản án viện dẫn Điều 98: mức 150% ngày thường"),
     ("a98_1b", "Bản án viện dẫn Điều 98: mức 200% ngày nghỉ hằng tuần"),
     ("a107_2b", "Bản án viện dẫn Điều 107: giới hạn làm thêm theo ngày, tháng"),
     ("a107_2c", "Bản án viện dẫn Điều 107: giới hạn 200 giờ trong 01 năm"),
     ("a107_3a", "Bản án viện dẫn Điều 107: ngành giày được làm thêm đến 300 giờ"),
     ("a190_1", "Bản án viện dẫn khoản 1 Điều 190"),
     ("a190_3", "Bản án viện dẫn khoản 3 Điều 190"),
     ("n55_1a", "Bản án viện dẫn NĐ 145/2020 (không ghi điều); Điều 55 hướng dẫn khoản 1 Điều 98: tiền lương giờ làm căn cứ"),
     ("n55_1b", "Bản án viện dẫn NĐ 145/2020; Điều 55 nhắc lại mức 150%, 200% của khoản 1 Điều 98"),
     ("n60_1", "Nhắc lại giới hạn của điểm b khoản 2 Điều 107 trong NĐ 145/2020 (quy ước 15/11 về quy định nhắc lại)")],
    added={"n60_1": ("Bản án viện dẫn Điều 107 và NĐ 145/2020 (không ghi điều); khoản 1 Điều 60 NĐ 145/2020 nêu cùng giới hạn \"không quá 50% số giờ làm việc bình thường trong 01 ngày\" như điểm b khoản 2 Điều 107 BLLĐ; quy ước 15/11 chọn cả hai đơn vị.", "a107_2b")},
    outside=["Điều 92 Bộ luật Tố tụng dân sự 2015 (chứng cứ)"],
    conf="medium",
    note="Căn cứ bản án: Điều 98, Điều 107, khoản 1, khoản 3 Điều 190 BLLĐ 2019 và NĐ 145/2020 (không ghi điều; ánh xạ sang Điều 55, Điều 60). Điểm a khoản 3 Điều 107 (300 giờ) chỉ áp dụng nếu doanh nghiệp sản xuất, gia công xuất khẩu giày; hồ sơ chỉ ghi công ty sản xuất giày có vốn nước ngoài. Kết quả không ghi tòa kết luận gì về giới hạn làm thêm, dù Điều 107 có trong căn cứ. Điểm a khoản 1 Điều 55 NĐ 145 loại tiền nhà ở khỏi tiền lương giờ làm căn cứ, khớp câu hỏi phụ cấp nhà ở của hồ sơ.",
    changed="Thêm khoản 1 Điều 60 NĐ 145/2020 (nhắc lại điểm b khoản 2 Điều 107) theo quy ước nhắc lại; các đơn vị khác giữ nguyên.")

rec("k20", None,
    "Sự việc tháng 01-05/2020 (facts c23: tạm đình chỉ tháng 01/2020, sa thải tháng 5/2020); tòa áp dụng BLLĐ 2012 và NĐ 148/2018, không có trong corpus v3; case-research ghi quy định tương ứng là Điều 122, 123, 125, 128 BLLĐ 2019 và Điều 70 NĐ 145/2020. " + PRE2021,
    [("a125_2", "Khoản 1 Điều 126 BLLĐ 2012, tương ứng Điều 125 BLLĐ 2019 (case-research)"),
     ("a123_1", "Điều 124 BLLĐ 2012 (thời hiệu), tương ứng Điều 123 BLLĐ 2019 (case-research)"),
     ("a128_2", "Điều 129 BLLĐ 2012 (tạm đình chỉ), tương ứng Điều 128 BLLĐ 2019; tòa buộc trả 50% lương thời gian tạm đình chỉ"),
     ("a128_3", "Điều 129 BLLĐ 2012, tương ứng Điều 128 BLLĐ 2019: bị kỷ luật thì không trả lại tiền đã tạm ứng"),
     ("n70_4", "Khoản 12 Điều 1 NĐ 148/2018, case-research ghi tương ứng Điều 70 NĐ 145/2020"),
     ("a127_3", "Khoản 3 Điều 128 BLLĐ 2012, ánh xạ theo chữ của lượt 12/11: chỉ kỷ luật hành vi có trong nội quy")],
    outside=["Điều 123, 124, khoản 1 Điều 126, khoản 3 Điều 128, Điều 129, khoản 8 Điều 36 Bộ luật Lao động 2012 (luật áp dụng)", "Khoản 12 Điều 1 Nghị định 148/2018/NĐ-CP; khoản 3 Điều 13 Luật Doanh nghiệp 2014 (ủy quyền ký)"],
    conf="low",
    note="Sự việc 2020 theo BLLĐ 2012. Về thẩm quyền: tòa dựa vào ủy quyền theo Luật Doanh nghiệp 2014 và khoản 12 Điều 1 NĐ 148/2018; khoản 4 Điều 70 NĐ 145 chỉ nói người có thẩm quyền ban hành quyết định, còn ai có thẩm quyền được định nghĩa ở điểm i khoản 2 Điều 69 NĐ 145 (dẫn khoản 3 Điều 18 BLLĐ); người gán nên chọn giữa hai đơn vị này. Khoản 3 Điều 127 là ánh xạ theo chữ do lượt 12/11 nêu, không có trong danh sách tương ứng của case-research. Điểm d khoản 4 Điều 123 BLLĐ 2012 (nuôi con dưới 12 tháng) tòa chỉ nêu khi so sánh nên không gán.",
    changed="Giữ nguyên đơn vị; hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.")

rec("k21", None,
    "Tai nạn tháng 02/2016 (facts c24), trước cả ngày Luật ATVSLĐ 2015 có hiệu lực (01/07/2016); tòa áp dụng BLLĐ 2012, NĐ 45/2013, TT 04/2015, không có trong corpus v3; case-research ghi quy định hiện hành tương ứng là Điều 38 Luật ATVSLĐ 2015. " + PRE2021,
    [("s38_4a", "TT 04/2015 (công thức 1,5 tháng lương cộng 0,4 tháng cho mỗi 1%), case-research ghi tương ứng Điều 38 Luật ATVSLĐ 2015; tòa buộc bồi thường 141 triệu đồng theo mức suy giảm 65%")],
    dropped={"s38_3": "Người lao động vẫn được trả đủ lương sau tai nạn; tòa không xét tiền lương khi điều trị.",
             "s38_2c": "Công ty đã hỗ trợ viện phí; tòa không xét chi phí y tế.",
             "s39_4": "Người lao động rút yêu cầu công ty trả thay chế độ bảo hiểm tại phiên tòa; tòa đình chỉ phần này.",
             "a13_2": "Kết quả không ghi nhận định về việc không giao kết hợp đồng; các Điều 15-41 BLLĐ 2012 được dẫn chung."},
    issues_dropped={"Chi phí y tế và tiền lương khi điều trị": "Công ty đã hỗ trợ viện phí và vẫn trả đủ lương; tòa không xét hai khoản này.",
                    "Hậu quả không đóng bảo hiểm tai nạn lao động": "Người lao động đã rút yêu cầu công ty trả thay chế độ bảo hiểm; tòa đình chỉ phần này.",
                    "Không giao kết hợp đồng": "Kết quả bản án không ghi nhận định về hậu quả của việc không giao kết hợp đồng."},
    outside=["Các Điều 15-41 Bộ luật Lao động 2012; khoản 1 Điều 12, khoản 3 Điều 13 Nghị định 45/2013/NĐ-CP; Thông tư 04/2015/TT-BLĐTBXH (luật áp dụng)", "Điều 43 Luật BHXH 2014"],
    conf="low",
    note="Tòa buộc bồi thường 141 triệu đồng theo mức suy giảm 65% theo TT 04/2015; điểm a khoản 4 Điều 38 Luật ATVSLĐ 2015 có cùng công thức. Câu hỏi hỏi trách nhiệm khi không đóng bảo hiểm, nhưng phần này người lao động đã rút nên tòa không xét; nếu giữ câu, câu trả lời chỉ có căn cứ cho mức bồi thường. Đề nghị người gán cân nhắc loại câu.",
    changed="Bỏ khoản 3, điểm c khoản 2 Điều 38, khoản 4 Điều 39 Luật ATVSLĐ và khoản 2 Điều 13 BLLĐ cùng ba vấn đề tòa không xét; hạ tin cậy xuống thấp.")

rec("k22", None,
    "Sự việc năm 2016 (facts c25: gia hạn đến hết nhiệm kỳ lâm thời 25/11/2016) theo BLLĐ 2012; nguồn là Án lệ 70/2023/AL (áp dụng từ 01/11/2023), chính án lệ nêu điều tương ứng của BLLĐ 2019 (notes c25). " + PRE2021,
    [("a177_4", "Điều 192 BLLĐ 2012, án lệ tự nêu tương ứng khoản 4 Điều 177 BLLĐ 2019"),
     ("a34_1", "Điều 36 BLLĐ 2012, án lệ tự nêu tương ứng Điều 34 BLLĐ 2019: chấm dứt khi hết hạn")],
    outside=["Điều 36, Điều 192 Bộ luật Lao động 2012 (luật áp dụng)", "Điều 25 Luật Công đoàn 2012 (tiêu chuẩn ứng cử)"],
    conf="medium",
    note="Giải pháp án lệ: trúng cử không hợp lệ thì không phát sinh nghĩa vụ gia hạn theo khoản 4 Điều 177; chấm dứt khi hết hạn theo khoản 1 Điều 34 là đúng. Tiêu chuẩn ứng cử thuộc Luật Công đoàn, ngoài corpus. Giữ tin cậy vừa (không phải thấp như các vụ trước 2021 khác) vì ánh xạ sang BLLĐ 2019 do chính án lệ nêu.",
    changed="Giữ nguyên đơn vị; hạ tin cậy từ cao xuống vừa vì sự việc theo BLLĐ 2012 (không có trong corpus), dù án lệ tự nêu điều tương ứng của BLLĐ 2019.")

rec("k23", None,
    "Sự việc 9-12/2013 (facts c26) theo BLLĐ 2012; nguồn là Án lệ 20/2018/AL; case-research ghi vấn đề tương ứng Điều 24-27 và điểm a khoản 1 Điều 36 BLLĐ 2019. " + PRE2021,
    [("a27_1", "Điều 29 BLLĐ 2012 (kết thúc thử việc), tương ứng Điều 27 BLLĐ 2019 (case-research)"),
     ("a25", "Điều 27 BLLĐ 2012 (thời gian thử việc), tương ứng Điều 25 BLLĐ 2019 (case-research): không có thỏa thuận kéo dài thử việc"),
     ("a36_1a", "Điểm a khoản 1 Điều 38 BLLĐ 2012, tương ứng điểm a khoản 1 Điều 36 BLLĐ 2019 (case-research)")],
    outside=["Điều 26, 27, 28, 29, điểm a khoản 1 Điều 38 Bộ luật Lao động 2012 (luật áp dụng)", "Khoản 1 Điều 12 Nghị định 44/2003/NĐ-CP"],
    conf="low",
    note="Án lệ áp dụng Điều 26-29, điểm a khoản 1 Điều 38 BLLĐ 2012; ánh xạ do case-research, không do án lệ tự nêu. Điểm a khoản 1 Điều 36 BLLĐ 2019 nay yêu cầu quy chế đánh giá, nên kết luận theo luật hiện hành còn rõ hơn kết luận của án lệ.",
    changed="Giữ nguyên đơn vị; hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.")

rec("k27", "2023-05-03",
    "case-research-v1 c31, facts: \"Sáng 03/5/2023, phó tổng giám đốc thông báo miệng chấm dứt hợp đồng\".",
    [("a41_1", "Bài báo (không nêu điều): phúc thẩm buộc trả lương đến hết hạn hợp đồng, 64 triệu đồng (02 tháng lương) và truy đóng bảo hiểm, tính theo lương hợp đồng 32 triệu đồng"),
     ("a41_1", "Bài báo: 32 triệu đồng tiền vi phạm báo trước", "a41_1_notice"),
     ("a36_2b", "Bài báo: tiền vi phạm báo trước bằng một tháng lương với hợp đồng xác định thời hạn 01 năm")],
    dropped={"a39": "Bài báo không nêu điều luật; công ty thừa nhận chấm dứt trái pháp luật nên tòa không cần xét căn cứ; Điều 39 chỉ là định nghĩa.",
             "a90_1": "Bài báo chỉ nêu tòa tính theo lương hợp đồng 32 triệu đồng; chữ \"tiền lương theo hợp đồng lao động\" đã có trong khoản 1 Điều 41, khoản 1 Điều 90 không phải căn cứ được nêu."},
    issues_dropped={"Xử lý khi người lao động bị tố cáo: kỷ luật theo trình tự": "Công ty thừa nhận chấm dứt trái pháp luật; tòa không xét trình tự kỷ luật."},
    outside=["Bài báo không nêu điều luật cụ thể"],
    conf="medium",
    note="Nguồn báo chí không nêu điều luật; mỗi đơn vị được chọn vì chữ của nó khớp từng khoản tòa buộc trả: lương những ngày không được làm việc, 02 tháng lương, truy đóng bảo hiểm và tiền vi phạm báo trước (khoản 1 Điều 41), thời hạn báo trước 30 ngày với hợp đồng 01 năm (điểm b khoản 2 Điều 36). Mức lương làm căn cứ là \"tiền lương theo hợp đồng lao động\" theo chữ khoản 1 Điều 41.",
    changed="Bỏ Điều 39 và khoản 1 Điều 90 (nguồn không nêu, không cần cho kết luận); bỏ vấn đề trình tự kỷ luật vì tòa không xét.")

rec("k28", None,
    "Sự việc tháng 6/2016 (facts c33) theo BLLĐ 2012, không có trong corpus v3; bài báo nêu điểm a khoản 1, khoản 3 Điều 123 BLLĐ 2012, case-research ghi tương ứng Điều 122, 125 BLLĐ 2019. " + PRE2021,
    [("a122_1a", "Điểm a khoản 1 Điều 123 BLLĐ 2012 (bài báo nêu), tương ứng Điều 122 BLLĐ 2019: chứng minh lỗi"),
     ("a122_3", "Khoản 3 Điều 123 BLLĐ 2012 (bài báo nêu); chữ khớp vấn đề nhiều hành vi trong case-research c33"),
     ("a127_3", "Bài báo: hành vi không thuộc trường hợp sa thải theo nội quy"),
     ("a125_2", "Bài báo: công ty không chứng minh được thiệt hại; nội quy chỉ quy định sa thải khi gây thiệt hại nghiêm trọng"),
     ("a41_1", "Bài báo: buộc nhận lại làm việc, trả lương cho thời gian không được làm việc và đóng bảo hiểm (áp dụng tương tự cho sa thải trái pháp luật)")],
    outside=["Điểm a khoản 1, khoản 3 Điều 123 Bộ luật Lao động 2012 (luật áp dụng)"],
    conf="low",
    note="Bài báo nêu điểm a khoản 1 và khoản 3 Điều 123 BLLĐ 2012 (nay điểm a khoản 1 và khoản 3 Điều 122). Các đơn vị khác chọn vì chữ khớp kết luận bài báo thuật lại: hành vi không thuộc trường hợp sa thải theo nội quy (khoản 3 Điều 127), không chứng minh được thiệt hại (khoản 2 Điều 125), nhận lại làm việc, trả lương và đóng bảo hiểm (khoản 1 Điều 41, áp dụng tương tự cho sa thải trái pháp luật). Sự việc 2016 theo BLLĐ 2012 nên tin cậy thấp.",
    changed="Giữ nguyên đơn vị; hạ tin cậy từ cao xuống thấp vì sự việc 2016 theo BLLĐ 2012, không có trong corpus.")

rec("k29", None,
    "Chấm dứt ngày 01/11/2020 (facts c35: thỏa thuận ngày 30/10/2020), trước khi BLLĐ 2019 (01/01/2021) và NĐ 145/2020 (01/02/2021) có hiệu lực; bài báo ghi tòa viện dẫn BLLĐ 1994 (không nêu điều) và BLDS. " + PRE2021,
    [("a34_3", "Facts: hai bên thỏa thuận chấm dứt; khoản 1 Điều 46 trả trợ cấp cho trường hợp khoản 3 Điều 34"),
     ("a46_1", "Tòa buộc công ty mẹ trả trợ cấp thôi việc còn thiếu (bài báo không nêu điều)"),
     ("a46_2", "Cách tính tòa chấp nhận: 8 năm làm việc trước khi có bảo hiểm thất nghiệp"),
     ("a46_3", "Cách tính tòa chấp nhận: lương bình quân 5 triệu đồng"),
     ("n8_1", "Nhắc lại khoản 1 Điều 46 trong NĐ 145/2020 (quy ước 15/11)"),
     ("n8_3", "Nhắc lại khoản 2 Điều 46 trong NĐ 145/2020 (quy ước 15/11)"),
     ("n8_5a", "Nhắc lại khoản 3 Điều 46 trong NĐ 145/2020 (quy ước 15/11)")],
    added={"n8_1": ("Khoản 1 Điều 8 NĐ 145/2020 nêu cùng quy tắc với khoản 1 Điều 46 BLLĐ (trả trợ cấp thôi việc khi chấm dứt theo các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34 cho người làm thường xuyên từ đủ 12 tháng); quy ước 15/11 chọn cả hai đơn vị.", "a46_1"),
           "n8_3": ("Câu dẫn khoản 3 Điều 8 NĐ 145/2020 nêu cùng quy tắc với khoản 2 Điều 46 BLLĐ (trừ thời gian đã tham gia bảo hiểm thất nghiệp); thay cho điểm a, b khoản 3 là phần định nghĩa chi tiết.", "a46_2")},
    dropped={"n8_3a": "Định nghĩa chi tiết thời gian làm việc thực tế, không nhắc lại quy tắc của khoản 2 Điều 46; quy tắc nằm ở câu dẫn khoản 3 Điều 8 (đã thêm).",
             "n8_3b": "Định nghĩa chi tiết thời gian tham gia bảo hiểm thất nghiệp; thay bằng câu dẫn khoản 3 Điều 8 nhắc lại đúng quy tắc của khoản 2 Điều 46."},
    outside=["Bộ luật Lao động 1994 (bài báo không nêu điều; luật áp dụng)", "Điều 157, khoản 2 Điều 468 Bộ luật Dân sự 2015 (thời hiệu bắt đầu lại, lãi chậm thi hành)", "Công văn 216/SNV-LĐVL của Sở Nội vụ"],
    conf="low",
    note="Bài báo không nêu điều luật lao động cụ thể và chấm dứt xảy ra trước khi BLLĐ 2019 có hiệu lực. Các đơn vị là quy định tương ứng hiện hành, chọn vì chữ khớp cách tính tòa chấp nhận (8 năm làm việc trước khi có bảo hiểm thất nghiệp: khoản 2 Điều 46; lương bình quân: khoản 3 Điều 46). Ai phải trả và thỏa thuận chuyển giao nghĩa vụ tòa giải quyết theo BLDS, ngoài corpus. Đề nghị người gán cân nhắc loại câu này.",
    changed="Thay điểm a, b khoản 3 Điều 8 NĐ 145 bằng câu dẫn khoản 3 Điều 8 và thêm khoản 1 Điều 8 NĐ 145 (nhắc lại khoản 2 và khoản 1 Điều 46); hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.")

rec("k30", "2024-12-30",
    "case-research-v1 c36, facts: \"Ngày 30/12/2024 công ty ra quyết định cho thôi việc từ cùng ngày\".",
    [("a34_3", "Bài báo nêu khoản 3 Điều 34 BLLĐ 2019: không có chứng cứ thỏa thuận chấm dứt"),
     ("a41_1", "Bài báo: lương đến ngày xét xử, 02 tháng lương, 45 ngày báo trước, đóng bảo hiểm"),
     ("a36_2a", "Bài báo: 45 ngày báo trước với hợp đồng không xác định thời hạn"),
     ("a41_3", "Bài báo: thêm 02 tháng lương do không nhận lại")],
    dropped={"a39": "Bài báo chỉ nêu khoản 3 Điều 34; Điều 39 chỉ là định nghĩa, không phải căn cứ được nêu."},
    conf="medium",
    note="Nguồn báo chí nêu khoản 3 Điều 34; các khoản tòa buộc trả khớp chữ của khoản 1 Điều 41 (lương những ngày không được làm việc, 02 tháng lương, tiền vi phạm báo trước, bảo hiểm), khoản 3 Điều 41 (thêm ít nhất 02 tháng lương khi không nhận lại) và điểm a khoản 2 Điều 36 (45 ngày). Giá trị chứng cứ của vi bằng là vấn đề tố tụng.",
    changed="Bỏ Điều 39 (nguồn không nêu, chỉ là định nghĩa).")

rec("k31", "2024-09-01",
    "case-research-v1 c37, facts: \"Ngày 02/8/2024 công ty thông báo chấm dứt hợp đồng từ 01/9/2024\".",
    [("a36_1a", "Bài báo nêu Điều 36; không có quy chế đánh giá mức độ hoàn thành công việc"),
     ("a41_1", "Bài báo: 180 triệu đồng lương đến hết hạn hợp đồng, 48 triệu đồng (02 tháng lương), đóng bảo hiểm"),
     ("a104_1", "Bài báo: phúc thẩm tính theo lương cơ bản vì thưởng không phải khoản đương nhiên được hưởng")],
    dropped={"a39": "Bài báo chỉ nêu Điều 36; Điều 39 chỉ là định nghĩa.",
             "a90_1": "Bài báo không nêu Điều 90 (ghi chú case-research: Điều 90, 104 là gợi ý). Khoản 1 Điều 104 được giữ vì chữ \"căn cứ vào kết quả sản xuất, kinh doanh, mức độ hoàn thành công việc\" khớp lập luận thưởng không đương nhiên được hưởng; khoản 1 Điều 90 không khớp lập luận đó."},
    conf="medium",
    note="Nguồn báo chí chỉ nêu Điều 36; điểm a khoản 1 là trường hợp không hoàn thành công việc theo quy chế, khớp tình tiết. Khoản 1 Điều 41 khớp các khoản tòa buộc trả. Về thưởng, ngoài khoản 1 Điều 104 còn đoạn cuối điểm c khoản 5 Điều 3 TT 10/2020 ghi thưởng theo Điều 104 thành mục riêng, khác các khoản bổ sung của tiền lương; người gán có thể chọn đơn vị đó nếu thấy khớp hơn. Ghi chú case-research c31 viết \"Điều 3 Nghị định 145/2020\" về tiền lương làm căn cứ, nhưng Điều 3 NĐ 145 là sổ quản lý lao động; có lẽ ý là Điều 3 TT 10/2020.",
    changed="Bỏ Điều 39 và khoản 1 Điều 90; giữ khoản 1 Điều 104.")

rec("k32", None,
    "Hợp đồng từ 07/9/2019, công ty cho là chấm dứt từ 12/11/2019 (facts c39); sự việc theo BLLĐ 2012 và Luật BHXH 2014, không có trong corpus v3; bài báo không nêu điều luật. " + PRE2021,
    [("a37_3", "Khoản 3 Điều 39 BLLĐ 2012 (notes c39), tương ứng khoản 3 Điều 37 BLLĐ 2019: không được đơn phương chấm dứt khi nuôi con dưới 12 tháng"),
     ("a137_3", "Điều 155 BLLĐ 2012 (notes c39), tương ứng Điều 137 BLLĐ 2019"),
     ("a41_1", "Bài báo: lương đến hết hạn hợp đồng, 02 tháng lương, đóng bảo hiểm"),
     ("b31_1b", "Bài báo: truy đóng phần chênh lệch bảo hiểm theo mức lương hợp đồng 110 triệu đồng")],
    dropped={"b39_1c": "Tòa buộc truy đóng phần chênh lệch, không phân loại hành vi trốn đóng; việc phân loại không được xét.",
             "b41_1": "Biện pháp xử lý trốn đóng của Luật BHXH 2024 không được tòa áp dụng (sự việc 2019 theo Luật BHXH 2014)."},
    outside=["Khoản 3 Điều 39, Điều 155 Bộ luật Lao động 2012; Luật BHXH 2014 (luật áp dụng)"],
    conf="low",
    note="Nguồn báo chí không nêu điều luật, sự việc 2019 theo luật cũ. Các đơn vị là quy định tương ứng hiện hành theo ghi chú case-research (khoản 3 Điều 37, khoản 3 Điều 137 BLLĐ 2019) và theo chữ khớp kết quả (khoản 1 Điều 41; điểm b khoản 1 Điều 31 Luật BHXH 2024 về tiền lương làm căn cứ đóng). Biên bản thanh lý đã hủy tòa xét như tình tiết, không có điều luật.",
    changed="Bỏ điểm c khoản 1 Điều 39 và khoản 1 Điều 41 Luật BHXH 2024 (tòa không phân loại trốn đóng, không áp biện pháp); hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.")

rec("k33", "2021-12-31",
    "case-research-v1 c40, facts: \"cuối tháng 11/2021 ông nhận thông báo chấm dứt hợp đồng từ 31/12/2021\".",
    [("a42_1a", "Bài báo: công ty không chứng minh được thay đổi cơ cấu, tổ chức lại vị trí quản lý theo luật"),
     ("a41_1", "Bài báo nêu khoản 1 Điều 41; người lao động cam kết hoàn trả trợ cấp mất việc làm khi được nhận lại", "a41_1_return")],
    outside=[],
    conf="medium",
    note="Bài báo nêu khoản 1 Điều 41: nhận lại, trả lương và bảo hiểm những ngày không được làm việc, 02 tháng lương, và đoạn 2 của khoản này về hoàn trả trợ cấp mất việc làm khi được nhận lại. Điểm a khoản 1 Điều 42 chọn vì chữ khớp lý do công ty đưa ra mà tòa kết luận không được chứng minh. Bài báo không cho biết tòa có trừ thời gian người lao động làm việc nơi khác không, nên vấn đề phạm vi lương những ngày không được làm việc chỉ có căn cứ ở chữ của khoản 1 Điều 41.",
    changed="Không đổi đơn vị; thêm ngày áp dụng.")

K34_FINAL = [("a102_1", "Bài báo và luật sư nêu Điều 102"), ("a102_2", "Điều 102: công nhân không được thông báo lý do khấu trừ"),
             ("a102_3", "Điều 102: mức khấu trừ tối đa 30%"), ("a129_2", "Bài báo nêu Điều 129: làm mất tài sản thì bồi thường theo lỗi"),
             ("a130_1", "Bài báo nêu Điều 130: căn cứ vào lỗi, thiệt hại thực tế"), ("a122_1b", "Bài báo nêu điểm b khoản 1 Điều 122"),
             ("a122_1c", "Bài báo nêu điểm c khoản 1 Điều 122"), ("n71_2a", "Bài báo nêu Điều 71 NĐ 145/2020: công nhân không được họp, không được thông báo")]
K34_NOTE = ("Không có phán quyết; căn cứ do bài báo và luật sư nêu (Điều 102, 129, 130, điểm b, c khoản 1 Điều 122 BLLĐ 2019, Điều 71 NĐ 145/2020). Điều 71 NĐ 145 được nêu chung; điểm a khoản 2 (thông báo họp trước ít nhất 05 ngày làm việc) khớp tình tiết không họp, không thông báo. "
            "Tranh chấp tập thể về quyền, con đường khiếu nại theo NĐ 24/2018 ngoài corpus.")
K34_SRC = "case-research-v1 c42, facts: trừ vào lương tháng 4/2024, công nhân \"chỉ phát hiện khi nhận lương ngày 07/5\" (bài báo 09/05/2024)."
rec("k34", "2024-05-07", K34_SRC, K34_FINAL, outside=["Khoản 1 Điều 15, khoản 2 Điều 10 Nghị định 24/2018/NĐ-CP (khiếu nại về lao động)"], conf="medium", note=K34_NOTE,
    changed="Không đổi đơn vị; thêm ngày áp dụng.")
rec("k43", "2024-05-07", K34_SRC, K34_FINAL, outside=["Khoản 1 Điều 15, khoản 2 Điều 10 Nghị định 24/2018/NĐ-CP (khiếu nại về lao động)"], conf="medium",
    note="Diễn đạt lại của k34 (cùng vụ c42), nhãn giống k34. " + K34_NOTE, changed="Không đổi đơn vị; thêm ngày áp dụng.")

rec("k35", "2024-12-30",
    "case-research-v1 c44, court_outcome: phúc thẩm xác định \"hợp đồng chấm dứt từ 30/12/2024 (ngày thông báo giải thể)\".",
    [("a34_7", "Bài báo (không nêu điều): hợp đồng chấm dứt do công ty giải thể, chấm dứt hoạt động"),
     ("a45_2", "Bài báo: phúc thẩm tính thời điểm chấm dứt từ ngày thông báo giải thể"),
     ("a46_1", "Bài báo: phúc thẩm bác trợ cấp thôi việc; khoản 1 Điều 46 có trường hợp khoản 7 Điều 34"),
     ("a46_2", "Bài báo: người lao động đã tham gia bảo hiểm thất nghiệp suốt thời gian làm việc"),
     ("n8_1", "Nhắc lại khoản 1 Điều 46 trong NĐ 145/2020 (quy ước 15/11)"),
     ("n8_3", "Nhắc lại khoản 2 Điều 46 trong NĐ 145/2020 (quy ước 15/11)")],
    added={"n8_1": ("Khoản 1 Điều 8 NĐ 145/2020 nêu cùng quy tắc với khoản 1 Điều 46 BLLĐ (trả trợ cấp thôi việc khi chấm dứt theo các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34); quy ước 15/11 chọn cả hai đơn vị.", "a46_1"),
           "n8_3": ("Câu dẫn khoản 3 Điều 8 NĐ 145/2020 nêu cùng quy tắc với khoản 2 Điều 46 BLLĐ (trừ thời gian đã tham gia bảo hiểm thất nghiệp); thay cho điểm b khoản 3 là phần định nghĩa chi tiết.", "a46_2")},
    dropped={"a48_1": "Tòa không xét thời hạn thanh toán; vấn đề bị bỏ.",
             "a48_1a": "Tòa không xét thời hạn thanh toán; vấn đề bị bỏ.",
             "n8_3b": "Định nghĩa chi tiết thời gian tham gia bảo hiểm thất nghiệp; thay bằng câu dẫn khoản 3 Điều 8 nhắc lại đúng quy tắc của khoản 2 Điều 46."},
    issues_dropped={"Thời hạn thanh toán": "Phúc thẩm chỉ buộc trả lương tháng 12/2024 và thưởng Tết, không xét thời hạn thanh toán."},
    outside=["Bài báo không nêu điều luật cụ thể"],
    conf="medium",
    note="Nguồn báo chí không nêu điều luật; đơn vị chọn vì chữ khớp từng kết luận phúc thẩm: thời điểm chấm dứt tính từ thông báo chấm dứt hoạt động (khoản 2 Điều 45, khoản 7 Điều 34), không có trợ cấp thôi việc vì toàn bộ thời gian đã đóng bảo hiểm thất nghiệp (khoản 1, khoản 2 Điều 46 và khoản 1, khoản 3 Điều 8 NĐ 145). Việc bác tiền vi phạm báo trước không có đơn vị: khoản 2 Điều 36 chỉ áp dụng cho đơn phương chấm dứt theo Điều 36.",
    changed="Bỏ khoản 1 Điều 48 và điểm a khoản 1 Điều 48 cùng vấn đề thời hạn thanh toán (tòa không xét); thay điểm b khoản 3 Điều 8 NĐ 145 bằng câu dẫn khoản 3 và thêm khoản 1 Điều 8 NĐ 145 (nhắc lại Điều 46).")

K36_FINAL = [("a122_4d", "Điều 123 BLLĐ 2012 (bài báo nêu), tương ứng điểm d khoản 4 Điều 122 BLLĐ 2019 (case-research)"),
             ("a137_3", "Điều 155 BLLĐ 2012 (bài báo nêu), tương ứng Điều 137 BLLĐ 2019 (case-research)"),
             ("n70_1", "Điều 30 NĐ 05/2015 (bài báo nêu), tương ứng Điều 70 NĐ 145/2020: tòa hủy quyết định vì không lập biên bản vi phạm"),
             ("n70_2a", "Điều 30 NĐ 05/2015, tương ứng Điều 70 NĐ 145/2020: chỉ gửi email mời họp trước một ngày"),
             ("a41_1", "Bài báo: buộc trả tiền và hai bên đóng bảo hiểm xã hội, y tế (áp dụng tương tự cho sa thải trái pháp luật)")]
K36 = dict(issues_dropped={"Tạm đình chỉ công việc": "Tòa hủy quyết định vì không lập biên bản, vi phạm thông báo họp và kỷ luật lao động nữ mang thai; không xét việc tạm đình chỉ (lượt 12/11 đã bỏ khoản 1 Điều 128 vì lý do này)."},
           outside=["Điều 123, 155 Bộ luật Lao động 2012; Điều 30 Nghị định 05/2015/NĐ-CP (luật áp dụng)"])
K36_NOTE = ("Nguồn báo chí; sự việc 2017 theo BLLĐ 2012 và NĐ 05/2015, không có trong corpus. Ánh xạ theo ghi chú case-research. Khoản 1 Điều 41 khớp một phần kết quả (đóng bảo hiểm; bài báo không nêu nhận lại làm việc hay 02 tháng lương). ")
K36_SRC = "Sự việc tháng 10/2017 (facts c45: họp ngày 12/10/2017, quyết định sa thải ngày 16/10/2017) theo BLLĐ 2012 và NĐ 05/2015, không có trong corpus v3. " + PRE2021
rec("k36", None, K36_SRC, K36_FINAL, conf="low", note=K36_NOTE + "Đề nghị người gán cân nhắc loại câu nếu bộ chỉ giữ câu có luật áp dụng nằm trong corpus.",
    changed="Giữ nguyên đơn vị; bỏ vấn đề tạm đình chỉ (tòa không xét); hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.", **K36)
rec("k42", None, K36_SRC, K36_FINAL, conf="low", note="Diễn đạt lại của k36 (cùng vụ c45), nhãn giống k36. " + K36_NOTE,
    changed="Giữ nguyên đơn vị; bỏ vấn đề tạm đình chỉ (tòa không xét); hạ tin cậy xuống thấp vì luật áp dụng không có trong corpus.", **K36)

rec("k37", "2022-09-01",
    "case-research-v1 c46, facts: \"Ngày 31/8/2022 công ty ra quyết định cho nghỉ từ 01/9/2022 vì không đạt yêu cầu thử việc\".",
    [("a25_1", "Bài báo (không nêu điều): kéo dài thử việc thêm một tháng không vượt giới hạn với vị trí quản lý"),
     ("a27_2", "Bài báo: việc chấm dứt thử việc là hợp pháp, không phải báo trước hay bồi thường")],
    dropped={"a25": "Bài báo không nêu điều luật; tòa kết luận việc kéo dài không vượt giới hạn thời gian với vị trí quản lý (khoản 1 Điều 25), không thuật lại quy tắc chỉ thử việc một lần."},
    issues_dropped={"Lương thử việc": "Mức 85% lương chỉ được tòa dùng làm chứng cứ cho thấy vẫn đang thử việc, không xét tính hợp pháp của mức lương thử việc."},
    outside=["Bài báo không nêu điều luật cụ thể", "Chứng minh việc đã ký hợp đồng thuộc tố tụng"],
    conf="medium",
    note="Nguồn báo chí không nêu điều luật; khoản 1 Điều 25 (180 ngày với người quản lý doanh nghiệp) và khoản 2 Điều 27 (hủy bỏ thử việc không báo trước, không bồi thường) khớp kết luận hai cấp. Mức 180 ngày là lập luận của công ty được bài báo thuật lại; giám đốc kinh doanh có phải người quản lý doanh nghiệp theo Luật Doanh nghiệp hay không chưa chắc (nếu không thì khoản 2 Điều 25: 60 ngày).",
    changed="Bỏ câu dẫn Điều 25 (nguồn không thuật lại quy tắc thử việc một lần) và vấn đề lương thử việc.")


# ---------------------------------------------------------------- build
def build():
    out = []
    for q in QS:
        qid = q["question_id"]
        prev = PREV[qid]
        draft = DRAFTS[q["question"]]
        base = {"question_id": qid, "case_id": q["case_id"], "question_type": prev["question_type"], "expected_status": prev["expected_status"]}
        if qid in EXCLUDED:
            out.append(base | {
                "excluded": True, "relevant_unit_ids": [], "kept": [], "dropped": [], "added": [], "outside_corpus": prev["outside_corpus"],
                "confidence": prev["confidence"],
                "note": "Loại khỏi bộ theo quyết định 15/11/2026 (docs/decisions.md). Lý do từ lượt rà 12/11: " + prev["note"],
                "as_of": None, "as_of_source": "Không xác định: câu bị loại, không rà tiếp.", "checked_at": None,
                "issues": draft["issues"], "issues_dropped": [], "stale_unit_ids": [], "basis": [],
                "changed_from_2026_11_12": "Loại khỏi bộ (một trong 9 câu tin cậy thấp của lượt 12/11, theo quyết định 15/11/2026).",
                "previous_review": prev["relevant_unit_ids"]})
            continue
        r = R[qid]
        final_ids, basis = [], []
        for item in r["final"]:
            key, src = item[0], item[1]
            qkey = item[2] if len(item) > 2 else key
            uid = U[key]
            if uid not in final_ids:
                final_ids.append(uid)
            basis.append({"unit_id": uid, "source_basis": src, "quote": Q[qkey]})
        prev_ids = prev["relevant_unit_ids"]
        kept = [u for u in final_ids if u in prev_ids]
        drop_ids = {U[k]: v for k, v in r["dropped"].items()}
        assert set(drop_ids) == set(prev_ids) - set(final_ids), (qid, set(prev_ids) - set(final_ids), set(drop_ids))
        new_ids = [u for u in final_ids if u not in prev_ids]
        add_map = {U[k]: v for k, v in r["added"].items()}
        added = []
        for uid in new_ids:
            assert uid in add_map, (qid, "missing added reason", uid)
            reason, restated = add_map[uid]
            item = {"unit_id": uid, "reason": reason, "quote": Q[KEY[uid]]}
            if restated:
                item["restates"] = {"unit_id": U[restated], "quote": Q[restated]}
            added.append(item)
        assert set(add_map) == set(new_ids), (qid, set(add_map) - set(new_ids))
        issues = [i for i in draft["issues"] if i not in r["issues_dropped"]]
        assert set(r["issues_dropped"]) <= set(draft["issues"]), (qid, set(r["issues_dropped"]) - set(draft["issues"]))
        stale_ids = [u for u in prev_ids if VALIDITY.status(u, r["as_of"] or LOCK) != "in_force"]
        out.append(base | {
            "excluded": False, "relevant_unit_ids": final_ids, "kept": kept,
            "dropped": [{"unit_id": u, "reason": drop_ids[u]} for u in prev_ids if u in drop_ids],
            "added": added, "outside_corpus": r["outside"], "confidence": r["conf"], "note": r["note"],
            "as_of": r["as_of"], "as_of_source": r["src"], "checked_at": r["as_of"] or LOCK,
            "issues": issues, "issues_dropped": [{"issue": k, "reason": v} for k, v in r["issues_dropped"].items()],
            "stale_unit_ids": stale_ids, "basis": basis,
            "changed_from_2026_11_12": r["changed"], "previous_review": prev_ids})
    for rec_ in out:
        text = json.dumps(rec_, ensure_ascii=False)
        assert "\u2014" not in text, rec_["question_id"]
        for b in rec_["basis"] + rec_["added"]:
            assert b["quote"] in UNITS[b["unit_id"]]["text"], (rec_["question_id"], b["unit_id"], b["quote"][:60])
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    build()
