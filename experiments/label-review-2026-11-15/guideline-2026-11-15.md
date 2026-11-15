# Hướng dẫn gán nhãn bộ khó trên corpus v3 (quy ước 15/11/2026)

Bộ câu hỏi này gắn với phiên bản corpus v3 đã khóa (`v48feefc6d53b`, 14 văn bản, 7.056 đơn vị).
Mỗi câu có sẵn một đề xuất của model (rà soát ngày 15/11/2026); đó không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.
Người gán giữ hoặc sửa từng trường; app ghi lại trường nào giữ, trường nào sửa.

Quy ước (docs/decisions.md, các dòng ngày 15/11/2026):

1. Câu không ghi ngày được hiểu là hỏi tại ngày khóa corpus v3 (11/11/2026); đáp án là đơn vị còn hiệu lực tại ngày đó.
   Ví dụ: NĐ 283/2026 thay NĐ 12/2022 từ 10/09/2026, nên đơn vị NĐ 12/2022 là lỗi thời và đơn vị NĐ 283/2026 cùng nội dung vào đáp án.
2. Câu có ngày (hoặc câu tình huống có ngày xảy ra việc) theo quy định có hiệu lực tại ngày đó.
3. Quy định được nhắc lại ở hai văn bản (thường là Bộ luật Lao động và NĐ 145/2020) thì chọn cả hai đơn vị, khi văn bản thứ hai nêu cùng quy tắc.
4. Chọn đơn vị nhỏ nhất chứa căn cứ; bỏ đơn vị chỉ cùng chủ đề; giữ quy định nối cần cho câu trả lời đúng.
5. Bộ tình huống chỉ gồm đơn vị mà bản án dựa vào; vấn đề tòa không xét đã bị bỏ khỏi danh sách vấn đề của câu.

Lý do của từng đề xuất nằm trong ô lý do của câu.
Bảng kiểm chi tiết theo từng đơn vị (giữ, thêm, bỏ, lỗi thời, kèm nguyên văn): `experiments/label-review-2026-11-15/<bộ>-check-sheet.csv`.
Hướng dẫn riêng của từng bộ: `docs/features/question-set-cases-v1-guideline.md`, `docs/features/question-set-complex-v1-guideline.md`, `experiments/question-drafts-conflict-v1/README.md`.
