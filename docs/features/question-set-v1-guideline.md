# Hướng dẫn gán nhãn bộ câu hỏi thực nghiệm v1

Bộ câu hỏi gắn với phiên bản corpus "Phạm vi thực nghiệm v1" (`veaeaad4a6edc`, 5 văn bản, 94 Điều).
152 câu do model soạn nháp (nguồn `model`); mỗi câu có một đề xuất nhãn của model.
Đề xuất chỉ để tham khảo: mỗi người tự gán nhãn mọi câu, độc lập với người kia.

## Trước khi bắt đầu

- Chọn chế độ một lần: tự gán (không xem đề xuất) hoặc xem đề xuất.
  Nên có ít nhất một người tự gán, để độ đồng thuận phản ánh đánh giá độc lập.
- Gán nhãn theo toàn bộ corpus, không theo trí nhớ về luật: chỉ coi là có căn cứ khi nguyên văn nằm trong 94 Điều của phiên bản này.

## Nhãn

| Trường | Cách gán |
|---|---|
| Loại câu | `lookup`: một quy định trả lời được. `synthesis`: cần từ hai quy định trở lên, có thể ở hai văn bản. `temporal`: hỏi về hiệu lực, văn bản bị thay thế, quy định chuyển tiếp. `out_of_scope`: corpus không có căn cứ |
| Hành vi mong đợi | `answer` khi nguyên văn trong corpus đủ để trả lời; `refuse` khi không đủ, kể cả câu nghe như trong phạm vi nhưng thiếu con số hoặc quy định cụ thể |
| Đơn vị liên quan | Bắt buộc khi `answer`: chọn đơn vị nhỏ nhất chứa căn cứ (điểm, khoản); chỉ chọn cả Điều khi Điều không chia khoản. Câu `synthesis` chọn đủ các đơn vị cần |
| Ghi chú | Ghi khi câu mơ hồ, ghép hai ý, hoặc đề xuất của model sai rõ |

## Lưu ý

- Câu cùng ý khác cách hỏi thuộc một nhóm diễn đạt; gán nhãn riêng từng câu nhưng thường giống nhau.
- Câu có phần dẫn chiếu tới Điều ngoài phạm vi (ví dụ Điều 62, 119, 138, 169) thì phần đó không có căn cứ.
- Một số công thức trong Nghị định 145/2020 (Điều 56, 57) là hình ảnh nên không có trong văn bản; câu cần công thức đó thì `refuse`.
- Câu hỏi xin tư vấn lựa chọn cá nhân là `out_of_scope`, `refuse`.
- Nếu câu sai hẳn hoặc trùng ý mà không phải diễn đạt lại, ghi chú để loại khi đối soát; không tự sửa câu chữ.
