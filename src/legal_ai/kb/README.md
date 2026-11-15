# kb

Kho tri thức có duyệt và đồ thị bằng chứng.

- `import_review.py` `ReviewStore` (`kb-store-v1`): nhiều kho, mỗi kho một chuỗi phiên bản bất biến; bản nháp, quyết định duyệt lưu dần, độ phủ câu, công bố có xem trước, tách bằng AI chạy nền.
- `graph.py`, `references.py`, `viewer.py`: đồ thị JSON/SQLite, dẫn chiếu tường minh, trang sơ đồ tự chứa cho `cli graph-build`; trong app, sơ đồ là trang Cytoscape.

- `amendments.py` (`amendment-rules-v1`, `cli amendment-build`): cạnh sửa đổi, bổ sung, bãi bỏ, thay cụm từ bằng quy tắc từ toàn văn văn bản sửa đổi (bản chụp vbpl.vn đã ghim), mỗi cạnh neo vào nguyên văn câu lệnh; đích ngoài corpus ghi là `external` hoặc `unresolved`, không suy đoán; khi Điều sửa đổi nằm trong corpus (phạm vi v3, `include_amending`), cạnh nối tới đơn vị chứa lời văn mới (`amending_unit_id`) và truy xuất có lọc hiệu lực thay đơn vị cũ bằng đơn vị này; không dùng model.
- `amendment_check.py` (`amendment-check-v1`, `cli amendment-sheet`, `amendment-score`): bảng CSV một dòng mỗi cạnh (kể cả cạnh chưa giải được) để hai người đối chiếu với nguyên văn, đếm kết luận theo trạng thái và loại, đo đồng thuận (tỉ lệ đồng ý thô, Cohen's kappa); bảng của corpus v3 ở `experiments/amendment-check-v3/`.
- `validity.py` (`unit-status-v1`): trạng thái đơn vị tại một ngày (còn hiệu lực, chưa có hiệu lực, hết hiệu lực, bị bãi bỏ, đã sửa đổi, không rõ) từ ngày hiệu lực vbpl.vn báo và cạnh sửa đổi.

Chưa có Neo4j (không định dùng) hay PostgreSQL. Test: `tests/test_import_review.py`, `tests/test_graph.py`, `tests/test_validity.py`, `tests/test_amendment_check.py`.
