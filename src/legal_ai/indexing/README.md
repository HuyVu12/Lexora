# indexing

Bản ghi chỉ mục cho từng điều kiện thực nghiệm (`records.py`, `index-record-v1`).

- ĐK1 `fixed_chunks`: cửa sổ cố định `chunk_tokens` token, chồng lấn `overlap_tokens`; cắt trên từng dải đơn vị liền nhau, không vượt chỗ hở hay sang văn bản khác.
- ĐK2 `structural_records`: mỗi đơn vị lá (Điều không có Khoản, Khoản không có Điểm, hoặc Điểm) là một bản ghi, kèm đường dẫn Chương > Điều > Khoản và câu dẫn của Điều/Khoản cha; đơn vị dài hơn `max_tokens` được chia tại cuối câu.
- Mỗi bản ghi giữ `text` đúng bằng `document_text[source_start:source_end]` (vị trí ký tự Unicode), `text_sha256` và các `unit_ids` nó phủ, để Recall@K của mọi điều kiện tính trên cùng đơn vị.
- `index_text` của cả hai điều kiện đều mở đầu bằng tên văn bản; khác biệt duy nhất là cấu trúc. `index_text` chỉ để tìm kiếm, không phải bằng chứng.
- Token đếm theo `lexora-syllable-v1` (âm tiết Unicode và `%`, giống tokenizer BM25); khi chốt model sinh câu trả lời sẽ đổi sang tokenizer của model và tạo phiên bản mới.

ĐK3/ĐK4 (claim do LLM trích) chưa có. Test: `tests/test_retrieval_run.py`.
