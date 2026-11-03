# Graph thực thể–quan hệ với quy phạm làm trung tâm

Ngày 03/11/2026. Trạng thái: đã triển khai local để review, mọi quy phạm vẫn `needs_review`. Không gọi model, không có request external, không cập nhật Jira/GitHub trong tác vụ này.

## Review giao diện

Mở [graph thực thể–quy phạm](../../data/kb/entity-relation-review/index.html). Giao diện mặc định tập trung vào một quy phạm: nguồn ở trái, quy phạm ở giữa, thực thể/hành động/ràng buộc ở phải. Có liên kết sang [graph cấu trúc và dẫn chiếu](../../data/kb/entity-relation-review/structure.html).

- Chọn quy phạm trong dropdown, hoặc tìm theo nội dung nguồn như `85%`, `hủy bỏ`, `người sử dụng lao động`.
- Chọn node để đọc bằng chứng riêng; chọn cạnh để đọc quote hỗ trợ quan hệ đó.
- Mặc định chỉ hiện 8 quy phạm ứng viên có thành phần đã tách. Bỏ chọn bộ lọc để thấy thêm 4 ứng viên chưa có quy tắc hỗ trợ.
- Thành phần unknown được ghi “Chưa xác định”, không tự tạo thành node có vẻ đã biết.
- Giao diện không cần server/CDN hay model. Chưa có kiểm tra trực quan browser/screenshot; đã có DOM unit smoke, không thay cho browser QA thực tế.

## Khác với phiên bản trước

Phiên bản trước chủ yếu có cấu trúc/dẫn chiếu và một slot action chứa nguyên đơn vị nguồn. Phiên bản này thêm node có loại và cạnh có vai trò:

| Vai trò | Node | Cạnh từ NormClaim |
|---|---|---|
| Chủ thể | Entity | HAS_ACTOR |
| Bên nhận thông tin/kết quả | Entity | HAS_RECIPIENT |
| Bên thụ hưởng | Entity | HAS_BENEFICIARY |
| Hành động | Action | HAS_ACTION |
| Đối tượng | LegalConcept | HAS_OBJECT |
| Tính quy phạm | Modality | HAS_MODALITY |
| Điều kiện | Condition | HAS_CONDITION |
| Ngoại lệ | Exception | HAS_EXCEPTION |
| Định lượng | Quantity | HAS_QUANTITY |
| Thời hạn | Deadline | HAS_DEADLINE |
| Kết quả | Outcome | HAS_OUTCOME |
| Ngữ cảnh ở đơn vị cha | Scope | HAS_SCOPE |

Mỗi node/quan hệ semantic có evidence IDs riêng, quote exact, Unicode offsets, unit version và text hash. Quy phạm nối về đơn vị nguồn bằng EXTRACTED_FROM; các quan hệ cấu trúc/dẫn chiếu cũ tiếp tục tồn tại.

Entity hiện là **đề cập có phạm vi theo từng quy phạm**. Hai lần xuất hiện “người lao động” chưa được tự gộp thành một thực thể toàn cục; “mỗi bên” và chủ thể kết hợp bằng “và” không được tự diễn giải thành các chủ thể độc lập.

## Ví dụ từ snapshot thật

Từ câu đầu khoản 1 Điều 27 đã lưu:

| Thành phần | Text được trích |
|---|---|
| Chủ thể | người sử dụng lao động |
| Tính quy phạm | obligation, evidence là `phải` |
| Hành động | thông báo |
| Đối tượng | kết quả thử việc |
| Bên nhận | người lao động |
| Điều kiện | Khi kết thúc thời gian thử việc |

Đây là kết quả trích xuất ứng viên từ snapshot, chưa phải kết luận pháp lý đã được người review xác nhận. Các câu tiếp theo về đạt/không đạt yêu cầu chưa được bóc tách tự động và vẫn được ghi trong extraction report; không suy từ câu đầu thành đã hiểu toàn bộ khoản.

Đối với khoản 2 Điều 27: giữ nguyên đối tượng kết hợp bằng `hoặc`, và giữ `mà không cần báo trước và không phải bồi thường` trong Outcome. Không đổi các phủ định đó thành nghĩa vụ và không gọi chúng là ngoại lệ.

Đối với các khoản Điều 25: giữ nguyên raw bound `Không quá ... ngày`/`ngày làm việc`, điều kiện công việc và toàn bộ own text ở Điều cha. Đối tượng `Thời gian thử việc` có bằng chứng riêng từ cha. Không đoán chủ thể hoặc tính quy phạm khi câu không nêu rõ.

Đối với Điều 26: giữ `ít nhất phải bằng 85% mức lương của công việc đó` cùng cơ sở tính. Không tự gán người sử dụng lao động làm actor khi actor chưa được pattern xác định trực tiếp.

## Phạm vi và chất lượng hiện có

- Input vẫn là 34 đơn vị cấu trúc thuộc hai snapshot VBPL đã ghim; không tải thêm nguồn và không sửa `pilot-v2`.
- Tạo 12 ứng viên: 8 có thành phần semantic, 4 fallback còn nguyên đơn vị nguồn; tất cả needs_review. Có 13 đơn vị lá khác không sinh candidate. Không coi 8/12 là precision/recall extraction.
- Graph thật có 5 node đề cập Entity, 4 Action, 7 LegalConcept, 7 Condition, 5 Quantity, 4 Modality, 1 Outcome và 8 Scope.
- Chưa có Exception/Deadline được trích từ corpus thật này. Hai loại đó đã có quy tắc và được kiểm tra trên fixture tổng hợp có nhãn; không thêm dữ liệu giả vào graph thật.
- Cơ chế hiện tại dùng các grammar/rule có giới hạn trong `src/legal_ai/extraction/norms.py`: câu deontic tường minh, giới hạn ngày, pattern lương thử việc và hai pattern hành động/đối tượng. Không phải bộ trích xuất pháp luật tổng quát hoặc LLM.
- Chưa có gold độc lập, đánh giá F1/qualifier recall, review sửa dữ liệu, entity resolution toàn cục, giải quyết xung đột quy định hoặc xác minh hiệu lực.

Những phần không khớp grammar được giữ nguyên trong `graph.json → extraction_report → unparsed_sentences`. Mọi claim luôn giữ `completeness=unknown`. Câu dẫn cha được lưu riêng dưới Scope; chưa suy luận AND/OR giữa các điều kiện ngầm định.

## Contract và version

Graph mới có `graph_version=evidence-graph-v2`. Các artifact v1 cũ giữ nguyên.

Contract pilot bổ sung tùy chọn `modality_evidence_ids` và slot `recipient`. Đầu vào cũ thiếu field tùy chọn vẫn đọc được. Claim mới có modality known phải có evidence cho từ quy phạm; validator kiểm tra cue có khớp nhãn như `phải → obligation`, `không được → prohibition`. Đây là consistency check của grammar, không chứng minh ngữ nghĩa pháp lý.

Slot text tiếp tục dùng nguyên văn; định lượng chưa được chuyển thành cấu trúc số/comparator/trigger/basis độc lập. Không sửa “ngày” thành “ngày làm việc”. Runtime cũ không hiểu field/slot mới cần cập nhật trước khi đọc các claim mới; xem [migration note](../planning/schema-v1-migration.md).

Config mới `configs/entity-graph.json` chọn `extraction_mode=norm-rules-v1`; config graph cũ vẫn chọn unit-cues. Lưu graph bằng JSON/SQLite local, chưa cần cài graph database khác.

## Tái lập và kiểm thử

Python 3.11+; runtime stdlib. Node 24 chỉ dùng cho DOM unit smoke, không cần npm install. Chạy từ Lexora, chọn output mới:

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.cli graph-build data/normalized/graph-pilot-v1 --config configs/entity-graph.json --output data/kb/entity-review-rebuild
python -m unittest discover -s tests -v
node scripts/check_entity_graph_viewer.cjs data/kb/entity-review-rebuild/index.html
node scripts/check_graph_viewer.cjs data/kb/entity-review-rebuild/structure.html
```

Đã chạy 56 unittest pass và hai DOM smoke pass. Tests mới kiểm tra actor/action/condition/exception/deadline có span riêng, giữ phủ định và ngày làm việc, tách recipient khỏi beneficiary, bảo toàn disjunction/outcome, giữ điều kiện cha, báo đoạn chưa parse, không gộp entity theo surface text và không chấp nhận modality có evidence sai.

Artifacts local bị `.gitignore` loại khỏi Git theo chính sách repo. Mở `index.html` tự chứa dữ liệu để review; build từ clone mới cần phục hồi source bundle/snapshots đã ghim như hướng dẫn pilot trước.
