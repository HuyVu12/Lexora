# configs/experiments

Cấu hình điều kiện truy xuất (`dk*.json`) và cấu hình dùng chung (`shared.json`, `answer*.json`) cho `cli run-retrieval` và `cli answer-run`.
Một tệp cấu hình đã dùng cho một lượt chạy thì không sửa nữa, vì manifest của lượt chạy ghi SHA-256 của tệp; muốn đổi thì tạo tệp mới.

## Thiết kế chính từ 23/11/2026

Đây là bộ điều kiện chính, chốt theo các dòng ngày 22/11 và 23/11/2026 của `docs/decisions.md` (lựa chọn hiệu lực B, kế thừa câu dẫn và `kb-validator-v4`, dòng thu gọn, không dùng khóa tìm kiếm), dùng với `shared-rrf100.json` (hybrid, `rrf_candidates` 100, P3 cho ĐK2-ĐK4, ĐK1 luôn P0).

- `main-v3/`: bộ khó (tình huống, xung đột, phức tạp) và bộ hiệu lực trên corpus v3.
  - `dk1.json`: ĐK1-hl, đoạn 128 token gối 21, lọc hiệu lực mức văn bản như ĐK2.
  - `dk2.json`: đơn vị lá, lọc hiệu lực mức văn bản (như `validity-b/dk2.json`).
  - `dk3.json`: ĐK2 cộng kho chưa kiểm chứng `kb-inherit-2026-11-23/v3-sonnet-v4-inherit` (`dk3.jsonl`), `claims_view: thin`, không có `index_keys`, đồ thị dẫn chiếu như trước cộng cạnh sửa đổi (`graph.amendments`), lọc mức văn bản.
  - `dk4.json`: cùng kho nhưng chỉ quy phạm qua `kb-validator-v4` (`dk4.jsonl`), cạnh sửa đổi chỉ dùng khi có hiệu lực tới ngày của câu hỏi, rồi lọc trạng thái đơn vị (`unit-status-v2`).
- `main-v1/`: bộ tra cứu trên corpus v1 (94 Điều, quyết định 15/11/2026) với kho dẫn xuất `kb-inherit-2026-11-23/v1-gptoss-v4-inherit` của gpt-oss-120b; cùng thiết kế nhưng không có khối `validity` vì corpus v1 không có cạnh sửa đổi.

Khóa do model soạn (`kb-keys-v2`) không qua cổng ngày 23/11 và khóa tất định (`kb-keys-v1`) không giúp, nên cả hai không thuộc thiết kế chính; `kb-keys/` chỉ để tái lập lượt thăm dò.
Lượt chạy thử đầu tiên của thiết kế này: `experiments/runs/main-dryrun-2026-11-23`.

## Điều kiện chính và mở rộng (kế hoạch nghiên cứu 11/11)

- `dk1-128.json`: ĐK1 chính từ 12/11/2026 (đoạn 128 token, gối 21), chọn theo recall của chính ĐK1 trên dev; `dk1.json` (384 token, gối 64) giữ để tái lập các lượt cũ và làm điểm độ nhạy.
- `dk2.json`: ĐK2 (đơn vị lá kèm đường dẫn).
- `corpus-v2/dk3-compact.json`, `corpus-v2/dk4-compact.json`: ĐK3, ĐK4 theo định nghĩa ở mục 6 của kế hoạch (bản ghi ĐK2 cộng dòng quy phạm gọn, đồ thị dẫn chiếu hai chiều).
- `validity/`: ĐK1-hl (lọc hiệu lực mức văn bản) và ĐK2-ĐK4 có lọc hiệu lực mức đơn vị (`unit-status-v1`) cho bộ hiệu lực (WP4).
  Từ 22/11/2026 (lựa chọn A ở mục 7 của `docs/planning/dk2-dk4-improvement-2026-11-22.md`) chỉ dùng để tái lập lượt chạy thử 16/11.
- `validity-b/`: bộ hiệu lực theo lựa chọn B (quyết định 22/11/2026), mỗi bậc thêm một cơ chế:
  - `dk2.json`: ĐK2 chỉ lọc theo ngày hiệu lực của văn bản (`validity.level: document`, như ĐK1-hl); không có cạnh sửa đổi, không có trạng thái đơn vị.
  - `dk3.json`: ĐK3 là ĐK2 cộng kho chưa kiểm chứng; cạnh sửa đổi (`amendment-rules-v2`) là quan hệ của kho (`graph.amendments`, `amendment-expansion-v1`): đơn vị được chọn kéo theo đơn vị sửa nó hoặc bị nó sửa, kèm ghi chú quan hệ, chỉ theo cạnh đã giải được; không kiểm trạng thái nên đơn vị lỗi thời vẫn có thể nằm trong ngữ cảnh; lọc mức văn bản như ĐK2.
  - `dk4.json`: ĐK4 là ĐK3 cộng kiểm chứng: quy phạm đã qua bộ kiểm chứng, quan hệ sửa đổi chỉ dùng khi cạnh có ngày hiệu lực tới ngày của câu hỏi, rồi lọc trạng thái đơn vị (`unit-status-v2`) trên cùng bộ cạnh; quy phạm của bản ghi bị loại được đếm là không dùng.
  - ĐK1 dùng lại `dk1-128.json` và `validity/dk1-hl.json`.
  - `cli preflight` kiểm thang này khi ĐK3 và ĐK4 khác khối `validity` (cùng ngày mặc định, ĐK2 và ĐK3 cùng lọc mức văn bản, ĐK3 và ĐK4 cùng bộ cạnh, các bước kiểm của ĐK4 chứa hẳn các bước của ĐK3).
- `query/`: ĐK3-q, ĐK4-q (`norm-query-v1`) trên kho gpt-oss-120b và kho gemma4:31b cho bộ liệt kê (WP5); cần `shared.query_slots` từ `cli query-slots`.
- `actor-aliases.json`: bảng bí danh chủ thể của `norm-query-v1`, phải được nhóm chốt trước lượt chạy ĐK3-q/ĐK4-q đầu tiên.
- `answer-main.json`: cấu hình sinh câu trả lời cho lượt chính (prompt `answer-v4.md`, 3.000 token, top 50); model chốt trên dòng lệnh.
- `ablations/dk1-chunk{128,256,512}.json`: độ nhạy cỡ đoạn của ĐK1 (WP2), chỉ đo truy xuất trên tập dev; `dk1-chunk128.json` cùng tham số với `dk1-128.json`.

Cách đóng gói ngữ cảnh (`context_packing`: P0, P1, P2, P3 của `pack-article-v1`) nằm trong cấu hình dùng chung; ĐK1 luôn là P0.
P3 (kế hoạch 22/11, mục 3.1) giữ xếp hạng và phần thêm anh em của P2, nhưng in câu dẫn của mỗi Khoản một lần trong khối Điều và dùng tên văn bản rút gọn tới số hiệu; mỗi Điểm vẫn có mã đoạn riêng.

- `shared-rrf100.json`: ứng viên của kế hoạch 22/11, khác `shared.json` đúng hai trường (`rrf_candidates` 100 cho mọi điều kiện kể cả ĐK1, `context_packing` P3 cho ĐK2-ĐK4); chọn trên dev bằng quy tắc của WP3 trước mốc dừng biến thể.
- `kb-keys/`: ĐK3/ĐK4 trên corpus v3 với kho dẫn xuất (`claims-inherit-v1` cộng `kb-validator-v4`), biến thể `claims_view` (`compact`, `thin`) và `index_keys` (`kb-keys-v1`: khóa tất định chỉ vào phần chữ đánh chỉ mục), không lọc hiệu lực; dùng cho lượt thăm dò `experiments/runs/kb-keys-2026-11-23`.
  `kb-keys/dk3-mkeys-thin.json`, `dk4-mkeys-thin.json`: như `*-keys-thin` nhưng `index_keys` là `kb-keys-v2` (khóa tất định cộng câu hỏi do model soạn bằng `cli kb-keys-gen`, chỉ để tìm); cần lượt khóa đã được duyệt và chạy.
- ĐK3/ĐK4 với kế thừa câu dẫn: tạo tệp điều kiện mới (không sửa tệp cũ) với `kb_run` trỏ vào thư mục dẫn xuất của `cli kb-materialize <run> --output <mới> --validator kb-validator-v4 --inherit claims-inherit-v1`; manifest dẫn xuất giữ `units_sha256` của lượt gốc nên `run-retrieval` dùng được ngay.

## Đóng băng từ 11/11/2026

Các cấu hình dưới đây chỉ dùng để tái lập các lượt đã chạy và được báo cáo là thăm dò; không chạy thêm và không dùng để kết luận (xem `docs/decisions.md`, 11/11/2026):

- toàn bộ `ablations/dk3-*.json`, `ablations/dk4-*.json`;
- `corpus-v2/dk{3,4}-chain.json`, `corpus-v2/dk{3,4}-concept.json`, `corpus-v2/dk{3,4}-sibling.json`, `corpus-v2/dk{3,4}-relation.json`, `corpus-v2/dk{3,4}-relation-sonnet.json`.
