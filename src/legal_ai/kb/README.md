# kb

Kho tri thức có duyệt và đồ thị bằng chứng.

- `import_review.py` `ReviewStore` (`kb-store-v1`): nhiều kho, mỗi kho một chuỗi phiên bản bất biến; bản nháp, quyết định duyệt lưu dần, độ phủ câu, công bố có xem trước, tách bằng AI chạy nền.
- `graph.py`, `references.py`, `viewer.py`: đồ thị JSON/SQLite, dẫn chiếu tường minh, trang sơ đồ tự chứa cho `cli graph-build`; trong app, sơ đồ là trang Cytoscape.

- `amendments.py` (`amendment-rules-v2`, `cli amendment-build`): cạnh sửa đổi, bổ sung, bãi bỏ, thay cụm từ, hết hiệu lực bằng quy tắc từ toàn văn văn bản sửa đổi (bản chụp vbpl.vn đã ghim), mỗi cạnh neo vào nguyên văn câu lệnh; đích ngoài corpus ghi là `external` hoặc `unresolved`, không suy đoán; khi Điều sửa đổi nằm trong corpus (phạm vi v3, `include_amending`), cạnh nối tới đơn vị chứa lời văn mới (`amending_unit_id`) và truy xuất có lọc hiệu lực thay đơn vị cũ bằng đơn vị này; v2 (15/11/2026) giữ nguyên mọi cạnh của v1, thêm phạm vi (`unit`, `own_text` cho lệnh chỉ sửa tên hoặc câu dẫn, `phrase` kèm cụm từ cũ và mới) và các câu "hết hiệu lực" trong Điều hiệu lực (`expire` nêu Điều, khoản; `expire_document` cả văn bản; `expire_subject` theo nội dung, luôn `unresolved`); không dùng model.
- `amendment_check.py` (`amendment-check-v1`, `cli amendment-sheet`, `amendment-score`): bảng CSV một dòng mỗi cạnh (kể cả cạnh chưa giải được) để hai người đối chiếu với nguyên văn, đếm kết luận theo trạng thái và loại, đo đồng thuận (tỉ lệ đồng ý thô, Cohen's kappa); bảng của corpus v3 ở `experiments/amendment-check-v3/`.
- `validity.py` (`unit-status-v2`, `unit-status-v1` vẫn chọn được): trạng thái đơn vị tại một ngày (còn hiệu lực, chưa có hiệu lực, hết hiệu lực, bị bãi bỏ, đã sửa đổi, không rõ) từ ngày hiệu lực vbpl.vn báo và cạnh sửa đổi; v2 xét theo từng đơn vị (thay đổi ở đơn vị con không làm đơn vị cha thành đã sửa đổi, lệnh chỉ sửa câu dẫn không thay các điểm, lệnh thay cụm từ chỉ chạm đơn vị chứa cụm từ). `RecordFilter` là nơi duy nhất quyết định một bản ghi bị loại, kèm ghi chú hay được thay bằng lời văn mới, dùng chung cho bộ lọc xếp hạng và cho đơn vị anh em khi đóng gói P2.

Chưa có Neo4j (không định dùng) hay PostgreSQL. Test: `tests/test_import_review.py`, `tests/test_graph.py`, `tests/test_validity.py`, `tests/test_amendment_check.py`.
