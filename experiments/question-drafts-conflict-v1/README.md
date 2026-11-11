# Bộ câu hỏi nháp: quy định đan xen giữa nhiều văn bản (conflict-v1)

Bộ câu hỏi này do mô hình (Claude) soạn ngày 2026-11-10.
Mọi nhãn (`relevant_unit_ids`, `rationale`, `issues`, `reference_outcome`, `conflict_kind`) chỉ là đề xuất chưa được người duyệt, không phải kết luận pháp lý đã kiểm chứng.

## Mục đích

Mỗi câu hỏi chỉ trả lời đúng được khi kết hợp quy định của ít nhất hai văn bản trong corpus mà các quy định đó chồng lấn, chi tiết hóa, sửa đổi, loại trừ hoặc mâu thuẫn nhau.
Bộ này dùng để kiểm tra xem cơ sở tri thức có cấu trúc (DK3/DK4) có giúp ích hơn so với truy hồi đoạn văn (DK1/DK2) khi luật đan xen hay không.

## Phạm vi

Corpus là bundle `data/normalized/experiment-scope-v2-ve5261858b8f3` gồm 9 văn bản: BLLĐ 2019, NĐ 145/2020, TT 10/2020, NĐ 135/2020, NĐ 293/2025, NĐ 12/2022, Luật BHXH 2024, Luật Việc làm 2025 và Luật ATVSLĐ 2015.
Tất cả đơn vị trong `relevant_unit_ids` là đơn vị lá (khoản hoặc điểm) đã được kiểm tra tồn tại trong `units.jsonl`, và mỗi câu có đơn vị từ ít nhất hai văn bản.
Mọi cụm từ trích trong dấu nháy đơn ở `rationale` đã được kiểm tra tự động là có mặt nguyên văn trong đơn vị nhãn hoặc phần dẫn của đơn vị cha.

## Số lượng

Tổng cộng 25 câu, tất cả có `question_type` là `synthesis` và `expected_status` là `answer`.
`law_and_detail`: 5 câu (luật và văn bản chi tiết).
`cross_law`: 5 câu (hai luật cùng điều chỉnh một vấn đề).
`lex_specialis_or_exception`: 5 câu (quy định chung và quy định riêng hoặc ngoại lệ làm đổi kết quả).
`amended_or_superseded`: 5 câu (văn bản sau thay thế văn bản trước, hoặc dẫn chiếu tới điều luật đã hết hiệu lực).
`obligation_and_sanction`: 5 câu (nghĩa vụ trong luật và chế tài trong NĐ 12/2022).

## Cách dùng

Đọc `drafts.json` (danh sách JSON, mỗi phần tử một câu hỏi) và duyệt từng câu trước khi đưa vào bộ câu hỏi chính thức.
Khi duyệt, kiểm tra lại đơn vị nhãn, kết luận trong `reference_outcome` và các giả định trong `notes`, đặc biệt các câu `amended_or_superseded` vì một số kết luận phụ thuộc văn bản ngoài corpus.
Có thể nhập các câu đã duyệt vào bộ câu hỏi qua màn hình nghiên cứu (`/research/questions`) hoặc chuyển thành tệp câu hỏi cho `answer-run`, giữ `issues` và `reference_outcome` làm căn cứ chấm điểm.
Trường `conflict_kind` dùng để báo cáo kết quả theo từng loại đan xen.

## Hạn chế đã biết

Bundle không chứa Điều 139 Luật BHXH 2024 (sửa đổi các luật liên quan) và Điều 219 BLLĐ, nên không có câu nào dựa vào hai điều này.
Corpus không chứa văn bản sửa đổi NĐ 12/2022 (nếu có), văn bản chi tiết Luật BHXH 2024 và Luật Việc làm 2025, Phụ lục địa bàn vùng của NĐ 293/2025 và mức lương cơ sở.
Các câu chỉ dùng phần trong corpus và ghi rõ giới hạn trong `notes`.
