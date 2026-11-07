# prompts

Prompt hệ thống có phiên bản; mỗi lần gọi model ghi tên tệp và SHA-256 của prompt.
Sửa nội dung thì tạo tệp phiên bản mới (`-v2`), không sửa tệp cũ đã dùng cho dữ liệu.

- `question-label-v1.md`: đề xuất loại câu, hành vi mong đợi và đơn vị liên quan cho một câu hỏi, chỉ từ các đơn vị ứng viên (`src/legal_ai/research/proposals.py`).
- `question-draft-v1.md`: soạn nháp câu hỏi từ các đơn vị người duyệt chọn; người duyệt sửa hoặc bỏ trước khi thêm.

Dự kiến thêm: extraction (ĐK3/ĐK4), answer, judge.
