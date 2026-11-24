# Hướng dẫn gán nhãn bộ hiệu lực v1 trên corpus v3 (24/11/2026)

Bộ này gắn với phiên bản corpus v3 đã khóa (`v48feefc6d53b`, 14 văn bản, 7.056 đơn vị).
30 câu hỏi và đề xuất nhãn do model soạn (Claude Opus 5.5, nháp 15/11/2026, dựng lại với `amendment-rules-v2` ngày 16/11).
Đó không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.
Người gán ở chế độ có xem đề xuất giữ hoặc sửa từng trường; người gán độc lập không xem đề xuất.

Mục đích của bộ: đo xem hệ thống có đưa đơn vị đã hết hiệu lực hoặc chưa có hiệu lực vào ngữ cảnh và trích dẫn hay không.

Quy ước:

1. Câu không ghi ngày được hiểu là hỏi tại ngày khóa corpus v3 (11/11/2026); đáp án là đơn vị còn hiệu lực tại ngày đó.
2. Câu ghi rõ ngày (hoặc tháng, năm xảy ra việc) hỏi theo quy định có hiệu lực tại ngày đó, kể cả khi quy định ấy nay đã hết hiệu lực.
3. Chỉ chọn làm đáp án đơn vị có hiệu lực tại ngày áp dụng; không chọn đơn vị đã hết hiệu lực, đã bị sửa bởi quy định có hiệu lực trước ngày áp dụng, hoặc chưa có hiệu lực.
4. Ví dụ: NĐ 283/2026 thay NĐ 12/2022 từ 10/09/2026, nên câu hỏi tại 11/11/2026 chọn đơn vị NĐ 283/2026; câu hỏi về tháng 5/2025 chọn đơn vị NĐ 12/2022.
5. Khi quy định có ở hai văn bản cùng hiệu lực, chọn cả hai đơn vị; chọn đơn vị nhỏ nhất chứa căn cứ và bỏ đơn vị chỉ cùng chủ đề.
6. Câu đối chứng (loại `lookup`) không liên quan tới thay đổi hiệu lực.

Cách chọn loại câu: `temporal` cho câu phụ thuộc ngày hiệu lực, `lookup` cho câu đối chứng; hành vi mong đợi của cả bộ là `answer`.
Phần lý do của mỗi đề xuất ghi ngày áp dụng, đơn vị lỗi thời không được chọn và căn cứ của model.
Bảng kiểm chi tiết từng đơn vị: `experiments/question-drafts-validity-v1/check-sheet.csv`.
Mô tả bộ: `experiments/question-drafts-validity-v1/README.md`.
