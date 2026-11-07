# kb

Kho tri thức có duyệt và đồ thị bằng chứng.

- `import_review.py` `ReviewStore` (`kb-store-v1`): nhiều kho, mỗi kho một chuỗi phiên bản bất biến; bản nháp, quyết định duyệt lưu dần, độ phủ câu, công bố có xem trước, tách bằng AI chạy nền.
- `graph.py`, `references.py`, `viewer.py`: đồ thị JSON/SQLite, dẫn chiếu tường minh, trang sơ đồ tự chứa cho `cli graph-build`; trong app, sơ đồ là trang Cytoscape.

Chưa có Neo4j (không định dùng) hay PostgreSQL. Test: `tests/test_import_review.py`, `tests/test_graph.py`.
