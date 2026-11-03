# extraction

Baseline rule-based và LLM structured output; lưu output thô, retry và run ID.

Đã có `candidates.py`: phát hiện ứng viên ở mức đơn vị nguồn bằng dấu hiệu từ ngữ; tất cả needs_review, chưa phải trích quy phạm nguyên tử hoặc LLM extraction. Xem `docs/features/knowledge-graph-pilot.md`.

`norms.py` bổ sung grammar có giới hạn để tách thành phần semantic và evidence riêng. Không khớp grammar thì giữ fallback và unparsed report; xem `docs/features/entity-relation-graph.md`.
