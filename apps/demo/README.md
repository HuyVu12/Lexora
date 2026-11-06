# Demo local

Đã có UI nhập TXT → xem extraction/evidence → duyệt/loại và nối thực thể → gộp revision → chat trên phần đã duyệt. Code chạy ở `src/legal_ai/demo.py`, `demo.html`, `demo-chat.js`.

Python 3.11+, runtime stdlib, không cần cài package. Từ workspace root:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.demo --store data/kb/demo-new.sqlite --seed data/kb/entity-relation-review/graph.json --port 8766
```

Mở `http://127.0.0.1:8766`, dừng đúng terminal bằng Ctrl+C. Dùng store mới để bắt đầu từ seed; store đã tồn tại giữ nguyên dữ liệu. Không cần mạng cho chế độ tra cứu nguyên văn.

Xem [thiết kế và kiểm thử](../../docs/features/reviewed-kb-chat.md). Gói tài liệu demo local riêng của người dùng: `.my_docs/06-chat-va-nguon-moi.md`. Chưa có PDF/OCR, LLM extraction, dense retrieval hoặc xác minh pháp lý đầy đủ. Chế độ model tùy chọn không mặc định bật.
