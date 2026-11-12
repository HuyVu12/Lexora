# configs/experiments

Cấu hình điều kiện truy xuất (`dk*.json`) và cấu hình dùng chung (`shared.json`, `answer*.json`) cho `cli run-retrieval` và `cli answer-run`.
Một tệp cấu hình đã dùng cho một lượt chạy thì không sửa nữa, vì manifest của lượt chạy ghi SHA-256 của tệp; muốn đổi thì tạo tệp mới.

## Điều kiện chính và mở rộng (kế hoạch nghiên cứu 11/11)

- `dk1-128.json`: ĐK1 chính từ 12/11/2026 (đoạn 128 token, gối 21), chọn theo recall của chính ĐK1 trên dev; `dk1.json` (384 token, gối 64) giữ để tái lập các lượt cũ và làm điểm độ nhạy.
- `dk2.json`: ĐK2 (đơn vị lá kèm đường dẫn).
- `corpus-v2/dk3-compact.json`, `corpus-v2/dk4-compact.json`: ĐK3, ĐK4 theo định nghĩa ở mục 6 của kế hoạch (bản ghi ĐK2 cộng dòng quy phạm gọn, đồ thị dẫn chiếu hai chiều).
- `validity/`: ĐK1-hl (lọc hiệu lực mức văn bản) và ĐK2-ĐK4 có lọc hiệu lực mức đơn vị (`unit-status-v1`) cho bộ hiệu lực (WP4).
- `query/`: ĐK3-q, ĐK4-q (`norm-query-v1`) trên kho gpt-oss-120b và kho gemma4:31b cho bộ liệt kê (WP5); cần `shared.query_slots` từ `cli query-slots`.
- `actor-aliases.json`: bảng bí danh chủ thể của `norm-query-v1`, phải được nhóm chốt trước lượt chạy ĐK3-q/ĐK4-q đầu tiên.
- `answer-main.json`: cấu hình sinh câu trả lời cho lượt chính (prompt `answer-v4.md`, 3.000 token, top 50); model chốt trên dòng lệnh.
- `ablations/dk1-chunk{128,256,512}.json`: độ nhạy cỡ đoạn của ĐK1 (WP2), chỉ đo truy xuất trên tập dev; `dk1-chunk128.json` cùng tham số với `dk1-128.json`.

Cách đóng gói ngữ cảnh (`context_packing`: P0, P1, P2 của `pack-article-v1`) nằm trong cấu hình dùng chung; ĐK1 luôn là P0.

## Đóng băng từ 11/11/2026

Các cấu hình dưới đây chỉ dùng để tái lập các lượt đã chạy và được báo cáo là thăm dò; không chạy thêm và không dùng để kết luận (xem `docs/decisions.md`, 11/11/2026):

- toàn bộ `ablations/dk3-*.json`, `ablations/dk4-*.json`;
- `corpus-v2/dk{3,4}-chain.json`, `corpus-v2/dk{3,4}-concept.json`, `corpus-v2/dk{3,4}-sibling.json`, `corpus-v2/dk{3,4}-relation.json`, `corpus-v2/dk{3,4}-relation-sonnet.json`.
