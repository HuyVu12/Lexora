# extraction

Đề xuất quy phạm để người duyệt quyết định; mọi kết quả ở trạng thái cần duyệt.

- `candidates.py`: ứng viên mức đơn vị theo dấu hiệu từ ngữ.
- `norms.py` (`norm-rules-v2`): tách thành phần quy phạm (chủ thể, hành vi, đối tượng, điều kiện, ngoại lệ, thời hạn, con số…), mỗi thành phần có bằng chứng riêng; câu có từ tình thái mà chưa tách đủ thành ứng viên `cue-sentence`.
- `llm_norms.py` (`norm-llm-v1`): gửi các câu quy tắc chưa tách được cho model (9Router, hoặc Claude Code với JSON schema), chỉ giữ giá trị tìm thấy đúng nguyên văn trong câu.

Test: `tests/test_norms.py`, `tests/test_ai_extraction.py`.
