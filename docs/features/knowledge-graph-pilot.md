# Knowledge graph — bản pilot để review

Ngày 02/11/2026. Người dùng xác nhận ưu tiên xem graph Điều/Khoản, dẫn chiếu, quy phạm và mở bằng chứng. Đây là trọng tâm demo mới; chưa đổi Jira/GitHub hoặc tự đồng bộ task/status.

Bản mở rộng ngày 03/11: [graph thực thể–quan hệ với quy phạm làm trung tâm](entity-relation-graph.md). Tài liệu này giữ mô tả bản cấu trúc/dẫn chiếu đầu tiên.

## Mở và review

Mở [`graph local`](../../data/kb/knowledge-graph-review/index.html) bằng browser. File tự chứa dữ liệu và JavaScript, không cần server, thư viện tải từ CDN hoặc kết nối dịch vụ. Dữ liệu trong file này là nguồn pháp luật công khai, không có hồ sơ private.

1. Mặc định xem cấu trúc và dẫn chiếu. Chọn node để đọc nguồn và các quan hệ liên quan; chọn đường nối để mở evidence của cạnh.
2. Tìm `Điều 25` để đi tới node, xem các khoản và câu dẫn được lưu riêng ở node Điều. Các dòng nội dung dài được rút gọn trên graph; tiêu đề đầy đủ hiện trong panel.
3. Chọn node khoản 2 Điều 24: nguồn dẫn sáu điểm a, b, c, đ, g, h khoản 1 Điều 21. Graph có sáu cạnh REFERENCES đến đúng các điểm.
4. Chọn Điều 6 Nghị định 145: cạnh REFERENCES trỏ sang khoản 1 Điều 21 Bộ luật Lao động. Chọn cạnh để xem quote gốc `khoản 1 Điều 21 của Bộ luật Lao động`.
5. Chuyển lớp `Ứng viên quy phạm`. Có 12 candidate, tất cả needs_review. Chọn candidate để đọc toàn bộ đơn vị nguồn; actor/conditions/exceptions còn unknown.

Browser automation của phiên trả `The browser access host is unavailable`, nên chưa kiểm tra trực quan layout/screenshot. Đã chạy DOM unit smoke bằng Node cho khởi tạo, evidence panel, cạnh xuyên văn bản, đổi lớp candidate, tìm node, lọc văn bản và reset. DOM smoke không thay cho kiểm thử browser thật; cần người dùng review trực quan.

## Dữ liệu graph

Bộ graph dùng snapshot VBPL đã tải trước đó, không có request external mới. `configs/sources-graph.json` giữ nguồn/hash như pilot cũ và thêm Điều 21 để giải quyết dẫn chiếu; `configs/sources-pilot.json` và `pilot-v2` không đổi.

| Nội dung | Số lượng |
|---|---:|
| Văn bản | 2 |
| Đơn vị cấu trúc (Chương/Mục/Điều/Khoản/Điểm) | 34 |
| Đơn vị mục tiêu / ngữ cảnh cha | 30 / 4 |
| Đoạn dẫn chiếu phát hiện | 2 |
| Cạnh REFERENCES | 7 |
| Ứng viên quy phạm needs_review | 12 |
| Node Evidence | 36 |
| Tổng node / cạnh, gồm evidence và slot | 98 / 115 |

Hai đoạn dẫn chiếu sinh bảy cạnh vì một đoạn có danh sách sáu điểm, đoạn còn lại có một đích. Không được diễn giải bảy cạnh thành bảy nguồn độc lập. Chỉ resolve đích có trong phiên bản dữ liệu đã nạp; không xác nhận hiệu lực, quan hệ sửa đổi hoặc tính đầy đủ của căn cứ.

## Loại node và cạnh

| Node | Nội dung |
|---|---|
| Document | Tên, URL, snapshot hash, document version và synthetic flag |
| LegalUnit | Đơn vị cấu trúc, logical ID/version, own text, parent và source span |
| ReferenceMention | Raw mention, mô tả đích, trạng thái resolved/pending/external/ambiguous/needs_review |
| NormClaim | Claim/candidate kèm validation decision và extraction scope |
| ClaimSlot | Slot có nội dung và evidence; unknown không biến thành node thực thể pháp lý |
| Evidence | Quote, unit version, Unicode offsets và text hash |

Các cạnh: PART_OF, MENTIONS_REFERENCE, REFERENCES, EXTRACTED_FROM, HAS_SLOT, SUPPORTED_BY, ANCHORED_IN. Mỗi cạnh có evidence IDs trỏ đến quote đã kiểm tra; cả hai endpoint phải tồn tại.

PART_OF là kết quả parser. REFERENCES là dẫn chiếu tường minh được resolver bind vào đích tồn tại. Candidate được tạo theo các dấu hiệu từ ngữ như “phải”, “có quyền”, “không quá”; chưa tách thành quy phạm nguyên tử hoặc xác định modality/actor/điều kiện. Chưa triển khai DEFINES, AMENDS, REPLACES hoặc EXCEPTION_TO. Không tạo các cạnh đó chỉ từ similarity hoặc từ “trừ”.

## Resolver

- Bỏ qua tiêu đề Điều ở đầu own text, không coi đó là dẫn chiếu.
- Hiểu `Điều N`, `khoản M Điều N`, và danh sách điểm tường minh thuộc cùng khoản/Điều.
- `Bộ luật này` hoặc tên loại văn bản kèm “này” giữ phạm vi văn bản nguồn. Tên văn bản khác chỉ bind theo alias cấu hình tường minh, hiện có `Bộ luật Lao động → bll-45-2019`.
- Một label trùng nhiều đích → ambiguous, không tạo REFERENCES.
- Thiếu đích hoặc thiếu một điểm trong danh sách → pending, không tạo đích giả hoặc link danh sách thiếu thành đầy đủ.
- Danh sách nhiều khoản và cách diễn đạt ngoài pattern hiện có → needs_review; chưa có parser dẫn chiếu pháp luật tổng quát.
- Nhiều lần cùng một quote trong source tạo mention/evidence riêng theo offset; không fuzzy align.

## Lưu trữ

Graph đang dùng JSON và SQLite stdlib, chưa cài Neo4j. SQLite có bảng nodes, edges và metadata; edge endpoints dùng foreign keys, source/target có index. `graph_hash` bất biến theo nội dung; output mới/rỗng để không ghi đè snapshot graph cũ.

Đây là mô hình knowledge graph, còn backend có thể chuyển sau khi đo truy vấn/traversal thực tế. Chưa có GraphRAG trả lời bằng LLM, upload, phân quyền nhiều người dùng, review chỉnh sửa hoặc Neo4j deployment.

## Lệnh tái lập

Python 3.11+, thư viện chuẩn; Node 24 đã được dùng để chạy DOM smoke, không cài npm package. Chạy từ Lexora; dùng output chưa tồn tại hoặc tên mới:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.cli build-pilot --config configs/sources-graph.json --output data/normalized/graph-review-rebuild
python -m legal_ai.cli graph-build data/normalized/graph-review-rebuild --output data/kb/graph-review-rebuild
python -m unittest discover -s tests -v
node scripts/check_graph_viewer.cjs data/kb/graph-review-rebuild/index.html
```

Đã chạy các lệnh build vào `graph-pilot-v1` và `knowledge-graph-review`; 40 unittest pass. Bổ sung 14 tests graph cho reference resolution, alias, danh sách điểm, ambiguous/missing target, provenance, candidate status, hash ổn định, SQLite integrity/FK và escaping dữ liệu khi render.

Artifacts local bị loại khỏi Git theo chính sách data hiện có. File `index.html` mở độc lập được; để build lại từ clone mới cần phục hồi snapshots đã ghim. Xem [gói pilot trước](../planning/local-pilot-review-2026-11-02.md) để biết backup/restore.

## Việc tiếp theo theo trọng tâm mới

1. Review graph và bảng nguồn, nhất là cạnh xuyên văn bản và các candidate.
2. Hoàn thiện extraction actor/modality/action/conditions/exceptions với slot evidence; bổ sung model runtime khi có tài nguyên đã chốt.
3. Tách candidate graph và graph đã duyệt theo revision/policy; chưa dùng candidate unknown làm căn cứ đã xác minh.
4. Bổ sung quy trình duyệt/sửa cạnh có audit; mở rộng resolver có bộ ca pháp luật được gán độc lập.
5. Sau đó mới dùng graph traversal để cấp evidence bundle cho hỏi đáp; đo so sánh với retrieval hiện tại.

Schema graph, source mapping và chất lượng cạnh là ưu tiên. Chưa kéo thêm graph database, chatbot hoặc OCR vào cùng lát cắt này.
