# providers

`pilot.py` cung cấp callable provider/cache dùng cho pilot và tests. `router.py` là transport 9Router tùy chọn, exact model/route approval/call budget, timeout và `stream=false`; không retry/fallback tự động.

Python 3.11+, stdlib, không cần install. Xem `docs/features/reviewed-kb-chat.md` để chạy demo và bật provider theo phê duyệt; cấu hình chỉ đọc từ `.env` của Lexora, không in key. Unit tests offline: `python -m unittest discover -s tests -v`. Chưa có live embedding adapter hoặc pipeline nghiên cứu hoàn chỉnh.
