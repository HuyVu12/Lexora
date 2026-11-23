# indexing

Bản ghi chỉ mục cho từng điều kiện thực nghiệm (`records.py`, `index-record-v1`).

- ĐK1 `fixed_chunks`: cửa sổ cố định `chunk_tokens` token, chồng lấn `overlap_tokens`; cắt trên từng dải đơn vị liền nhau, không vượt chỗ hở hay sang văn bản khác.
- ĐK2 `structural_records`: mỗi đơn vị lá (Điều không có Khoản, Khoản không có Điểm, hoặc Điểm) là một bản ghi, kèm đường dẫn Chương > Điều > Khoản và câu dẫn của Điều/Khoản cha; đơn vị dài hơn `max_tokens` được chia tại cuối câu.
- Mỗi bản ghi giữ `text` đúng bằng `document_text[source_start:source_end]` (vị trí ký tự Unicode), `text_sha256` và các `unit_ids` nó phủ, để Recall@K của mọi điều kiện tính trên cùng đơn vị.
- `index_text` của cả hai điều kiện đều mở đầu bằng tên văn bản; khác biệt duy nhất là cấu trúc. `index_text` chỉ để tìm kiếm, không phải bằng chứng.
- Token đếm theo `lexora-syllable-v1` (âm tiết Unicode và `%`, giống tokenizer BM25); khi chốt model sinh câu trả lời sẽ đổi sang tokenizer của model và tạo phiên bản mới.

- ĐK3/ĐK4 `kb_unit_records`: bản ghi ĐK2 kèm quy phạm của đơn vị (`claims_view` full, compact hoặc thin). `thin` chỉ in cho model phần không có nguyên văn trong đơn vị: nhãn tính quy phạm (không in khi `unknown`) và chủ thể kế thừa từ câu dẫn khi chủ thể đó không có trong đơn vị, ghi "Chủ thể (từ câu dẫn)"; quy phạm không thêm gì thì không có dòng, dòng trùng chỉ in một lần.
- `kb_keys.py` (`kb-keys-v1`, bật bằng `"index_keys": {"version": "kb-keys-v1", "aliases": "configs/experiments/actor-aliases.json"}` trong cấu hình điều kiện, mặc định tắt): khóa tìm kiếm tất định chỉ thêm vào `index_text` của bản ghi có quy phạm, không vào phần model đọc, không phải bằng chứng. Mỗi quy phạm: tên chủ thể chuẩn và mọi bí danh theo bảng bí danh, tính quy phạm bằng lời thường (nghĩa vụ -> "nghĩa vụ phải", điều cấm -> "bị cấm không được", quyền và được phép -> "được quyền"), "bị xử phạt" khi ô kết quả có chữ "phạt", và giá trị chủ thể, kết quả kế thừa từ câu dẫn (`claims-inherit-v1`); mỗi khóa một lần trong bản ghi. ĐK4 lấy khóa từ tập quy phạm đã kiểm chứng.
- `kb-keys-v2` (`"index_keys": {"version": "kb-keys-v2", "aliases": ..., "model_keys": "<lượt kb-keys-gen>"}`): khóa của `kb-keys-v1` cộng câu hỏi do model soạn của lượt `kb-keys-gen` (`evaluation/keys_run.py`), cùng quy tắc chỉ vào `index_text`. Bản ghi nhận câu hỏi của đơn vị khi ít nhất một quy phạm của bản ghi nằm trong `claim_ids` đã dùng để soạn, nên ĐK4 bỏ câu hỏi của đơn vị có mọi quy phạm bị loại. Lượt khóa phải cùng bundle và cùng `dk3.jsonl` với kho của điều kiện; manifest của lượt truy xuất ghi SHA-256 của `keys.jsonl` và manifest lượt khóa.
- `packing.py` (`pack-article-v1`): đóng gói ngữ cảnh trong ngân sách token, dùng chung cho lượt sinh câu trả lời và recall theo ngân sách: P0 danh sách phẳng, P1 gom theo Điều và in tiêu đề một lần, P2 thêm Khoản, Điểm anh em chưa xếp hạng của 3 Điều đầu (mỗi khối tối đa 400 token).

Test: `tests/test_retrieval_run.py`, `tests/test_packing.py`, `tests/test_kb_keys.py`, `tests/test_keys_run.py`.
