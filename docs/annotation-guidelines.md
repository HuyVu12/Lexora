# Hướng dẫn gán nhãn bộ câu hỏi

Phiên bản 1, ngày 07/11/2026.
Áp dụng cho bộ câu hỏi đánh giá ĐK1-ĐK4 gán nhãn trong app (Nghiên cứu > Bộ câu hỏi).
Thay bản nháp v0; bản pilot 02/11 (`docs/planning/pilot-annotation-guideline.md`) giữ làm lịch sử.
Cách dùng app: `docs/features/question-annotation.md`; giao thức thực nghiệm: `docs/evaluation-protocol.md`.

## 1. Nguyên tắc chung

- Gán nhãn dựa trên nguyên văn của phiên bản corpus đã khóa; không dùng kiến thức pháp luật bên ngoài corpus để quyết định.
- Mỗi người gán độc lập trên máy của mình; không xem nhãn của người kia trước khi xong vòng độc lập.
- Ít nhất một người chọn chế độ "Tự gán, không xem đề xuất"; lựa chọn này được ghi vào tệp nhãn.
- Đề xuất của model chỉ là gợi ý: kiểm tra từng trường với nguyên văn trước khi giữ.
- Không chắc thì ghi vào ô Ghi chú, không đoán; ghi chú giúp đối soát nhanh hơn.
- Đây là nhãn nghiên cứu của sinh viên, không phải xác nhận của chuyên gia pháp lý.

## 2. Viết câu hỏi

- Viết như nhân viên pháp chế hoặc nhân sự hỏi trong công việc: ngôn ngữ đời thường, có tình huống khi hợp lý.
- Không chép nguyên cụm từ của điều luật; câu hỏi dùng đúng chữ trong luật quá dễ cho tìm kiếm từ khóa và làm sai lệch kết quả.
- Mỗi câu hỏi một ý chính; câu hỏi gộp nhiều ý thì tách ra.
- Cùng một ý viết theo cách khác thì đưa vào cùng nhóm diễn đạt ("Cùng ý với câu …"); nhóm luôn nằm chung tập dev hoặc held-out.
- Câu do model soạn nháp phải được đọc lại và sửa câu chữ cho tự nhiên trước khi thêm.
- Mục tiêu khoảng 150 câu, phân bố dự kiến: 60 tra cứu, 45 tổng hợp, 25 hiệu lực/sửa đổi, 20 ngoài phạm vi.
  Phân bố cuối chốt sau khi soạn thử, ghi lý do nếu lệch.

## 3. Loại câu hỏi

| Loại | Khi nào chọn | Ví dụ (minh họa) |
|---|---|---|
| Tra cứu (`lookup`) | Trả lời được từ một quy định cụ thể, thường một Khoản hoặc một Điều | "Lương thử việc tối thiểu bằng bao nhiêu phần trăm lương chính thức?" |
| Tổng hợp (`synthesis`) | Phải ghép từ hai quy định trở lên (nhiều Khoản, nhiều Điều hoặc nhiều văn bản) mới đủ | "Nhân viên thử việc nghỉ ngang thì công ty có phải trả lương và báo trước không?" |
| Hiệu lực, sửa đổi (`temporal`) | Hỏi văn bản còn hiệu lực không, áp dụng từ khi nào, đã bị sửa đổi hay thay thế chưa | "Quy định thử việc của Bộ luật Lao động 2012 còn áp dụng không?" |
| Ngoài phạm vi (`out_of_scope`) | Corpus không có căn cứ, hoặc câu hỏi thuộc lĩnh vực khác | "Thủ tục ly hôn thuận tình thế nào?" |

Phân biệt tra cứu và tổng hợp: nếu bỏ đi bất kỳ đơn vị nào trong số đã chọn mà câu trả lời vẫn đủ, đó là tra cứu.

## 4. Hệ thống nên trả lời hay từ chối

- Chọn **Trả lời** khi các đơn vị trong corpus chứa đủ căn cứ nguyên văn để trả lời đúng và đủ điều kiện quan trọng.
- Chọn **Từ chối** khi:
  - corpus không có căn cứ (thường đi với loại Ngoài phạm vi);
  - căn cứ chỉ có một phần, thiếu điều kiện quan trọng làm đổi kết luận;
  - câu hỏi đòi xác minh hiệu lực hoặc tình trạng sửa đổi mà corpus không chứng minh được (Lexora không xác minh hiệu lực pháp luật).
- Câu Hiệu lực, sửa đổi mặc định là Từ chối, trừ khi chính nguyên văn trong corpus nêu rõ điều được hỏi (ví dụ điều khoản thi hành ghi ngày có hiệu lực).

## 5. Chọn đơn vị liên quan

- Chọn **đơn vị nhỏ nhất** chứa căn cứ: Điểm thay vì Khoản, Khoản thay vì Điều; chọn cả Điều chỉ khi Điều không chia Khoản hoặc căn cứ nằm ở câu dẫn của Điều.
- Chọn **đủ**: mọi đơn vị cần cho câu trả lời đầy đủ, kể cả đơn vị chứa điều kiện hoặc ngoại lệ làm đổi kết luận.
- Không chọn đơn vị chỉ "liên quan chủ đề" mà không góp vào câu trả lời.
- Câu dẫn của Điều ("…như sau:") cần cho ý nghĩa của Khoản thì không chọn riêng; hệ thống tự đưa câu dẫn kèm Khoản.
- Câu Trả lời bắt buộc có ít nhất một đơn vị; câu Từ chối được để trống, hoặc chọn đơn vị chứa căn cứ một phần nếu có, kèm ghi chú.
- Dẫn chiếu sang Điều hoặc văn bản ngoài corpus: không tự thêm; ghi chú "dẫn chiếu ngoài corpus".
- Dùng ô "Tìm đơn vị trong corpus" để tìm; đọc nguyên văn trong khung trước khi bấm Chọn.

## 6. Ghi chú

Ghi ngắn vào ô Ghi chú khi:
- phân vân giữa hai loại câu hoặc giữa Trả lời và Từ chối;
- căn cứ nằm ở văn bản chưa có trong corpus;
- nguyên văn có lỗi tách cấu trúc (xem cảnh báo parser của văn bản);
- câu hỏi có thể hiểu theo hai cách.

## 7. Đối soát

- Sau vòng độc lập, hai người trao đổi tệp nhãn và mở trang Đối soát.
- Câu khớp nhau được chốt một lần; câu lệch được hai người thảo luận, đối chiếu nguyên văn, rồi chốt nhãn cuối kèm lý do ở ô Ghi chú.
- Không sửa nhãn độc lập sau khi đã xem nhãn người kia; chỉ chốt nhãn cuối.
- Báo cáo kappa (loại câu, hành vi) và Dice (đơn vị) cùng chế độ xem đề xuất của từng người.
- Câu không chốt được thì bỏ khỏi bộ và ghi lý do, không giữ nhãn mơ hồ.

## 8. Thang chấm câu trả lời (dùng khi chấm ĐK1-ĐK4)

| Điểm | Tiêu chí |
|---|---|
| 0 | Sai nguồn, thêm kết luận không có căn cứ, hoặc mất điều kiện làm đổi ý nghĩa |
| 1 | Đúng một phần nhưng thiếu căn cứ hoặc điều kiện quan trọng |
| 2 | Đúng trong phạm vi corpus, đủ điều kiện quan trọng, trích dẫn thực sự hỗ trợ |

Chấm riêng: trích dẫn có đúng đơn vị không, nội dung có được trích dẫn hỗ trợ không, có đủ ý không, và hành vi từ chối khi thiếu căn cứ.
Lỗi dịch vụ (model không trả lời được) không tính là từ chối đúng.
Người chấm là chính; giám khảo LLM (Sonnet 5.5) chỉ bổ sung và báo cáo riêng.
