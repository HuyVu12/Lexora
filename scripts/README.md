# scripts

Kiểm thử trên trình duyệt thật (Chrome hoặc Edge headless qua DevTools, không cần npm, báo lỗi nếu console có lỗi):

- `node scripts/check_app_browser.cjs http://127.0.0.1:<port> <thư mục ảnh>`: luồng chính của app (đăng nhập, nhập và duyệt, sơ đồ, hỏi đáp, corpus, bộ câu hỏi, quyền người tra cứu, hướng dẫn); cần store mới có ba tài khoản ghi trong đầu script; không gọi mạng hay model.
- `node scripts/check_graph_viewer.cjs <index.html>` và `node scripts/check_entity_graph_viewer.cjs <index.html>`: kiểm tra DOM của hai trang sơ đồ tự chứa do `cli graph-build` xuất.

Tiện ích:

- `python scripts/build_fixture.py`: tạo lại fixture hợp đồng dữ liệu tổng hợp trong `tests/fixtures/contract-v1/`.
- `python scripts/evaluate_pilot.py data/normalized/pilot-v2 --output <tệp>`: Recall@5 thăm dò trên câu pilot nháp (đã có `run-retrieval` thay thế cho thực nghiệm).
- `scripts/publish-github.ps1`: hỗ trợ đăng lên GitHub; chỉ chạy khi người dùng duyệt.

CLI chính: `$env:PYTHONPATH = 'src'` rồi `python -m legal_ai.cli --help` (snapshot, parse, validate, build-pilot, search, graph-build, catalog-build, catalog-search, vbpl-fetch, corpus-export, run-retrieval).
