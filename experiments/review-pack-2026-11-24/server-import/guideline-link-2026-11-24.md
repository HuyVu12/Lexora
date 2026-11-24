# Hướng dẫn gán nhãn bộ cần liên kết v1 trên corpus v3 (24/11/2026)

Bộ này gắn với phiên bản corpus v3 đã khóa (`v48feefc6d53b`, 14 văn bản, 7.056 đơn vị).
35 câu hỏi và đề xuất nhãn do một agent Claude soạn ngày 23/11/2026.
Đó không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.
Người gán ở chế độ có xem đề xuất giữ hoặc sửa từng trường; người gán độc lập không xem đề xuất.

Mục đích của bộ: đo xem hệ thống có lấy được cả đơn vị A (nơi tình huống được nêu) lẫn đơn vị B (nơi A dẫn chiếu tới) hay không.

Quy ước:

1. Gán mọi đơn vị cần để trả lời đầy đủ câu hỏi, gồm cả đơn vị liên kết B; một câu mà thiếu B thì chưa trả lời đủ.
2. Đơn vị đáp án gồm A và B; nếu A chỉ dẫn tới B mà B mới nêu quy tắc thì cả hai đều phải có.
3. Chọn đơn vị nhỏ nhất chứa căn cứ; bỏ đơn vị chỉ cùng chủ đề hoặc không cần để trả lời.
4. Câu không ghi ngày được hiểu là hỏi tại ngày khóa corpus v3 (11/11/2026); chỉ chọn đơn vị còn hiệu lực tại ngày đó.
5. Câu sửa đổi, bổ sung (loại d): chọn đơn vị sửa đổi cộng phần còn hiệu lực của đơn vị gốc; cụm từ cũ đã bị thay của đơn vị gốc không được coi là đáp án (ghi chú trong phần lý do).
6. Câu đối chứng chỉ cần một đơn vị lá, không có đơn vị liên kết.

Cách chọn loại câu: `synthesis` cho câu cần nhiều đơn vị, `lookup` cho câu đối chứng; hành vi mong đợi của cả bộ là `answer`.
Phần lý do của mỗi đề xuất nêu loại liên kết, đơn vị B, lưu ý hiệu lực và đáp án tham chiếu của model; người gán đối chiếu đáp án với nguyên văn.
Phiếu kiểm: `experiments/runs/link-set-2026-11-23/check-sheet.csv`.
Mô tả bộ: `experiments/runs/link-set-2026-11-23/README.md`.
