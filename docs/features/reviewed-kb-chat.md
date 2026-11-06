# Nguồn local đã ghim và chat theo revision được duyệt

Ngày 06/11/2026. Đã có UI local và offline regression tests. Chưa có browser visual QA cho luồng mới. Không coi các kết quả là pháp luật đã xác minh.

## Phạm vi thực thi

- `legal_ai.ingestion.source_library.SourceLibrary`: đọc catalog `source-library-v1`, chặn path vượt thư mục catalog, kiểm tra bytes SHA-256 trước khi tạo draft. Không truy cập mạng khi người dùng chọn nguồn.
- `legal_ai.kb.import_review.ReviewStore`: nhận TXT, giữ raw/normalized source và extraction report; duyệt mọi claim trước khi publish, chặn draft stale, giữ revision cũ bất biến. Nối đề cập thực thể bằng cạnh `REVIEWED_ENTITY_LINK` có quyết định người duyệt; không canonicalize toàn bộ entity.
- `legal_ai.rag.review_chat.ChatService`: session cố định revision; chỉ lấy claim có `human_review.decision=approved`. Lấy evidence của claim, không mở rộng thành toàn bộ source unit có thể chứa câu chưa được duyệt/bị loại. Quote/offset/hash được kiểm tra trước retrieval.
- Tra cứu local dùng BM25 trên các đoạn được phép, hỗ trợ không dấu, trả `sources_found` cùng nguyên văn. Đây là tra cứu nguồn, không phải sinh câu trả lời.
- Provider tùy chọn: `legal_ai.providers.router.RouterProvider`; exact model + route approval + call budget, không fallback/retry, `stream=false`, timeout 25 giây, output/context có giới hạn. Endpoint/key chỉ đọc trong `.env` của Lexora.
- LLM trả JSON statements với citation IDs. Gate từ chối schema sai hoặc citation ngoài bundle; không chứng minh legal entailment. Câu trả lời vẫn cần người đọc đối chiếu evidence.

## Chạy

Python 3.11+, standard library only. Không cài package. Node chỉ cần cho DOM smoke. Chạy từ workspace root:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.demo --store data/kb/demo-new.sqlite --seed data/kb/entity-relation-review/graph.json --port 8766
```

Seed là artifact local cần phục hồi từ nguồn pilot khi clone mới. Có thể bỏ `--seed` để bắt đầu KB rỗng rồi nhập TXT. Server chỉ bind `127.0.0.1`; lưu SQLite local, có token cho POST và kiểm tra Host/Origin.

Nếu có catalog local đã chuẩn bị, thêm:

```powershell
python -m legal_ai.demo --store data/kb/demo-sources-new.sqlite --seed data/kb/entity-relation-review/graph.json --source-catalog .my_docs/sources-online/catalog.json --port 8766
```

Chế độ provider chỉ chạy sau phê duyệt người dùng về endpoint/model/dữ liệu/phạm vi gọi. Không coi quyền mạng là phê duyệt. Lệnh opt-in cụ thể:

```powershell
python -m legal_ai.demo --store data/kb/demo-sources-new.sqlite --source-catalog .my_docs/sources-online/catalog.json --router-model ollama/beam --approve-router --router-max-calls 3 --port 8766
```

Flag `--approve-router` là opt-in kỹ thuật, không khẳng định model miễn phí. UI yêu cầu xác nhận dữ liệu công khai và duyệt gửi từng lượt. Không dùng lịch sử session khác hoặc nguyên draft làm prompt. Không gửi tên reviewer hoặc key. Lỗi dịch vụ/quota/schema có status riêng, không phải kết luận pháp lý.

## API loopback

- `GET /api/sources`: catalog nguồn đã có local.
- `POST /api/prepare-source`: `{source_id}` → draft chờ người dùng review, không tự publish.
- `POST /api/chat/start`: `{revision}` → session; từ chối revision chưa có claim được human review.
- `POST /api/chat/ask`: `{session_id, question, mode, allow_public_transfer}`; mode `extractive` mặc định, `llm` opt-in.
- `GET /api/chat/session?id=...`: lịch sử và revision đã bind.

Demo một người dùng, một store/KB mỗi process, không phải production auth/SSO. Nếu KB gộp thêm, session hiện có vẫn dùng revision cũ; tạo session mới để dùng revision mới. Từng câu hỏi cần đủ ngữ cảnh, chưa rewrite follow-up bằng model.

## Kiểm tra

```powershell
python -m unittest discover -s tests -q
python .my_docs/verify_chat_ui.py
```

Lệnh thứ hai là tiện ích local của gói demo người dùng, cần Node và catalog `.my_docs/sources-online/catalog.json`. Nó chạy UI JavaScript với DOM mock, HTTP loopback thật và SQLite tạm riêng; chỉ publish fixture tổng hợp có nhãn, không gộp nguồn thật vào KB live hoặc gọi model.

Regression tests kiểm tra publication gate, rejected-sentence exclusion, revision isolation qua publish/restart, evidence tampering, no-accent retrieval, consent/provider errors, citation ngoài bundle, source checksum/path và transport call budget. Chưa có gold độc lập, benchmark retrieval/answer hoặc browser screenshot QA. Bộ ĐK1–ĐK4 chưa được hoàn tất bởi thay đổi này.
