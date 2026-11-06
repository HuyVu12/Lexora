# Nguồn local đã ghim và chat theo revision được duyệt

Ngày 06/11/2026. Đã có UI local nhiều kho, offline regression tests và E2E trên browser thật. Không coi các kết quả là pháp luật đã xác minh.
Thiết kế vòng đời kho (tạo mới, gộp, chỉnh sửa, hỏi nhiều kho): [F-KB-02](knowledge-base-workflow.md).

## Phạm vi thực thi

- `legal_ai.ingestion.source_library.SourceLibrary`: đọc catalog `source-library-v1`, chặn path vượt thư mục catalog, kiểm tra bytes SHA-256 trước khi tạo draft. Không truy cập mạng khi người dùng chọn nguồn.
- `legal_ai.kb.import_review.ReviewStore` (`kb-store-v1`): nhiều kho, mỗi kho một chuỗi revision bất biến. Draft nhắm tới kho mới hoặc ghim revision hiện tại của một kho; quyết định review được lưu dần (`review_decisions`), có duyệt cả Điều và chỉnh sửa claim bằng câu trích nguồn (lớp `curated`, bản máy giữ nguyên). Duyệt mọi claim trước khi publish; draft stale nhận `Conflict` (HTTP 409). Nối đề cập thực thể bằng cạnh `REVIEWED_ENTITY_LINK` trong phạm vi một kho; không canonicalize toàn bộ entity. Store `import-review-v1` cũ được chuyển thành "Kho mặc định" mà không sửa revision.
- `legal_ai.rag.review_chat.ChatService`: session ghim revision của 1 đến 5 kho (`bindings`); chỉ lấy claim có `human_review.decision=approved`. Cùng một câu trích ở nhiều kho chỉ hiện một lần, ghi danh sách kho chứa. Chế độ LLM bị chặn nếu session có kho riêng tư. Lấy evidence của claim, không mở rộng thành toàn bộ source unit có thể chứa câu chưa được duyệt/bị loại. Quote/offset/hash được kiểm tra trước retrieval.
- Tra cứu local dùng BM25 trên các đoạn được phép, hỗ trợ không dấu, trả `sources_found` cùng nguyên văn. Đây là tra cứu nguồn, không phải sinh câu trả lời.
- Tìm kết hợp tùy chọn (`legal_ai.rag.dense`): khi chạy với `--embedding-model` và người dùng bật "Tìm thêm theo ý nghĩa", đoạn đã duyệt và câu hỏi được nhúng qua 9Router, xếp hạng RRF cùng BM25. Chỉ áp dụng khi mọi kho là công khai; lỗi embedding quay về BM25. Vector được cache trong SQLite theo model và SHA-256 của đoạn.
- Provider tùy chọn: `legal_ai.providers.router.RouterProvider` (chat) và `RouterEmbeddings`; mỗi instance một model đã duyệt và ngân sách gọi riêng, không fallback/retry, không redirect, `stream=false`, timeout 25 giây (tách quy phạm mặc định 90 giây), output có giới hạn. Endpoint/key chỉ đọc `9ROUTER_URL`/`9ROUTER_KEY` trong `.env` của Lexora; chỉ chấp nhận HTTPS hoặc loopback.
- LLM trả JSON statements với citation IDs. Gate từ chối schema sai hoặc citation ngoài bundle; không chứng minh legal entailment. Câu trả lời vẫn cần người đọc đối chiếu evidence.

## Chạy

Python 3.11+, standard library only. Không cài package. Node chỉ cần cho DOM smoke. Chạy từ workspace root:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.demo --store data/kb/demo-new.sqlite --seed data/kb/entity-relation-review/graph.json --port 8766
```

Seed là artifact local cần phục hồi từ nguồn pilot khi clone mới; với store mới, seed tạo "Kho mặc định". Bỏ `--seed` để bắt đầu không có kho nào; kho được tạo khi công bố bản nháp đầu tiên. Server chỉ bind `127.0.0.1`; lưu SQLite local, có token cho POST và kiểm tra Host/Origin.

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

- `GET /api/state`: danh sách kho, bản nháp, session.
- `GET /api/kb?id=...`: chi tiết kho, tài liệu, lịch sử revision.
- `GET /api/sources`: catalog nguồn đã có local.
- `POST /api/prepare`: `{title, text, synthetic, target, extraction}`; `POST /api/prepare-source`: `{source_id, target, extraction}`. `extraction` là `rules` (mặc định) hoặc `llm` (chỉ kho công khai, server phải chạy với `--extract-model`). `target` là `{mode: "new", name, description, data_class}` hoặc `{mode: "merge", kb_id}`. Trả draft view, không tự publish.
- `GET /api/draft?id=...`: draft view gồm Điều/đơn vị nguồn, claim, thực thể, tiến độ và diff với kho đích.
- `POST /api/draft/review`: `{draft_id, item_id, decision, payload}`; `decision` là `approve`, `reject`, `clear`, `edit`, `approve_article`, `link`, `no_link`, `add_claim` (`payload {unit_version_id, start, end}`), `remove_claim` (chỉ claim thêm thủ công), `no_norm` (câu chưa có quy phạm, `item_id = gap:...`), `no_norm_article`.
- `POST /api/draft/extract`: `{draft_id}` chạy lại tách bằng AI khi bản nháp chưa có quyết định.
- `POST /api/draft/discard`: `{draft_id}`.
- `POST /api/publish`: `{draft_id, reviewer, reason}` → `{revision, kb_id, summary}`; `409 base_changed` nếu kho đã có revision mới.
- `POST /api/chat/start`: `{kb_ids}` → session; từ chối kho chưa có claim được human review.
- `POST /api/chat/ask`: `{session_id, question, mode, allow_public_transfer, semantic}`; mode `extractive` mặc định, `llm` opt-in; `semantic: true` bật tìm kết hợp. Phản hồi có `retrieval: {mode: hybrid|lexical, reason}`.
- `GET /api/chat/session?id=...`: lịch sử và bindings.

Demo một người dùng, không phải production auth/SSO. Kho công bố revision mới thì session hiện có vẫn dùng revision cũ; tạo session mới để dùng revision mới. Từng câu hỏi cần đủ ngữ cảnh, chưa rewrite follow-up bằng model.

## Kiểm tra

```powershell
python -m unittest discover -s tests -q
python -m legal_ai.demo --store data/kb/browser-check-new.sqlite --port 8770
node scripts/check_demo_browser.cjs http://127.0.0.1:8770 data/interim/browser-check
```

Script thứ ba điều khiển Chrome hoặc Edge headless qua DevTools protocol, chạy kịch bản tạo kho, sửa claim, loại claim, duyệt cả Điều, công bố, gộp tài liệu có liên kết thực thể và hỏi đáp bằng dữ liệu minh họa; chụp màn hình từng bước và thất bại nếu console có lỗi. Cần store mới và không gọi model.

Regression tests kiểm tra publication gate, rejected-sentence exclusion, revision isolation qua publish/restart, phạm vi kho, tên kho trùng, draft stale (409), lưu quyết định dần, duyệt cả Điều, chỉnh sửa claim với câu trích không hợp lệ, migration store/session cũ, khử trùng citation đa kho, chặn LLM với kho riêng tư, evidence tampering, no-accent retrieval, consent/provider errors, citation ngoài bundle, source checksum/path và transport call budget. Chưa có gold độc lập hoặc benchmark retrieval/answer. Bộ ĐK1–ĐK4 chưa được hoàn tất bởi thay đổi này.
