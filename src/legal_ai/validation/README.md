# validation

Schema, tham chiếu, evidence, duplicate, temporal/status checks; báo cáo accepted/rejected/needs_review.

Bộ kiểm chứng quy phạm của kho LLM (ĐK3 thành ĐK4): `claims.py` là `kb-validator-v3` (giữ nguyên, vẫn chọn được); `claims_v4.py` là `kb-validator-v4`, cùng các kiểm tra và mã lý do, chỉ khác là giá trị không có trong câu nhưng có nguyên văn ở câu dẫn của đơn vị cha thì được chấp nhận, bằng chứng trỏ về câu dẫn (`evidence.lead_in`, kiểm được bằng `evidence.check_evidence`). Test: `tests/test_kb_validator_v4.py`.

Đã có code pilot local cho một phần trách nhiệm module; xem `docs/planning/local-pilot-review-2026-11-02.md` và `docs/planning/schema-v1-migration.md` để biết phạm vi thực thi. Unit tests: `python -m unittest discover -s tests -v`. Chưa hoàn tất pipeline nghiên cứu hoặc LLM runtime.
