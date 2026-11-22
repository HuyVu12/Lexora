# extraction

Đề xuất quy phạm để người duyệt quyết định; mọi kết quả ở trạng thái cần duyệt.

- `candidates.py`: ứng viên mức đơn vị theo dấu hiệu từ ngữ.
- `norms.py` (`norm-rules-v2`): tách thành phần quy phạm (chủ thể, hành vi, đối tượng, điều kiện, ngoại lệ, thời hạn, con số…), mỗi thành phần có bằng chứng riêng; câu có từ tình thái mà chưa tách đủ thành ứng viên `cue-sentence`.
- `llm_norms.py` (`norm-llm-v1`): gửi các câu quy tắc chưa tách được cho model (9Router, hoặc Claude Code với JSON schema), chỉ giữ giá trị tìm thấy đúng nguyên văn trong câu.
- `inherit.py` (`claims-inherit-v1`): bước hậu xử lý tất định cho quy phạm của kho ĐK3; ô chủ thể, hành vi hoặc kết quả đang trống của Điểm/Khoản con được lấy từ câu dẫn của đơn vị cha khi một quy tắc cố định tìm thấy giá trị nguyên văn ở đó (chủ thể trước từ tình thái, cụm động từ sau từ tình thái, "Phạt tiền từ ... đến ..." và bên bị phạt sau "đối với"); mỗi ô kế thừa có bằng chứng riêng theo hợp đồng dữ liệu và ghi nguồn ở `claim["inheritance"]`; trường hợp mơ hồ thì để trống.

Test: `tests/test_norms.py`, `tests/test_ai_extraction.py`, `tests/test_claims_inherit.py`.
