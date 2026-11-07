# Chạy ứng dụng local

Workspace nhiều kho tri thức: nhập văn bản (tìm trong danh mục hoặc dán link vbpl.vn rồi chọn các Điều, tải tệp TXT/HTML/DOCX/PDF có lớp chữ, dán nội dung, hoặc thư viện nguồn) → duyệt quy phạm trên nguyên văn (duyệt, loại, sửa bằng câu trích, duyệt cả Điều) → xem trước rồi tạo kho mới hoặc gộp vào kho có sẵn → hỏi đáp trên một hoặc nhiều kho → xem sơ đồ tri thức của kho.
Lớp web ở `src/legal_ai/web/` (FastAPI), giao diện ở `frontend/` (SvelteKit, xuất tĩnh).
Giao diện cũ (`src/legal_ai/demo.py`, `demo-app.js`) đã được gỡ ngày 07/11/2026.

Khu vực Nghiên cứu (corpus, bộ câu hỏi) dành cho người duyệt; xem `docs/features/question-annotation.md`.

Cần Python 3.11+, virtualenv `.venv` có extra `web` (thêm `catalog` nếu tự dựng danh mục) và Node để build frontend.
Từ workspace root:

```powershell
python -m venv .venv; .venv\Scripts\python -m pip install -e ".[web,web-test]"   # một lần
cd frontend; npm install; npm run build; cd ..
.venv\Scripts\python -m legal_ai.auth create-admin --store data/kb/app-new.sqlite --username admin
.venv\Scripts\python -m legal_ai.web --store data/kb/app-new.sqlite --port 8766
```

Mở `http://127.0.0.1:8766`, đăng nhập, dừng đúng terminal bằng Ctrl+C.
Tài khoản người duyệt và người tra cứu do quản trị tạo trong trang quản lý tài khoản.
Store mới không có kho nào; kho được tạo khi công bố bản nháp đầu tiên.
Thêm `--seed data/kb/entity-relation-review/graph.json` để khởi tạo "Kho mặc định" từ graph seed (chỉ áp dụng cho store mới).
Store cũ một chuỗi revision được tự chuyển thành "Kho mặc định" khi mở; revision cũ không bị sửa.
Không cần mạng cho chế độ trích nguyên văn.

Kiểm thử giao diện trên browser thật (Chrome hoặc Edge headless, không cần npm), dùng store mới có ba tài khoản ghi trong đầu script:

```powershell
node scripts/check_app_browser.cjs http://127.0.0.1:8790 data/interim/app-check
```

Script chạy toàn bộ luồng bằng dữ liệu minh họa, chụp màn hình từng bước và báo lỗi nếu console có lỗi.

Câu không có quy phạm nào được gạch chân chấm trên màn hình duyệt; mỗi câu phải được thêm quy phạm hoặc đánh dấu "Không phải quy phạm" trước khi công bố.

## Danh mục và vbpl.vn

- Danh mục tìm kiếm (171.547 văn bản) được nhận tự động khi có `data/catalog/catalog-v1.sqlite`; dựng bằng `python -m legal_ai.cli catalog-build --output data/catalog/catalog-v1.sqlite` từ các tệp trong `data/catalog/raw/` (cần phần `catalog`).
- `--allow-vbpl` cho phép lấy văn bản từ vbpl.vn, mỗi lần một văn bản và luôn hỏi xác nhận; bản chụp lưu ở `data/raw/vbpl/` (đổi bằng `--vbpl-dir`).
- Ở màn Nhập văn bản, sau khi lấy văn bản, tích các Điều cần nhập (tối đa 60 mỗi lần); Điều có trích dẫn lồng nhau bị khóa kèm lý do.

## Tùy chọn AI qua Claude Code

Gọi `claude -p` trên máy với đăng nhập Claude của người chạy; dùng hạn mức gói Claude và mỗi đợt gọi đều hỏi xác nhận.

```powershell
.venv\Scripts\python -m legal_ai.web --store data/kb/app.sqlite --port 8766 --allow-vbpl `
  --extract-claude-model claude-opus-5-5 --extract-claude-max-calls 30 `
  --proposal-model claude-opus-5-5 --proposal-max-calls 20 --approve-claude
```

- `--extract-claude-model`: lựa chọn "Bằng AI" ở bước nhập dùng Opus qua Claude Code (chỉ kho công khai; không dùng chung với `--extract-model` của 9Router); `--extract-claude-effort` (mặc định `medium`), `--extract-claude-max-calls` (mặc định 40).
- `--proposal-model`: đề xuất nhãn và soạn nháp câu hỏi trong bộ câu hỏi; `--proposal-effort`, `--proposal-max-calls`.

## Tùy chọn AI qua 9Router

Mặc định ứng dụng không gọi mạng.
Chỉ bật khi người dùng đã duyệt endpoint, model, dữ liệu và phạm vi theo `AGENTS.md`.
Endpoint và key đọc từ `9ROUTER_URL`, `9ROUTER_KEY` trong `.env` của Lexora; tên model có thể là giá trị hoặc tên biến `MODEL_*` trong `.env`.

```powershell
.venv\Scripts\python -m legal_ai.web --store data/kb/app-ai-new.sqlite --source-catalog .my_docs/sources-online/catalog.json --port 8766 `
  --extract-model MODEL_OSS_120B --embedding-model MODEL_EMB_GEMINI_1 --approve-router
```

- `--extract-model`: thêm lựa chọn "Bằng AI" ở bước nhập, chỉ cho kho công khai. Chỉ các câu bộ quy tắc chưa tách được mới được gửi; mọi thành phần AI trả về phải khớp đúng nguyên văn. Ngân sách `--extract-max-calls` (mặc định 60), timeout `--extract-timeout` (90 giây).
- `--embedding-model`: thêm ô "Tìm thêm theo ý nghĩa" khi hỏi trên các kho công khai. Số chiều `--embedding-dimensions` (768), ngân sách `--embedding-max-calls` (200). Vector được cache trong store.
- `--router-model`: trả lời bằng model có kiểm tra citation.

Xem [thiết kế F-KB-02](../../docs/features/knowledge-base-workflow.md) và [chat theo revision đã duyệt](../../docs/features/reviewed-kb-chat.md).
Chưa có OCR cho PDF scan, worker nền bền vững hoặc xác minh pháp lý đầy đủ.
