# prompts

Prompt hệ thống có phiên bản; mỗi lần gọi model ghi tên tệp và SHA-256 của prompt.
Sửa nội dung thì tạo tệp phiên bản mới (`-v2`), không sửa tệp cũ đã dùng cho dữ liệu.

- `question-label-v1.md`: đề xuất loại câu, hành vi mong đợi và đơn vị liên quan cho một câu hỏi, chỉ từ các đơn vị ứng viên (`src/legal_ai/research/proposals.py`).
- `question-draft-v1.md`: soạn nháp câu hỏi từ các đơn vị người duyệt chọn; người duyệt sửa hoặc bỏ trước khi thêm.

- `answer-v1.md`: sinh câu trả lời có trích dẫn từ các đoạn căn cứ E01.. cho ĐK1-ĐK4 (`src/legal_ai/evaluation/answer_run.py`).
- `judge-v1.md`: giám khảo bổ sung chấm câu trả lời theo cùng rubric với người chấm (`src/legal_ai/evaluation/answer_grading.py`).

Trích xuất cho ĐK3/ĐK4 dùng prompt `norm-llm-v1` trong `src/legal_ai/extraction/llm_norms.py` (đã chạy thật với Opus 5.5 ngày 07/11).
