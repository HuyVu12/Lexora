"""Build experiments/label-review-2026-11-15/conflict.jsonl from the 12/11 records plus the 15/11 changes below."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:/Users/T14S/Desktop/Lexora")
OLD = {json.loads(l)["question_id"]: json.loads(l) for l in (ROOT / "experiments/label-review-2026-11-12/conflict.jsonl").open(encoding="utf-8")}
FREEZE = ("2026-11-11", "no date in question, corpus freeze date")

N12 = "12-2022-nd-cp/"
N283 = "283-2026-nd-cp/"
ORG = "Mức phạt tiền đối với tổ chức bằng 02 lần mức phạt tiền đối với cá nhân."
A7_1 = {"unit_id": N283 + "chapter-i/article-7/clause-1",
        "reason": "Quy tắc thay khoản 1 Điều 6 NĐ 12/2022: mức phạt trong Nghị định là mức đối với cá nhân, tổ chức bị phạt gấp đôi; điều phạt dùng trong câu này không nằm trong danh sách ngoại lệ của khoản này",
        "quote": ORG}
A7_2B = {"unit_id": N283 + "chapter-i/article-7/clause-2/point-b",
         "reason": "Doanh nghiệp thuộc nhóm tổ chức bị phạt gấp 02 lần (câu dẫn khoản 2 Điều 7 NĐ 283)",
         "quote": "Doanh nghiệp được thành lập và hoạt động theo pháp luật Việt Nam"}
A67_2 = {"unit_id": N283 + "chapter-vi/article-67/clause-2",
         "reason": "Quy định chuyển tiếp: hành vi bắt đầu trước 10/09/2026 nhưng vẫn đang diễn ra sau ngày đó thì xử lý theo NĐ 283, nên NĐ 12/2022 không còn là căn cứ phạt",
         "quote": "xảy ra trước thời điểm Nghị định này có hiệu lực nhưng vẫn đang diễn ra khi Nghị định này đã có hiệu lực thì áp dụng quy định của Nghị định này để xử lý"}
P6_1 = {"unit_id": N12 + "chapter-i/article-6/clause-1", "replaced_by": A7_1["unit_id"],
        "old_quote": ORG, "new_quote": ORG,
        "reason": "NĐ 12/2022 hết hiệu lực từ 10/09/2026 (khoản 4 Điều 66 NĐ 283); khoản 1 Điều 7 NĐ 283 giữ nguyên câu về mức phạt tổ chức gấp đôi"}
ART8_1 = "145-2020-nd-cp/chapter-iii/section-2/article-8/clause-1"
Q8_1 = "từ đủ 12 tháng trở lên khi hợp đồng lao động chấm dứt theo quy định tại các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34 của Bộ luật Lao động"


def item(unit_id, reason, quote):
    return {"unit_id": unit_id, "reason": reason, "quote": quote}


def pair(old, new, quote, reason, new_quote=None):
    return {"unit_id": old, "replaced_by": new, "old_quote": quote, "new_quote": new_quote or quote, "reason": reason}


S = {}

S["x00"] = dict(as_of=FREEZE, added=[item("135-2020-nd-cp/article-4/clause-1",
    "Nhắc lại cùng quy tắc lộ trình của khoản 2 Điều 169 BLLĐ (quy ước 15/11: quy định nhắc lại ở hai văn bản thì chọn cả hai); khoản 2 Điều 169 BLLĐ cũng ghi 'tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường là đủ 60 tuổi 03 tháng đối với lao động nam'",
    "tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường là đủ 60 tuổi 03 tháng đối với lao động nam")],
    note_add="Rà lại 15/11 trên corpus v3 tại 11/11/2026: mọi đơn vị còn hiệu lực. Thêm khoản 1 Điều 4 NĐ 135 vì nhắc lại nguyên văn lộ trình của khoản 2 Điều 169 BLLĐ. Khoản 1 Điều 69 Luật BHXH 2024 và khoản 2 Điều 3 NĐ 135 là hai quy định khác nhau về thời điểm hưởng (theo văn bản chấm dứt HĐLĐ, và ngày đầu tiên của tháng liền kề sau thời điểm nghỉ hưu), không phải nhắc lại; cả hai là đơn vị trả lời.",
    changed="Thêm khoản 1 Điều 4 NĐ 135/2020 vì nhắc lại lộ trình tuổi nghỉ hưu của khoản 2 Điều 169 BLLĐ (quy ước nhắc lại ở hai văn bản).")

S["x01"] = dict(as_of=("2026-01-01", "câu hỏi nêu 'Từ tháng 1/2026'; dùng ngày 01/01/2026, mọi ngày sau đó đến ngày khóa corpus cho cùng trạng thái hiệu lực"),
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 01/01/2026. Khoản 2 Điều 90 BLLĐ và khoản 2 Điều 4 NĐ 293 cùng nêu mức lương theo công việc hoặc chức danh 'không được thấp hơn mức lương tối thiểu' (NĐ 293 chi tiết cho lương giờ), là nhắc lại nên giữ cả hai. Corpus v3 không có văn bản mới về lương tối thiểu.",
    changed="Không đổi; chỉ ghi ngày áp dụng 01/01/2026 theo câu hỏi.")

S["x02"] = dict(as_of=("2026-03-01", "câu hỏi nêu nghỉ việc 'vào tháng 3/2026'; dùng ngày đầu tháng, mọi ngày trong tháng 3/2026 cho cùng trạng thái hiệu lực"),
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 03/2026; corpus v3 không có văn bản mới về bảo hiểm thất nghiệp hay lương tối thiểu.",
    changed="Không đổi; chỉ ghi ngày áp dụng tháng 3/2026 theo câu hỏi.")

S["x03"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Khoản 1 Điều 4 TT 10 nhắc lại quyền thỏa thuận của khoản 2 Điều 21 BLLĐ ('Khi người lao động làm việc có liên quan trực tiếp đến bí mật kinh doanh, bí mật công nghệ theo quy định của pháp luật thì người sử dụng lao động có quyền thỏa thuận') và thêm hình thức 'trong hợp đồng lao động hoặc bằng văn bản khác'; cả hai đã có trong nhãn.",
    changed="Không đổi.")

S["x04"] = dict(as_of=("2026-11-11", "câu hỏi chỉ nêu 'trong năm 2026', không nêu ngày sự việc; dùng ngày khóa corpus (nằm trong năm 2026)"),
    added=[item("145-2020-nd-cp/chapter-vii/article-59/clause-1",
        "Nhắc lại yêu cầu người lao động đồng ý của điểm a khoản 2 Điều 107 BLLĐ ('Phải được sự đồng ý của người lao động'); NĐ 145 chi tiết các nội dung phải được đồng ý",
        "người sử dụng lao động phải được sự đồng ý của người lao động tham gia làm thêm"),
        item(N283 + "chapter-ii/section-2/article-24/clause-1/point-b",
        "Văn bản còn hiệu lực tại 11/11/2026 gọi cơ quan nhận thông báo làm thêm từ trên 200 giờ đến 300 giờ là 'Sở Nội vụ', khác tên 'Sở Lao động - Thương binh và Xã hội' ở khoản 1 Điều 62 NĐ 145; cùng nghĩa vụ thông báo, khác tên cơ quan, nên cần đọc cùng để trả lời 'thông báo cho cơ quan nào'",
        "Không thông báo bằng văn bản cho Sở Nội vụ nơi tổ chức làm thêm giờ và nơi đặt trụ sở chính về việc tổ chức làm thêm giờ từ trên 200 giờ đến 300 giờ trong một năm")],
    confidence="medium", supported=True,
    outcome_issue="Kết quả tham chiếu ghi 'cơ quan chuyên môn về lao động cấp tỉnh' (khớp khoản 4 Điều 107 BLLĐ) nhưng chưa nêu tên cơ quan hiện nay. Điểm b khoản 1 Điều 24 NĐ 283/2026 (hiệu lực từ 10/09/2026) ghi 'Không thông báo bằng văn bản cho Sở Nội vụ nơi tổ chức làm thêm giờ và nơi đặt trụ sở chính', trong khi khoản 1 Điều 62 NĐ 145 vẫn ghi 'Sở Lao động - Thương binh và Xã hội'. Corpus không có văn bản sửa khoản 1 Điều 62 NĐ 145; người duyệt cần quyết định có ghi 'Sở Nội vụ' vào đáp án hay không.",
    note_add="Rà lại 15/11: các đơn vị BLLĐ và NĐ 145 còn hiệu lực tại 11/11/2026. Thêm khoản 1 Điều 59 NĐ 145 (nhắc lại yêu cầu đồng ý) và điểm b khoản 1 Điều 24 NĐ 283 (tên cơ quan nhận thông báo hiện nay là Sở Nội vụ). Khoản 2 Điều 60 NĐ 145 chỉ nhắc giới hạn 12 giờ/ngày, không nhắc giới hạn 40 giờ/tháng, nên không thêm. Hạ độ tin cậy vì tên cơ quan trong NĐ 145 và NĐ 283 khác nhau, cần người xem.",
    changed="Thêm khoản 1 Điều 59 NĐ 145 (nhắc lại yêu cầu người lao động đồng ý) và điểm b khoản 1 Điều 24 NĐ 283/2026 (cơ quan nhận thông báo nay được gọi là Sở Nội vụ); hạ độ tin cậy xuống vừa.")

S["x05"] = dict(as_of=FREEZE, added=[
    item(ART8_1, "Nhắc lại câu dẫn trách nhiệm trả trợ cấp thôi việc của khoản 1 Điều 46 BLLĐ: cùng điều kiện 'từ đủ 12 tháng trở lên' và cùng các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34", Q8_1),
    item("145-2020-nd-cp/chapter-iii/section-2/article-8/clause-5/point-a",
         "Nhắc lại khoản 3 Điều 46 BLLĐ về tiền lương tính trợ cấp thôi việc: cùng cụm 'tiền lương bình quân của 06 tháng liền kề theo hợp đồng lao động trước khi người lao động thôi việc'",
         "tiền lương bình quân của 06 tháng liền kề theo hợp đồng lao động trước khi người lao động thôi việc")],
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Thêm hai đơn vị NĐ 145 nhắc lại khoản 1 và khoản 3 Điều 46 BLLĐ. Câu dẫn khoản 3 Điều 8 NĐ 145 nhắc lại khoản 2 Điều 46 BLLĐ nhưng đã có hai điểm con (a, c) trong nhãn nên không cần ghi riêng.",
    changed="Thêm khoản 1 Điều 8 và điểm a khoản 5 Điều 8 NĐ 145/2020 vì nhắc lại khoản 1 và khoản 3 Điều 46 BLLĐ.")

S["x06"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Khoản 1 Điều 53 Luật BHXH 2024 dẫn chiếu thẳng khoản 1 Điều 139 BLLĐ (không chép lại nội dung); cả hai đã có trong nhãn.",
    changed="Không đổi.")

S["x07"] = dict(as_of=("2026-11-11", "câu hỏi chỉ nêu lộ trình 'năm 2026', không nêu ngày chấm dứt; dùng ngày khóa corpus (nằm trong năm 2026)"),
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Khoản 1 Điều 46 BLLĐ và khoản 1 Điều 8 NĐ 145 là nhắc lại (cùng 'từ đủ 12 tháng trở lên', cùng các khoản của Điều 34), cả hai đã có; điểm a khoản 1 Điều 8 NĐ 145 chi tiết ngoại lệ 'đủ điều kiện hưởng lương hưu'.",
    changed="Không đổi.")

S["x08"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: các đơn vị Luật ATVSLĐ dùng ở đây (khoản 3, điểm a khoản 4 Điều 38; Điều 45) không bị Điều 139 Luật BHXH 2024 sửa (các khoản bị sửa là khoản 7 Điều 42, khoản 1 Điều 43, điểm b khoản 2 Điều 44, khoản 3 và 5 Điều 49, khoản 3 Điều 53), nên còn hiệu lực tại 11/11/2026.",
    changed="Không đổi.")

S["x09"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Điểm b khoản 1 Điều 31 Luật BHXH 2024 và điểm b khoản 1 Điều 34 Luật Việc làm 2025 nhắc lại cùng một quy tắc ('phụ cấp lương và các khoản bổ sung khác được thỏa thuận trả thường xuyên, ổn định trong mỗi kỳ trả lương'), cả hai đã có. Không thêm chế tài: câu hỏi chỉ hỏi đúng hay sai; nếu người duyệt muốn nêu mức phạt thì căn cứ hiện hành là điểm a khoản 2 Điều 44 và điểm a khoản 2 Điều 46 NĐ 283/2026 (đăng ký tiền lương đóng BHXH, BHTN thấp hơn quy định).",
    changed="Không đổi.")

Q17_4 = "không trả hoặc trả không đủ cùng lúc với kỳ trả lương một khoản tiền cho người lao động tương đương với mức người sử dụng lao động đóng bảo hiểm xã hội bắt buộc"
Q17_4A = "Từ 3.000.000 đồng đến 5.000.000 đồng đối với vi phạm từ 01 người đến 10 người lao động"
S["x10"] = dict(as_of=FREEZE,
    added=[item(N283 + "chapter-ii/section-2/article-23/clause-4",
        "Thay khoản 4 Điều 17 NĐ 12/2022: câu dẫn mô tả cùng hành vi không trả khoản tiền tương đương mức đóng bảo hiểm cho người không thuộc diện tham gia", Q17_4),
        item(N283 + "chapter-ii/section-2/article-23/clause-4/point-a",
        "Mức phạt khi vi phạm với một người lao động (01 đến 10 người), thay điểm a khoản 4 Điều 17 NĐ 12/2022 với cùng mức", Q17_4A),
        A7_1, A7_2B],
    stale=[pair(N12 + "chapter-ii/article-17/clause-4/point-a", N283 + "chapter-ii/section-2/article-23/clause-4/point-a", Q17_4A,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ nguyên mức phạt cho 01 đến 10 người (12/11 đã bỏ đơn vị này, nay có đơn vị thay thế trong corpus)"),
        pair(N12 + "chapter-ii/article-17/clause-4", N283 + "chapter-ii/section-2/article-23/clause-4", Q17_4,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; câu dẫn khoản 4 Điều 23 NĐ 283 mô tả nguyên văn cùng hành vi")],
    outside_corpus=[], confidence="high",
    outcome_issue="Kết quả tham chiếu ghi 'không trả thì bị phạt theo khoản 4 Điều 17 NĐ 12/2022'. Tại 11/11/2026 NĐ 12/2022 đã hết hiệu lực; căn cứ hiện hành là khoản 4 Điều 23 NĐ 283/2026, cùng hành vi ('không trả hoặc trả không đủ cùng lúc với kỳ trả lương một khoản tiền cho người lao động tương đương với mức người sử dụng lao động đóng bảo hiểm xã hội bắt buộc') và cùng mức 'Từ 3.000.000 đồng đến 5.000.000 đồng đối với vi phạm từ 01 người đến 10 người lao động'; doanh nghiệp bị phạt gấp 02 lần theo khoản 1 Điều 7 NĐ 283. Cần sửa số hiệu điều trong đáp án.",
    note_add="Rà lại 15/11: câu không nêu ngày nên hỏi tại 11/11/2026. Phần chế tài mà 12/11 để ngoài corpus nay có trong NĐ 283/2026 (khoản 4 Điều 23, kèm khoản 1 và điểm b khoản 2 Điều 7 về mức phạt doanh nghiệp gấp đôi). Phần nghĩa vụ không đổi.",
    changed="Thêm chế tài theo NĐ 283/2026 (khoản 4 Điều 23 và điểm a; khoản 1 và điểm b khoản 2 Điều 7) thay khoản 4 Điều 17 NĐ 12/2022 đã hết hiệu lực; bỏ NĐ 283 khỏi danh sách ngoài corpus; nâng độ tin cậy lên cao.")

S["x11"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: các đơn vị Luật ATVSLĐ dùng ở đây (Điều 38, 39, 45) không bị Điều 139 Luật BHXH 2024 sửa, còn hiệu lực tại 11/11/2026.",
    changed="Không đổi.")

S["x12"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Câu dẫn khoản 1 Điều 5 NĐ 135 nhắc lại khoản 3 Điều 169 BLLĐ ('có thể nghỉ hưu ở tuổi thấp hơn nhưng không quá 05 tuổi'), cả hai đã có.",
    changed="Không đổi.")

S["x13"] = dict(as_of=FREEZE, added=[
    item(ART8_1, "Nhắc lại câu dẫn khoản 1 Điều 46 BLLĐ (cùng 'từ đủ 12 tháng trở lên' và cùng các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34, trong đó có khoản 9 là người lao động đơn phương chấm dứt đúng luật)", Q8_1),
    item("145-2020-nd-cp/chapter-iii/section-2/article-8/clause-3",
         "Nhắc lại khoản 2 Điều 46 BLLĐ về thời gian tính trợ cấp thôi việc trừ thời gian đã tham gia bảo hiểm thất nghiệp (cùng cụm từ)",
         "tổng thời gian người lao động đã làm việc thực tế cho người sử dụng lao động trừ đi thời gian người lao động đã tham gia bảo hiểm thất nghiệp")],
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Thêm hai đơn vị NĐ 145 nhắc lại khoản 1 và khoản 2 Điều 46 BLLĐ.",
    changed="Thêm khoản 1 và câu dẫn khoản 3 Điều 8 NĐ 145/2020 vì nhắc lại khoản 1 và khoản 2 Điều 46 BLLĐ.")

S["x14"] = dict(as_of=FREEZE,
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026. Điều 138 BLLĐ (quyền tạm hoãn) và khoản 3 Điều 50 Luật BHXH 2024 (ngưỡng 03 tháng) là hai quy định khác nhau, không phải nhắc lại; cả hai là đơn vị trả lời.",
    changed="Không đổi.")

S["x15"] = dict(as_of=("2026-02-01", "câu hỏi nêu 'Tháng 2/2026 thanh tra lập biên bản'; dùng ngày đầu tháng, mọi ngày trong tháng 2/2026 cho cùng trạng thái hiệu lực"),
    added=[item("74-2025-qh15/chapter-vii/section-2/article-33/clause-5",
        "Câu hỏi hỏi cả bảo hiểm thất nghiệp: Luật Việc làm 2025 (hiệu lực từ 01/01/2026) giao việc xử lý chậm đóng bảo hiểm thất nghiệp cho Luật BHXH, nên mức 0,03%/ngày của khoản 1 Điều 40 Luật BHXH 2024 áp dụng cho cả phần bảo hiểm thất nghiệp",
        "Việc xử lý hành vi chậm đóng, trốn đóng bảo hiểm thất nghiệp được thực hiện theo quy định của Luật Bảo hiểm xã hội.")],
    note_add="Rà lại 15/11: sự việc ở tháng 2/2026, khi NĐ 12/2022 còn hiệu lực (hết hiệu lực 10/09/2026), nên các đơn vị NĐ 12 vẫn là đơn vị trả lời và không lỗi thời tại ngày này; NĐ 283/2026 chưa có hiệu lực nên không đưa vào. Để người duyệt biết: NĐ 283 (điểm b khoản 4 Điều 43) nay tự quy định 'nộp số tiền bằng 0,03%/ngày', tức xung đột với cách tính lãi của NĐ 12 không còn từ 10/09/2026; khoản 2 Điều 67 NĐ 283 cho áp dụng NĐ 283 nếu hành vi chậm đóng còn kéo dài sau 10/09/2026, khoản 1 Điều 67 giữ nghị định có hiệu lực lúc vi phạm cho hành vi đã kết thúc trước ngày đó. Thêm khoản 5 Điều 33 Luật Việc làm 2025.",
    changed="Thêm khoản 5 Điều 33 Luật Việc làm 2025 (chậm đóng bảo hiểm thất nghiệp xử lý theo Luật BHXH); ghi ngày áp dụng 02/2026, nên các đơn vị NĐ 12/2022 vẫn giữ.")

S["x16"] = dict(as_of=("2026-11-11", "câu hỏi hỏi 'Hiện nay', không nêu ngày; dùng ngày khóa corpus"),
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 11/11/2026; corpus v3 không có văn bản sửa khoản 1 Điều 7 NĐ 135.",
    changed="Không đổi.")

Q23_1D = "Không giới thiệu người lao động bị tai nạn lao động, bệnh nghề nghiệp được giám định y khoa, xác định mức độ suy giảm khả năng lao động"
Q23_1 = "Phạt tiền từ 2.000.000 đồng đến 4.000.000 đồng khi vi phạm đối với mỗi người lao động nhưng tối đa không quá 75.000.000 đồng"
Q41_4 = "Phạt tiền từ 2.000.000 đồng đến 4.000.000 đồng khi vi phạm với mỗi người lao động nhưng tối đa không quá 75.000.000 đồng"
S["x17"] = dict(as_of=("2026-11-11", "câu hỏi chỉ nêu 'thanh tra kiểm tra năm 2026', không nêu ngày; dùng ngày khóa corpus (nằm trong năm 2026, sau khi bộ câu hỏi được soạn ngày 10/11/2026); hai trường hợp đang chờ giới thiệu nên hành vi còn tiếp diễn"),
    added=[item(N283 + "chapter-ii/section-3/article-34/clause-1/point-d",
        "Thay điểm d khoản 1 Điều 23 NĐ 12/2022 với nguyên văn cùng hành vi: không giới thiệu người bị tai nạn lao động đi giám định", Q23_1D),
        item(N283 + "chapter-ii/section-3/article-34/clause-1",
        "Câu dẫn chứa mức phạt 2 - 4 triệu đồng mỗi người, giống khoản 1 Điều 23 NĐ 12/2022", Q23_1),
        item(N283 + "chapter-iii/article-48/clause-3/point-đ",
        "Thay điểm c khoản 4 Điều 41 NĐ 12/2022 nhưng dẫn chiếu 'Điều 65 của Luật Bảo hiểm xã hội' thay vì Điều 55 Luật BHXH 2014, tức cùng điều mà khoản 5 Điều 13 Luật BHXH 2024 dẫn chiếu; căn cứ phạt cho trường hợp thứ hai không còn vướng",
        "Không giới thiệu người lao động thuộc đối tượng quy định tại Điều 47 của Luật An toàn, vệ sinh lao động và Điều 65 của Luật Bảo hiểm xã hội đi khám giám định suy giảm khả năng lao động tại Hội đồng Giám định y khoa"),
        item(N283 + "chapter-iii/article-48/clause-3",
        "Câu dẫn chứa mức phạt 2 - 4 triệu đồng mỗi người, giống khoản 4 Điều 41 NĐ 12/2022", Q41_4),
        item("41-2024-qh15/chapter-v/section-3/article-65/clause-1",
        "Điều 65 Luật BHXH 2024 là điều mà cả khoản 5 Điều 13 Luật BHXH 2024 và điểm đ khoản 3 Điều 48 NĐ 283 dẫn chiếu: hưởng lương hưu với mức thấp hơn khi suy giảm khả năng lao động, đúng trường hợp nhân viên thứ hai",
        "được hưởng lương hưu với mức thấp hơn so với người đủ điều kiện hưởng lương hưu"),
        A7_1, A7_2B, A67_2],
    dropped=[{"unit_id": "41-2024-qh15/chapter-xi/article-140/clause-2", "reason": "Chỉ cần khi căn cứ phạt là NĐ 12/2022 (dẫn chiếu Điều 55 Luật BHXH 2014 đã hết hiệu lực); NĐ 283 dẫn chiếu Điều 65 nên câu trả lời tại 11/11/2026 không còn dựa vào việc Luật 2014 hết hiệu lực"},
             {"unit_id": "41-2024-qh15/chapter-xi/article-140/clause-1", "reason": "Chỉ dùng kèm khoản 2 Điều 140 để xác định Luật BHXH 2014 hết hiệu lực từ 01/7/2025; không còn cần khi căn cứ phạt là NĐ 283"}],
    stale=[pair(N12 + "chapter-ii/article-23/clause-1/point-d", N283 + "chapter-ii/section-3/article-34/clause-1/point-d", Q23_1D,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ nguyên hành vi"),
        pair(N12 + "chapter-ii/article-23/clause-1", N283 + "chapter-ii/section-3/article-34/clause-1", Q23_1,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng mức phạt"),
        pair(N12 + "chapter-iii/article-41/clause-4/point-c", N283 + "chapter-iii/article-48/clause-3/point-đ",
        "Không giới thiệu người lao động thuộc đối tượng quy định tại Điều 47 của Luật An toàn, vệ sinh lao động và Điều 55 của Luật Bảo hiểm xã hội",
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ hành vi nhưng đổi dẫn chiếu từ Điều 55 sang Điều 65 Luật BHXH",
        new_quote="Không giới thiệu người lao động thuộc đối tượng quy định tại Điều 47 của Luật An toàn, vệ sinh lao động và Điều 65 của Luật Bảo hiểm xã hội"),
        pair(N12 + "chapter-iii/article-41/clause-4", N283 + "chapter-iii/article-48/clause-3", Q41_4,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng mức phạt"),
        P6_1],
    outside_corpus=["Luật Xử lý vi phạm hành chính (một hành vi chỉ bị xử phạt một lần)"], confidence="low",
    outcome_issue="Kết quả tham chiếu dựa vào NĐ 12/2022 (điểm d khoản 1 Điều 23, điểm c khoản 4 Điều 41) và kết luận căn cứ cho trường hợp thứ hai 'không chắc chắn và cần đối chiếu văn bản xử phạt cập nhật ngoài corpus'. Văn bản đó nay có trong corpus: điểm đ khoản 3 Điều 48 NĐ 283/2026 ghi 'Không giới thiệu người lao động thuộc đối tượng quy định tại Điều 47 của Luật An toàn, vệ sinh lao động và Điều 65 của Luật Bảo hiểm xã hội đi khám giám định suy giảm khả năng lao động', tức dẫn chiếu đúng Điều 65 mà khoản 5 Điều 13 Luật BHXH 2024 dẫn chiếu. Trường hợp thứ nhất chuyển sang điểm d khoản 1 Điều 34 NĐ 283 (cùng hành vi, cùng mức 2 - 4 triệu đồng mỗi người, doanh nghiệp gấp đôi theo khoản 1 Điều 7). Nếu thanh tra kiểm tra từ 10/09/2026, đáp án cần viết lại: cả hai trường hợp đều có căn cứ phạt theo NĐ 283, phần 'còn vướng' chỉ còn việc hai điều khoản (điểm d khoản 1 Điều 34 và điểm đ khoản 3 Điều 48) cùng áp cho người bị tai nạn lao động.",
    note_add="Rà lại 15/11: câu chỉ nêu 'năm 2026', nên áp ngày khóa corpus 11/11/2026; khi đó NĐ 12/2022 đã hết hiệu lực và hành vi (chưa giới thiệu) vẫn tiếp diễn, nên theo khoản 2 Điều 67 NĐ 283 áp dụng NĐ 283. Năm đơn vị NĐ 12 chuyển sang lỗi thời, thay bằng các đơn vị NĐ 283 trích nguyên văn. Độ tin cậy thấp vì (1) 'năm 2026' có thể được người duyệt hiểu là trước 10/09/2026, khi đó nhãn 12/11 (NĐ 12) đúng; (2) kết quả tham chiếu phải viết lại. Corpus v3 không có phần mở đầu của NĐ 283 nên không đọc được số hiệu Luật BHXH mà NĐ 283 gọi là 'Luật Bảo hiểm xã hội'; việc coi đó là Luật 41/2024 dựa vào trùng số Điều 65 với khoản 5 Điều 13 Luật BHXH 2024, người duyệt nên kiểm.",
    changed="Áp ngày 11/11/2026: thay năm đơn vị NĐ 12/2022 bằng điểm d khoản 1 Điều 34, điểm đ khoản 3 Điều 48 (kèm câu dẫn), khoản 1 và điểm b khoản 2 Điều 7, khoản 2 Điều 67 NĐ 283/2026; thêm khoản 1 Điều 65 Luật BHXH 2024; bỏ khoản 1, khoản 2 Điều 140 Luật BHXH 2024 vì NĐ 283 đã dẫn chiếu Điều 65; hạ độ tin cậy xuống thấp và ghi vấn đề của kết quả tham chiếu.")

S["x18"] = dict(as_of=("2026-01-05", "câu hỏi nêu 'đến đầu tháng 1/2026 vẫn chưa có quyết định'; dùng ngày 05/01/2026 (ngày làm việc đầu tiên của năm), mọi ngày đầu tháng 1/2026 cho cùng trạng thái hiệu lực"),
    note_add="Rà lại 15/11: tại đầu tháng 1/2026 Luật Việc làm 2025 đã có hiệu lực và NĐ 12/2022 còn hiệu lực, nên giữ nguyên nhãn; NĐ 283/2026 chưa có hiệu lực ở ngày này nên không đưa vào. Khoản 1 Điều 67 NĐ 283 xác nhận hành vi đã kết thúc trước 10/09/2026 vẫn xử theo nghị định có hiệu lực lúc vi phạm (NĐ 12). Khoản 3 Điều 13 Luật BHXH 2024 nói về phối hợp xác nhận thời gian đóng bảo hiểm xã hội, không phải bảo hiểm thất nghiệp, nên không coi là nhắc lại điểm a khoản 3 Điều 48 BLLĐ.",
    changed="Không đổi; ghi ngày áp dụng đầu tháng 1/2026 theo câu hỏi, khi NĐ 12/2022 còn hiệu lực.")

S["x19"] = dict(as_of=("2026-01-01", "câu hỏi nêu 'Từ 01/01/2026'"),
    note_add="Rà lại 15/11: mọi đơn vị còn hiệu lực tại 01/01/2026; NĐ 74/2024 và Phụ lục NĐ 293 vẫn không có trong corpus v3.",
    changed="Không đổi; ghi ngày áp dụng 01/01/2026 theo câu hỏi.")

Q31_2 = "Phạt tiền từ 10.000.000 đồng đến 15.000.000 đồng đối với người sử dụng lao động có hành vi sử dụng người lao động cao tuổi làm nghề, công việc nặng nhọc, độc hại, nguy hiểm"
S["x20"] = dict(as_of=FREEZE,
    added=[item(N283 + "chapter-ii/section-2/article-29/clause-2",
        "Thay khoản 2 Điều 31 NĐ 12/2022 với nguyên văn cùng hành vi và cùng mức 10 - 15 triệu đồng; câu này cũng nhắc lại điều cấm của khoản 3 Điều 149 BLLĐ ('trừ trường hợp bảo đảm các điều kiện làm việc an toàn')", Q31_2),
        A7_1, A7_2B, A67_2],
    stale=[pair(N12 + "chapter-ii/article-31/clause-2", N283 + "chapter-ii/section-2/article-29/clause-2", Q31_2,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ nguyên hành vi và mức phạt (12/11 đã bỏ đơn vị này, nay có đơn vị thay thế trong corpus)"),
        P6_1],
    outside_corpus=[], confidence="high",
    outcome_issue="Kết quả tham chiếu ghi mức phạt 'gấp đôi khung 10 - 15 triệu của khoản 2 Điều 31 NĐ 12'. Tại 11/11/2026 căn cứ là khoản 2 Điều 29 NĐ 283/2026 ('Phạt tiền từ 10.000.000 đồng đến 15.000.000 đồng đối với người sử dụng lao động có hành vi sử dụng người lao động cao tuổi làm nghề, công việc nặng nhọc, độc hại, nguy hiểm'), doanh nghiệp gấp 02 lần theo khoản 1 Điều 7 NĐ 283 (Điều 29 không nằm trong danh sách ngoại lệ), nên con số 20 - 30 triệu đồng không đổi; chỉ cần sửa số hiệu điều và tên nghị định.",
    note_add="Rà lại 15/11: hành vi 'liên tục 6 năm nay' vẫn đang diễn ra tại 11/11/2026, nên theo khoản 2 Điều 67 NĐ 283 xử theo NĐ 283. Chế tài mà 12/11 để ngoài corpus nay có trong NĐ 283 (khoản 2 Điều 29, khoản 1 và điểm b khoản 2 Điều 7). Phần vi phạm (khoản 3 Điều 149 BLLĐ; điểm c, d khoản 1 Điều 64 Luật ATVSLĐ) không đổi.",
    changed="Thêm chế tài theo NĐ 283/2026 (khoản 2 Điều 29; khoản 1, điểm b khoản 2 Điều 7; khoản 2 Điều 67) thay NĐ 12/2022 đã hết hiệu lực; bỏ NĐ 283 khỏi danh sách ngoài corpus; nâng độ tin cậy lên cao.")

Q28_2A = "Sử dụng người lao động mang thai từ tháng thứ 07 hoặc từ tháng thứ 06 nếu làm việc ở vùng cao, vùng sâu, vùng xa, biên giới, hải đảo làm thêm giờ hoặc làm việc ban đêm hoặc đi công tác xa"
Q28_2I = "đơn phương chấm dứt hợp đồng lao động đối với người lao động vì lý do kết hôn, mang thai, nghỉ thai sản hoặc nuôi con dưới 12 tháng tuổi"
Q28_2 = "Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng đối với người sử dụng lao động có một trong các hành vi sau đây:"
Q28_3C = "Buộc người sử dụng lao động nhận người lao động trở lại làm việc khi có hành vi vi phạm quy định tại điểm i khoản 2 Điều này."
S["x21"] = dict(as_of=FREEZE,
    added=[item(N283 + "chapter-ii/section-2/article-26/clause-2/point-a",
        "Thay điểm a khoản 2 Điều 28 NĐ 12/2022 với nguyên văn cùng hành vi (làm thêm giờ, làm đêm với người mang thai từ tháng thứ 07)", Q28_2A),
        item(N283 + "chapter-ii/section-2/article-26/clause-2/point-i",
        "Thay điểm i khoản 2 Điều 28 NĐ 12/2022: đơn phương chấm dứt hợp đồng vì lý do mang thai", Q28_2I),
        item(N283 + "chapter-ii/section-2/article-26/clause-2",
        "Câu dẫn chứa khung phạt 10 - 20 triệu đồng, giống khoản 2 Điều 28 NĐ 12/2022", Q28_2),
        item(N283 + "chapter-ii/section-2/article-26/clause-3/point-c",
        "Thay điểm c khoản 3 Điều 28 NĐ 12/2022: buộc nhận người lao động trở lại làm việc", Q28_3C),
        A7_1, A7_2B],
    stale=[pair(N12 + "chapter-ii/article-28/clause-2/point-a", N283 + "chapter-ii/section-2/article-26/clause-2/point-a", Q28_2A,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ nguyên hành vi"),
        pair(N12 + "chapter-ii/article-28/clause-2/point-i", N283 + "chapter-ii/section-2/article-26/clause-2/point-i", Q28_2I,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; NĐ 283 giữ hành vi (chỉ thêm chữ 'người lao động' sau 'Sa thải')"),
        pair(N12 + "chapter-ii/article-28/clause-3/point-c", N283 + "chapter-ii/section-2/article-26/clause-3/point-c", Q28_3C,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng biện pháp khắc phục"),
        pair(N12 + "chapter-ii/article-28/clause-2", N283 + "chapter-ii/section-2/article-26/clause-2", Q28_2,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng khung phạt"),
        P6_1],
    outside_corpus=[], confidence="high",
    outcome_issue="Kết quả tham chiếu ghi 'bị buộc nhận chị trở lại làm việc theo điểm c khoản 3 Điều 28 NĐ 12' và khung 10 - 20 triệu đồng theo NĐ 12/2022. Tại 11/11/2026 căn cứ là NĐ 283/2026: điểm a và điểm i khoản 2 Điều 26 (khung 'Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng'), biện pháp khắc phục ở điểm c khoản 3 Điều 26, doanh nghiệp gấp 02 lần theo khoản 1 Điều 7. Con số 20 - 40 triệu đồng mỗi hành vi không đổi; cần sửa số hiệu điều. Đáp án vẫn nên bổ sung khoản 1 Điều 41 BLLĐ như ghi chú 12/11.",
    note_add="Rà lại 15/11: câu không nêu ngày nên hỏi tại 11/11/2026; năm đơn vị NĐ 12/2022 lỗi thời, thay bằng NĐ 283 trích nguyên văn. Độ tin cậy nâng lên vì quy ước 15/11 đã chốt ngày áp dụng.",
    changed="Áp ngày 11/11/2026: thay năm đơn vị NĐ 12/2022 bằng điểm a, điểm i, câu dẫn khoản 2 và điểm c khoản 3 Điều 26, khoản 1 và điểm b khoản 2 Điều 7 NĐ 283/2026; bỏ NĐ 283 khỏi danh sách ngoài corpus; nâng độ tin cậy lên cao.")

Q9_1B = "Từ 5.000.000 đồng đến 10.000.000 đồng đối với vi phạm từ 11 người đến 50 người lao động"
Q9_1 = "giao kết hợp đồng lao động không bằng văn bản với người lao động làm công việc có thời hạn từ đủ 01 tháng trở lên"
Q9_3A = "Buộc người sử dụng lao động giao kết hợp đồng lao động bằng văn bản với người lao động khi có hành vi giao kết hợp đồng lao động không bằng văn bản với người lao động làm công việc có thời hạn từ đủ 01 tháng trở lên"
S["x22"] = dict(as_of=("2026-11-11", "no date in question, corpus freeze date ('dịp Tết' không phải ngày cụ thể)"),
    added=[item(N283 + "chapter-ii/section-2/article-15/clause-1/point-b",
        "Thay điểm b khoản 1 Điều 9 NĐ 12/2022 với cùng mức cho 11 đến 50 người lao động (20 người)", Q9_1B),
        item(N283 + "chapter-ii/section-2/article-15/clause-1",
        "Câu dẫn mô tả hành vi giao kết không bằng văn bản với công việc từ đủ 01 tháng, giống khoản 1 Điều 9 NĐ 12/2022", Q9_1),
        item(N283 + "chapter-ii/section-2/article-15/clause-3/point-a",
        "Thay điểm a khoản 3 Điều 9 NĐ 12/2022: buộc giao kết hợp đồng bằng văn bản", Q9_3A),
        A7_1, A7_2B],
    stale=[pair(N12 + "chapter-ii/article-9/clause-1/point-b", N283 + "chapter-ii/section-2/article-15/clause-1/point-b", Q9_1B,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng mức"),
        pair(N12 + "chapter-ii/article-9/clause-3/point-a", N283 + "chapter-ii/section-2/article-15/clause-3/point-a", Q9_3A,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng biện pháp khắc phục"),
        pair(N12 + "chapter-ii/article-9/clause-1", N283 + "chapter-ii/section-2/article-15/clause-1", Q9_1,
        "NĐ 12/2022 hết hiệu lực từ 10/09/2026; cùng hành vi"),
        P6_1],
    confidence="medium",
    note_add="Rà lại 15/11: 'dịp Tết' không phải ngày cụ thể nên theo quy ước 15/11 câu được hỏi tại 11/11/2026; bốn đơn vị NĐ 12/2022 lỗi thời, thay bằng NĐ 283 trích nguyên văn. Nếu người duyệt hiểu là Tết tháng 2/2026 (NĐ 12 còn hiệu lực) thì dùng lại bốn đơn vị NĐ 12 của nhãn 12/11; mức phạt và biện pháp khắc phục giống hệt nhau nên kết quả tham chiếu (không nêu số hiệu điều) đúng theo cả hai cách. Giữ độ tin cậy vừa vì cách hiểu ngày.",
    changed="Áp ngày 11/11/2026: thay bốn đơn vị NĐ 12/2022 bằng câu dẫn và điểm b khoản 1, điểm a khoản 3 Điều 15, khoản 1 và điểm b khoản 2 Điều 7 NĐ 283/2026 (cùng mức phạt).")

S["x23"] = dict(as_of=("2026-06-15", "câu hỏi nêu 'đến giữa tháng 6/2026'"),
    note_add="Rà lại 15/11: tại 15/06/2026 NĐ 12/2022 còn hiệu lực, nên giữ các đơn vị NĐ 12; NĐ 283/2026 chưa có hiệu lực ở ngày này. Để người duyệt biết: từ 10/09/2026 NĐ 283 tách riêng hành vi 'không đăng ký hoặc đăng ký không đầy đủ số người phải tham gia' (khoản 2 Điều 43) với mức theo số người; nếu hành vi còn kéo dài sau ngày đó thì khoản 2 Điều 67 NĐ 283 cho áp NĐ 283.",
    changed="Không đổi; ghi ngày áp dụng giữa tháng 6/2026 theo câu hỏi, khi NĐ 12/2022 còn hiệu lực.")

S["x24"] = dict(as_of=("2026-05-11", "câu hỏi nêu hợp đồng hết hạn ngày 01/4/2026 và 'đã 40 ngày', tức ngày 11/05/2026"),
    added=[item(ART8_1, "Nhắc lại câu dẫn khoản 1 Điều 46 BLLĐ (cùng 'từ đủ 12 tháng trở lên' và cùng các khoản của Điều 34, trong đó khoản 1 là hết hạn hợp đồng)", Q8_1)],
    note_add="Rà lại 15/11: tại 11/05/2026 NĐ 12/2022 còn hiệu lực nên giữ các đơn vị NĐ 12; NĐ 283/2026 chưa có hiệu lực ở ngày này. Thêm khoản 1 Điều 8 NĐ 145 vì nhắc lại khoản 1 Điều 46 BLLĐ.",
    changed="Thêm khoản 1 Điều 8 NĐ 145/2020 vì nhắc lại khoản 1 Điều 46 BLLĐ; ghi ngày áp dụng 11/05/2026, khi NĐ 12/2022 còn hiệu lực.")

out = []
for qid, old in OLD.items():
    s = S[qid]
    as_of, as_of_source = s["as_of"]
    added, dropped, stale = s.get("added", []), s.get("dropped", []), s.get("stale", [])
    stale_ids = [p["unit_id"] for p in stale]
    removed = set(stale_ids) | {d["unit_id"] for d in dropped}
    base = old["relevant_unit_ids"]
    rel = list(dict.fromkeys([u for u in base if u not in removed] + [a["unit_id"] for a in added]))
    out.append({
        "question_id": qid, "question_type": old["question_type"], "expected_status": old["expected_status"],
        "relevant_unit_ids": rel,
        "kept": [u for u in base if u not in removed],
        "dropped": dropped, "added": added,
        "stale_unit_ids": stale_ids, "stale_pairs": stale,
        "outside_corpus": s.get("outside_corpus", old.get("outside_corpus", [])),
        "reference_outcome_supported": s.get("supported", False if s.get("outcome_issue") else old.get("reference_outcome_supported", True)),
        "confidence": s.get("confidence", old["confidence"]),
        "as_of": as_of, "as_of_source": as_of_source,
        "outcome_issue": s.get("outcome_issue"),
        "changed_from_2026_11_12": s["changed"],
        "note": s["note_add"] + " Ghi chú 12/11: " + old.get("note", ""),
        "previous_review": {"date": "2026-11-12", "relevant_unit_ids": base, "confidence": old["confidence"]},
    })
dest = ROOT / "experiments/label-review-2026-11-15"
dest.mkdir(exist_ok=True)
with (dest / "conflict.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
    for record in out:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
print(len(out), "records")
