# web

Lớp FastAPI phục vụ API và giao diện SvelteKit đã build (`frontend/build`).

- `app.py` `create_app`: tài khoản ba vai trò, phiên HttpOnly SameSite=Strict, token POST theo tiến trình, kiểm tra Host/Origin, giới hạn kích thước (lớn hơn cho tải tệp và gói câu hỏi), CSP, không ghi log request; API kho tri thức, nhập văn bản (kể cả vbpl.vn và tệp), corpus, danh mục, bộ câu hỏi.
- `setup.py`: cờ dòng lệnh dùng chung, tạo provider (9Router, Claude Code), tách bằng AI chạy nền; không phụ thuộc FastAPI.
- `__main__.py`: `python -m legal_ai.web --store <store.sqlite> --port 8766` (thêm `--allow-vbpl`, `--extract-claude-model`, `--proposal-model`, `--approve-claude` khi cần).

Cần `.venv` có phần `web`. Test: `tests/test_web_api.py` (tự bỏ qua khi thiếu FastAPI).
