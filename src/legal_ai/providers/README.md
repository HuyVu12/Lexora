# providers

Mọi lần gọi model đi qua đây; mỗi provider một model, ngân sách gọi, không thử lại, không tự đổi model.

- `claude_code.py` `ClaudeCodeProvider`: chạy `claude -p` trên máy với đăng nhập Claude của người dùng: prompt hệ thống riêng của Lexora, không công cụ, JSON schema, không lưu phiên, `--safe-mode`, thư mục trống; ghi nhật ký từng lần gọi. Bật bằng `--extract-claude-model` / `--proposal-model` cùng `--approve-claude`.
- `router.py`: 9Router (chat và embedding), cấu hình chỉ đọc từ `.env` của Lexora, chỉ HTTPS hoặc loopback, `stream=false`.
- `pilot.py`: provider có cache cho pilot và test; lớp lỗi chung `ProviderError`.

Test offline: `tests/test_claude_code.py`, `tests/test_pipeline.py`, `tests/test_ai_extraction.py`. Mọi lần gọi thật cần người dùng duyệt model, dữ liệu và phạm vi.
