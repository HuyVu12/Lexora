# unit

Tests hiện chạy từ `tests/test_pipeline.py` và `tests/test_snapshot.py` bằng `python -m unittest discover -s tests -v`. Không gọi mạng; provider và snapshot transport được giả lập.

Các ca parser/schema/evidence/citations/metrics không gọi mạng.

Trạng thái: đã có bộ kiểm thử offline cho phần pilot; chưa có kiểm thử LLM runtime.
