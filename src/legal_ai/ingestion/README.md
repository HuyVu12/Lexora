# ingestion

Lấy văn bản và giữ nguồn gốc; không tự suy đoán hiệu lực.

- `snapshot.py`: tải bản chụp HTML VBPL bất biến kèm checksum (`cli snapshot`, cần duyệt).
- `vbpl_html.py`, `parser.py`: tách đoạn HTML và cấu trúc Chương/Mục/Điều/Khoản/Điểm; `pilot.py` dựng bundle từ cấu hình nguồn (`"article_ids": "all"` lấy cả văn bản).
- `vbpl_api.py`: lấy một văn bản vbpl.vn theo link hoặc mã qua API công khai mà trang dùng, lưu `document.json` bất biến kèm SHA-256 và metadata chính thức; `load_snapshot` đọc lại không gọi mạng.
- `catalog.py`: danh mục tìm kiếm cục bộ (`catalog-v1`, SQLite FTS5, không phân biệt dấu) dựng từ hai bộ dữ liệu mở; dựng cần `pyarrow`, tìm chỉ cần thư viện chuẩn.
- `files.py`: đọc tệp TXT, HTML, DOCX và PDF có lớp chữ (`pypdf`).
- `excerpt.py`: mục lục Điều của văn bản dài và cắt nguyên văn các Điều được chọn kèm tiêu đề Chương/Mục.
- `source_library.py`: thư viện nguồn cục bộ đã kiểm checksum.

Test: `tests/test_sources.py`, `tests/test_excerpt.py`, `tests/test_pipeline.py`, `tests/test_snapshot.py`.
