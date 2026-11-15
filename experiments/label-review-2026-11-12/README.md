# Rà soát nhãn bằng model (12/11/2026)

Đây là nhãn **model rà soát**, không phải nhãn người.
Năm agent Claude (Opus 5.5 qua Claude Code) đối chiếu từng đơn vị trong nhãn nháp của bốn bộ câu hỏi với nguyên văn corpus v2 (`experiment-scope-v2-ve5261858b8f3`), bỏ đơn vị chỉ cùng chủ đề, thêm đơn vị còn thiếu và ghi lý do.
Đề cương yêu cầu nhãn do hai người gán độc lập và đo kappa; bộ này chỉ là tài liệu tham khảo cho hai người gán nhãn và cho việc chạy thử trên tập dev, không được báo cáo như nhãn người.

## Tệp

| Tệp | Nội dung |
|---|---|
| `cases.jsonl`, `conflict.jsonl`, `complex.jsonl`, `lookup-part1.jsonl`, `lookup-part2.jsonl` | Kết quả gốc của từng agent: đơn vị giữ, bỏ, thêm (kèm trích nguyên văn), độ tin cậy, ghi chú |
| `merge.py` | Gộp và kiểm tra; chạy lại được bất cứ lúc nào |
| `<bộ>-reviewed.json` | Bộ câu hỏi đã rà soát, cùng định dạng tệp câu hỏi (`annotation_status: model_review`, khối `model_review` giữ nhãn nháp và lý do) |
| `<bộ>-check-sheet.csv` | Bảng kiểm cho người: mỗi dòng một (câu, đơn vị) với kết luận giữ/bỏ/thêm, lý do, nguyên văn; hai cột trống để người gán nhãn ghi đồng ý hay không |
| `summary.json` | Số liệu tổng |
| `unit.py` | In nguyên văn một đơn vị của corpus v2 |

## Kiểm tra tự động (đều đạt)

- Mỗi câu của bộ gốc được rà đúng một lần.
- Mọi mã đơn vị có trong corpus v2; mọi trích dẫn của đơn vị thêm là chuỗi con chính xác của đơn vị đó.
- Câu "trả lời" có đơn vị, câu "từ chối" không có; loại câu thuộc `QUESTION_TYPES` của app (`validity` đổi thành `temporal`).
- Các câu gần trùng nhau ở bộ phức tạp (cq00/cq08, cq03/cq09, cq10/cq18, cq14/cq19, cq20/cq28, cq21/cq29) cùng nhóm diễn đạt, nên không lọt qua ranh giới dev/held-out.

## Số liệu

| Bộ | Câu | Đơn vị nháp | Đơn vị sau rà soát | Câu giữ nguyên | Đổi trả lời/từ chối | Tin cậy cao / vừa / thấp |
|---|---|---|---|---|---|---|
| Tình huống | 44 | 220 | 251 | 6 | 0 | 4 / 31 / 9 |
| Xung đột | 25 | 121 | 156 | 4 | 0 | 17 / 8 / 0 |
| Phức tạp | 30 | 92 | 119 | 13 | 0 | 16 / 14 / 0 |
| Tra cứu | 152 | 177 | 234 | 116 | 11 | 120 / 31 / 1 |

## Quy ước áp dụng khi gộp

- Một đơn vị bị bỏ khỏi nhãn khi đơn vị con của nó cũng có trong nhãn: đơn vị con là căn cứ chính xác hơn, bản ghi ĐK2 của nó đã mang câu dẫn của đơn vị cha, và cách chấm recall coi đơn vị cha được phủ khi tìm thấy bất kỳ đơn vị con nào.
  Các agent làm khác nhau ở điểm này (có agent thêm câu dẫn của Khoản chứa mức phạt, có agent không), nên quy ước được áp đồng loạt.

## Lỗi hệ thống của nhãn nháp mà các agent tìm thấy

1. Thiếu quy định chỉ có ở corpus v2 (nhãn nháp soạn trên v1): chế tài trong NĐ 12/2022, Luật BHXH, Luật Việc làm; 11 câu tra cứu từng là "từ chối" nay trả lời được.
2. Thiếu đơn vị nối: ví dụ trợ cấp thôi việc (Điều 46) mà không có khoản của Điều 34 làm phát sinh quyền, hoặc thiếu khoản 2 Điều 46 (trừ thời gian đóng bảo hiểm thất nghiệp).
3. Bỏ quy tắc tổ chức bị phạt gấp đôi (khoản 1 Điều 6 NĐ 12/2022), nên câu trả lời theo nhãn nháp sẽ nêu mức phạt bằng một nửa với doanh nghiệp.
4. Ở bộ tình huống: thiếu quy định thủ tục và hậu quả mà bản án viện dẫn, và có đơn vị chỉ cùng chủ đề.

## Quyết định còn để người gán nhãn

1. **Câu hỏi về mức phạt ở thời điểm hiện tại.** NĐ 12/2022 hết hiệu lực từ 10/09/2026 và văn bản thay thế (NĐ 283/2026) không có trong corpus v2. Bộ tra cứu vẫn ghi "trả lời" theo NĐ 12/2022 kèm ghi chú; bộ xung đột bỏ đơn vị NĐ 12/2022 ở x10, x20 vì sự việc xảy ra sau ngày đó. Cần thống nhất: câu không ghi ngày thì coi là "từ chối" trên v2, hay trả lời theo NĐ 12/2022, hay chuyển sang corpus v3 (có NĐ 283/2026).
2. **Quy định trùng giữa Bộ luật Lao động và Nghị định 145.** Nửa đầu bộ tra cứu giữ cả hai đơn vị (ghi "nhắc lại"), nửa sau và bộ phức tạp chỉ giữ một. Giữ cả hai làm recall khó hơn với hệ thống chỉ tìm thấy một; cần chọn một quy ước.
3. **Câu tình huống mà tòa không xét hết các vấn đề câu hỏi nêu** (ví dụ k11-k14, k25): giữ đơn vị trả lời trực tiếp vấn đề đó hay chỉ giữ căn cứ tòa dùng.
4. **9 câu tình huống tin cậy thấp** (k01, k09, k15, k17, k24, k25, k26, k40, k41): tòa chỉ công nhận hòa giải, nguồn là bài báo không nêu Điều, hoặc tòa áp dụng luật cũ; nên xem xét loại khỏi bộ khi khóa.
