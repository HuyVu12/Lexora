# retrieval

Truy xuất theo cấu hình; trả scored units/claims cùng source mapping.

- `norm_query.py` (`norm-query-v1`): ĐK3-q/ĐK4-q cho câu hỏi liệt kê: phân tích câu hỏi một lần (`prompts/query-slots-v1.md`), lọc quy phạm theo tính quy phạm, trường bắt buộc, chủ thể (bảng bí danh `configs/experiments/actor-aliases.json`), bản ghi một dòng mỗi quy phạm kèm nguyên văn ô hành vi.

Đã có code pilot local cho một phần trách nhiệm module; xem `docs/planning/local-pilot-review-2026-11-02.md` và `docs/planning/schema-v1-migration.md` để biết phạm vi thực thi. Unit tests: `python -m unittest discover -s tests -v`. Chưa hoàn tất pipeline nghiên cứu hoặc LLM runtime.
