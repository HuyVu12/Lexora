# Runbook demo Lexora

Hướng dẫn dựng lại môi trường demo từ đầu, kịch bản trình diễn khoảng 15 phút và phương án dự phòng.
Mọi bước dựng store đều chạy offline; chỉ các bước có ghi chú "cần mạng" mới gọi vbpl.vn hoặc model.

## 1. Chuẩn bị (một lần trên mỗi máy)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[web,web-test,catalog,embeddings]"
cd frontend; npm install; npm run build; cd ..
```

- Bản chụp văn bản phải có sẵn trong `data/raw/vbpl/` (năm văn bản của `configs/experiment-scope-v1.json`); trên máy mới, chép thư mục này từ máy đã tải hoặc tải lại bằng `cli vbpl-fetch` (cần mạng, cần duyệt).
- Danh mục tìm kiếm `data/catalog/catalog-v1.sqlite` giúp màn Nhập văn bản tìm theo tên; lấy văn bản từ danh mục cần chạy app với `--allow-vbpl` (mỗi văn bản một lượt gọi vbpl.vn, có xác nhận).
- Chuẩn bị sẵn một tệp TXT hoặc DOCX chứa nguyên văn Điều 24-27 Bộ luật Lao động (mỗi Điều bắt đầu bằng "Điều N." trên một dòng) để nhập khi không có mạng.
- Tách quy phạm bằng AI cần Claude Code đã đăng nhập (`claude` trên PATH); không có thì dùng tách theo quy tắc.

## 2. Dựng store demo mới

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli demo-build --store data/kb/demo-<ngày>.sqlite
```

- Lệnh tạo ba tài khoản (`admin` quản trị, `phapche` người duyệt, `nhansu` người tra cứu) với mật khẩu ngẫu nhiên in ra đúng một lần; ghi lại ngay.
- Store có sẵn corpus "Phạm vi thực nghiệm v1" đã khóa phiên bản 1, chưa có kho tri thức nào.
- Lệnh từ chối ghi vào tệp đã tồn tại, nên mỗi lần dựng là một store sạch.

## 3. Chạy app

```powershell
.venv\Scripts\python -m legal_ai.web --store data/kb/demo-<ngày>.sqlite --port 8766
```

Mở http://127.0.0.1:8766.
Cờ tùy chọn (cần mạng, cần duyệt trước): `--allow-vbpl` để lấy văn bản từ vbpl.vn trong app; `--extract-claude-model claude-opus-5-5 --approve-claude --extract-claude-max-calls 30` để tách quy phạm bằng AI.

## 4. Kịch bản trình diễn

1. Đăng nhập `phapche`; ở Tổng quan giới thiệu ba vai trò và khung "Trang này là gì?".
2. Nhập văn bản: nếu đã bật `--allow-vbpl`, tìm "bộ luật lao động" trong danh mục, xác nhận lấy văn bản, mở mục lục và tích Điều 24-27 (thử việc); nếu không, tải lên tệp đã chuẩn bị ở mục 1. Chọn tạo kho mới, tách theo quy tắc (hoặc AI nếu đã bật).
3. Duyệt bản nháp: rê chuột vào "Chủ thể", "Tính quy phạm" để hiện giải thích; duyệt một quy phạm, sửa một ô bằng cách bôi đen cụm từ trong nguyên văn, ghi "không có quy phạm" cho một câu trống; chỉ ra rằng phải quyết định hết mới công bố được.
4. Công bố revision; mở Sơ đồ tri thức của kho để xem Điều, quy phạm và chủ thể.
5. Đăng nhập `nhansu` ở cửa sổ ẩn danh: chỉ thấy kho đã công bố; hỏi "Tiền lương thử việc ít nhất bằng bao nhiêu?" và mở trích dẫn về đúng câu trong luật.
6. Quay lại `phapche`, khu Nghiên cứu: corpus phạm vi thực nghiệm, mở một văn bản và rê chuột vào cảnh báo parser (ví dụ "Trích dẫn sửa đổi").
7. Mở Gold và Bộ câu hỏi để giới thiệu cách hai người gán nhãn độc lập rồi đối soát bằng kappa.
8. Mở Kết quả: bảng so sánh model trích xuất (ĐK3/ĐK4, tỉ lệ bị loại, chèn lỗi), nhấn mạnh model yếu hơn thì kiểm chứng loại nhiều hơn.

Bước 8 chỉ có số liệu khi thư mục `experiments/runs/` của máy demo có các lượt chạy; nếu không, trình chiếu `docs/results/extraction-models.md`.

## 5. Sau buổi diễn tập: sao lưu và khôi phục

- Tắt app (Ctrl+C) rồi chép tệp store: `Copy-Item data/kb/demo-<ngày>.sqlite data/kb/demo-<ngày>.backup.sqlite`.
- Bản sao lưu chứa kho tri thức do chính người duyệt quyết định trong buổi diễn tập, không có nội dung tự duyệt.
- Khôi phục trước giờ demo: chép bản sao lưu ra một tệp mới rồi chạy app với tệp đó; không chạy thẳng trên bản sao lưu.
- Quay video dự phòng toàn bộ kịch bản ở mục 4 sau buổi diễn tập.

## 6. Dự phòng

| Sự cố | Cách xử lý |
|---|---|
| Không có mạng | Bỏ `--allow-vbpl` và tải lên tệp TXT/DOCX đã chuẩn bị ở mục 1 |
| Claude Code hoặc 9Router không trả lời | Tách theo quy tắc; mọi màn khác chạy không cần model |
| Quên mật khẩu | Dựng store mới bằng `demo-build`, hoặc tạo quản trị mới bằng `python -m legal_ai.auth create-admin` |
| App báo 503 | Chưa build giao diện: chạy `npm run build` trong `frontend` |
| Mọi thứ hỏng | Khôi phục từ bản sao lưu (mục 5) hoặc phát video dự phòng |

## 7. Kiểm tra nhanh trước giờ demo

- `.venv\Scripts\python -m unittest discover -s tests` đạt.
- Đăng nhập được cả ba tài khoản; kho đã công bố hiện với `nhansu`.
- Một câu hỏi mẫu trả về trích dẫn mở đúng đoạn nguồn.
- Trình duyệt ở 100% zoom, cửa sổ rộng ít nhất 1280 px.
