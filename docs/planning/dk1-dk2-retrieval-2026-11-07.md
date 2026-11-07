# ĐK1/ĐK2: truy xuất cố định và theo cấu trúc

Ngày: 07/11/2026.
Trạng thái: đã có code và lượt chạy thăm dò; chưa phải kết quả thực nghiệm.

## Đã làm

- Corpus toàn văn `data/normalized/full-v1` dựng từ hai snapshot đã ghim (`configs/sources-full-v1.json`, `"article_ids": "all"`), không gọi mạng.
  Gồm Bộ luật Lao động 45/2019/QH14 và Nghị định 145/2020/NĐ-CP: 2.134 đơn vị, 1.594 đơn vị lá, mọi bằng chứng qua kiểm tra.
- Bản ghi chỉ mục ĐK1/ĐK2 trong `src/legal_ai/indexing/records.py`, giữ vị trí ký tự và mã băm của nguồn.
- Bộ chạy `src/legal_ai/evaluation/retrieval_run.py` và lệnh `python -m legal_ai.cli run-retrieval`.
- BM25 tách thành lớp `BM25` dùng chung; hàm `search` cũ dùng lại lớp này với tham số cũ (k1=1,5, b=0,75), kết quả giống hệt trên 14 câu thử ở cả hai corpus.
- Tham số trong `configs/pilot.json` và `configs/experiments/dk1.json`, `dk2.json`: BM25 k1=1,2, b=0,75; ĐK1 384 token, chồng lấn 64; ĐK2 tối đa 384 token mỗi bản ghi; báo Recall@1, 3, 5, 10.

## Kết quả thăm dò trên 10 câu thí điểm

| | Số bản ghi | Token/bản ghi | Recall@1 | Recall@5 | Token context@5 |
|---|---|---|---|---|---|
| ĐK1 | 287 | 383 | 1,00 | 1,00 | 1.914 |
| ĐK2 | 1.609 | 50 | 1,00 | 1,00 | 377 |

Hai điều kiện đều tìm đúng đơn vị ngay ở vị trí đầu, nhưng ĐK2 cần context ít hơn khoảng 5 lần.
Không được dùng bảng này làm kết luận:

- 10 câu thí điểm là bản nháp, viết từ chính các Điều 24 đến 27 và dùng gần như nguyên chữ của luật, nên câu nào cũng dễ.
- Chưa có câu diễn đạt lại, câu tổng hợp nhiều đơn vị hay câu không dấu.
- Hai câu cần từ chối (P11, P12) bị loại khỏi Recall vì không có đơn vị gold; hành vi từ chối chưa được chấm.

## Việc chặn tiếp theo

1. Bộ câu hỏi: theo `docs/evaluation-protocol.md` cần khoảng 150 câu (tra cứu, tổng hợp, hiệu lực, ngoài phạm vi), chia dev/held-out theo nhóm diễn đạt, khóa mã băm trước khi tinh chỉnh.
   Gold phải do người gán; không tạo gold bằng model rồi tự chấm.
2. Corpus: kế hoạch cần 8-12 văn bản; hiện có 2. Thêm văn bản cần gọi `cli snapshot`, phải được duyệt trước theo `AGENTS.md`.
3. Parser: 73 cảnh báo ở các điều sửa đổi luật khác (Điều 219 Bộ luật Lao động, từ Điều 115 Nghị định 145), do trích dẫn lồng nhau; cần người xem lại trước khi khóa corpus.
4. Tokenizer: "384 token" đang đếm theo âm tiết (`lexora-syllable-v1`); đổi theo tokenizer của model khi chốt model.
