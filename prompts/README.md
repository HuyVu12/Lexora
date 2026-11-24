# prompts

Prompt hệ thống có phiên bản; mỗi lần gọi model ghi tên tệp và SHA-256 của prompt.
Sửa nội dung thì tạo tệp phiên bản mới (`-v2`), không sửa tệp cũ đã dùng cho dữ liệu.

- `question-label-v1.md`: đề xuất loại câu, hành vi mong đợi và đơn vị liên quan cho một câu hỏi, chỉ từ các đơn vị ứng viên (`src/legal_ai/research/proposals.py`).
- `question-draft-v1.md`: soạn nháp câu hỏi từ các đơn vị người duyệt chọn; người duyệt sửa hoặc bỏ trước khi thêm.
- `answer-v1.md`: sinh câu trả lời có trích dẫn từ các đoạn căn cứ E01.. cho ĐK1-ĐK4 (`src/legal_ai/evaluation/answer_run.py`).
- `decompose-v1.md`: tách câu hỏi hoặc tình huống thành tối đa 4 vấn đề pháp lý kèm câu tìm kiếm; chạy một lần, mọi điều kiện ĐK1-ĐK4 dùng chung (`src/legal_ai/evaluation/decompose.py`).
- `answer-v2.md`: như `answer-v1.md`, trả lời theo từng vấn đề đã tách và áp tình tiết vào điều kiện, ngoại lệ của quy định (bộ tình huống).
- `answer-v3.md`: như `answer-v2.md`, thêm `relations` giữa các đoạn (ngoại lệ, chế tài, hướng dẫn...) từ đồ thị `legal-chain-v1` và thứ tự xét quy định gốc, ngoại lệ, hướng dẫn, chế tài (thử nghiệm, `docs/planning/graph-legal-reasoning-2026-11-10.md`).
- `answer-v4.md`: như `answer-v2.md`, đọc được ngữ cảnh gom theo Điều (`source` và `passages`) của `pack-article-v1` P1/P2 (`src/legal_ai/indexing/packing.py`); danh sách phẳng vẫn dùng được.
- `neighbor-select-v1.md`: chọn các láng giềng trên đồ thị `legal-chain-v1` mà câu hỏi cần (ngoại lệ, chế tài, hướng dẫn...), hoặc không chọn gì (`src/legal_ai/evaluation/neighbor_select.py`, thử nghiệm 11/11).
- `neighbor-select-v2.md`: như `neighbor-select-v1.md`, ứng viên theo từng vấn đề đã tách, tối đa 2 đoạn mỗi vấn đề (`--grouping issue`).
- `judge-v1.md`: giám khảo bổ sung chấm câu trả lời theo cùng rubric với người chấm (`src/legal_ai/evaluation/answer_grading.py`).
- `judge-v2.md`: giám khảo bổ sung cho câu hỏi tình huống và xung đột: như `judge-v1.md`, thêm lỗi luật theo phát biểu, điểm theo từng vấn đề pháp lý và độ khớp với kết luận chuẩn (`src/legal_ai/evaluation/outcome_judge.py`).
- `kb-keys-v1.md`: soạn 2-3 câu hỏi bằng lời thường mà mỗi đơn vị có quy phạm trả lời, từ nguyên văn, câu dẫn và các ô quy phạm; chỉ làm khóa tìm kiếm trong chỉ mục `kb-keys-v2`, không phải căn cứ (`src/legal_ai/evaluation/keys_run.py`, `cli kb-keys-gen`).

Trích xuất cho ĐK3/ĐK4 dùng prompt `norm-llm-v1` trong `src/legal_ai/extraction/llm_norms.py` (đã chạy thật với Opus 5.5 ngày 07/11).
