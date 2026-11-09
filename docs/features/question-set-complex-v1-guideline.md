# Hướng dẫn gán nhãn bộ câu hỏi phức tạp v1

Bộ câu hỏi gắn với cùng phiên bản corpus "Phạm vi thực nghiệm v1" (`veaeaad4a6edc`, 5 văn bản, 94 Điều) như bộ v1.
Bộ v1 chủ yếu là câu tra cứu một quy định (101 trên 152 câu có đúng một đơn vị đáp án, chỉ 2 câu cần hai văn bản).
Bộ này bổ sung loại câu mà người làm pháp chế và nhân sự hay gặp: câu cần nhiều quy định cùng lúc.
Kết quả được báo cáo riêng, không gộp vào bộ v1, để thấy hệ thống làm tốt hay kém ở đúng loại câu này.

30 câu do model soạn nháp (nguồn `model`), đều là loại `synthesis`, chia ba nhóm:

| Nhóm | Ý nghĩa | Ví dụ |
|---|---|---|
| `cross_document` | Cần một quy định của Bộ luật Lao động và quy định của Nghị định hoặc Thông tư hướng dẫn chi tiết quy định đó | Trợ cấp thôi việc: Điều 46 Bộ luật và Điều 8 Nghị định 145/2020 |
| `multi_article` | Cần hai hoặc ba Điều khác nhau trong cùng văn bản, ví dụ một quyền và thủ tục hoặc ngoại lệ của nó | Quyền đơn phương chấm dứt và thời hạn báo trước |
| `situation` | Một tình huống có nhiều vấn đề pháp lý, mỗi vấn đề cần một quy định | Sa thải người đang mang thai: căn cứ sa thải, thủ tục, bảo vệ lao động nữ |

## Cách gán nhãn

Các trường và quy tắc giống hướng dẫn bộ v1 (`question-set-v1-guideline.md`), với ba điểm cần chú ý thêm:

- Chọn **đủ** mọi đơn vị cần để trả lời trọn câu hỏi, mỗi đơn vị là điểm hoặc khoản nhỏ nhất chứa căn cứ.
  Thiếu một đơn vị thì kết quả đo sẽ thưởng cho hệ thống trả lời thiếu ý.
- Nếu một vấn đề trong câu không có căn cứ trong 94 Điều, vẫn gán `answer` cho phần có căn cứ và ghi chú phần thiếu.
  Chỉ gán `refuse` khi không vấn đề nào có căn cứ.
- Nếu câu thực chất chỉ cần một quy định (nhóm ghi sai), đổi loại câu thành `lookup` và ghi chú.

## Đo gì trên bộ này

- Recall@K và Recall theo ngân sách token như bộ v1, cộng thêm tỉ lệ câu tìm đủ (`mean_complete`): câu chỉ được tính khi mọi đơn vị đáp án đều nằm trong K kết quả đầu.
- So sánh ĐK3/ĐK4 có và không có mở rộng theo đồ thị dẫn chiếu (chiều dẫn chiếu và chiều được dẫn chiếu, `reference-expansion-v2`).
- Chấm câu trả lời theo cùng phiếu chấm mù như bộ v1; câu trả lời thiếu một vấn đề thì không được điểm đúng tối đa.
