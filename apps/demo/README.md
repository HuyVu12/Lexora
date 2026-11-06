# Demo local

Workspace nhiều kho tri thức: nhập TXT hoặc văn bản từ thư viện nguồn → duyệt quy phạm trên nguyên văn (duyệt, loại, sửa bằng câu trích, duyệt cả Điều) → xem trước rồi tạo kho mới hoặc gộp vào kho có sẵn → hỏi đáp trên một hoặc nhiều kho.
Code chạy ở `src/legal_ai/demo.py`, `demo.html`, `demo.css`, `demo-app.js`.

Python 3.11+, runtime stdlib, không cần cài package. Từ workspace root:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.demo --store data/kb/demo-new.sqlite --port 8766
```

Mở `http://127.0.0.1:8766`, dừng đúng terminal bằng Ctrl+C.
Store mới không có kho nào; kho được tạo khi công bố bản nháp đầu tiên.
Thêm `--seed data/kb/entity-relation-review/graph.json` để khởi tạo "Kho mặc định" từ graph seed (chỉ áp dụng cho store mới).
Store cũ một chuỗi revision được tự chuyển thành "Kho mặc định" khi mở; revision cũ không bị sửa.
Không cần mạng cho chế độ trích nguyên văn.

Kiểm thử giao diện trên browser thật (Chrome hoặc Edge headless, không cần npm), dùng store mới:

```powershell
python -m legal_ai.demo --store data/kb/browser-check-new.sqlite --port 8770
node scripts/check_demo_browser.cjs http://127.0.0.1:8770 data/interim/browser-check
```

Script chạy toàn bộ luồng bằng dữ liệu minh họa, chụp màn hình từng bước và báo lỗi nếu console có lỗi.

Câu không có quy phạm nào được gạch chân chấm trên màn hình duyệt; mỗi câu phải được thêm quy phạm hoặc đánh dấu "Không phải quy phạm" trước khi công bố.

## Tùy chọn AI qua 9Router

Mặc định demo không gọi mạng.
Chỉ bật khi người dùng đã duyệt endpoint, model, dữ liệu và phạm vi theo `AGENTS.md`.
Endpoint và key đọc từ `9ROUTER_URL`, `9ROUTER_KEY` trong `.env` của Lexora; tên model có thể là giá trị hoặc tên biến `MODEL_*` trong `.env`.

```powershell
python -m legal_ai.demo --store data/kb/demo-ai-new.sqlite --source-catalog .my_docs/sources-online/catalog.json --port 8766 `
  --extract-model MODEL_OSS_120B --embedding-model MODEL_EMB_GEMINI_1 --approve-router
```

- `--extract-model`: thêm lựa chọn "Bằng AI" ở bước nhập, chỉ cho kho công khai. Chỉ các câu bộ quy tắc chưa tách được mới được gửi; mọi thành phần AI trả về phải khớp đúng nguyên văn. Ngân sách `--extract-max-calls` (mặc định 60), timeout `--extract-timeout` (90 giây).
- `--embedding-model`: thêm ô "Tìm thêm theo ý nghĩa" khi hỏi trên các kho công khai. Số chiều `--embedding-dimensions` (768), ngân sách `--embedding-max-calls` (200). Vector được cache trong store.
- `--router-model`: trả lời bằng model có kiểm tra citation, như trước.

Kiểm thử browser có AI (gửi dữ liệu minh họa tới model đã chọn): thêm `--ai` vào lệnh `check_demo_browser.cjs` và chạy demo với `--extract-model`.

Xem [thiết kế F-KB-02](../../docs/features/knowledge-base-workflow.md) và [chat theo revision đã duyệt](../../docs/features/reviewed-kb-chat.md).
Chưa có PDF/OCR, worker nền bền vững hoặc xác minh pháp lý đầy đủ.
