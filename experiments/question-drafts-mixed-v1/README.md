# Bộ câu hỏi trộn v1 (thử nghiệm chọn láng giềng, 11/11/2026)

Bản sao được theo dõi trong Git của bộ câu dùng ở `docs/planning/graph-legal-reasoning-2026-11-10.md` (mục 7-8); bản chạy gốc nằm ở `experiments/runs/mixed-select-v1/` (ngoài Git).

- `questions.json`: 85 câu xáo trộn (hạt giống `lexora-mixed-v1`): 25 câu tra cứu đơn giản và 5 câu ngoài phạm vi lấy mẫu từ `experiments/runs/dryrun-v1/questions.json`, 30 câu phức tạp từ `dryrun-complex-v1`, 25 câu xung đột từ `dryrun-conflict-v1`; trường `level` (simple, out_of_scope, complex) và `source_set` ghi nguồn.
- `subqueries-sonnet.jsonl` và `subqueries-sonnet-manifest.json`: lượt tách vấn đề bằng Claude Sonnet 5.5 (`decompose-v1`, 85 lượt).

Nhãn là đề xuất của model, chưa có người duyệt; nhãn của các câu lấy từ `dryrun-v1` và `dryrun-complex-v1` được soạn trên corpus v1 (94 Điều) nên có thể thiếu đơn vị chỉ có ở corpus v2.
Chỉ dùng cho chạy thử; không dùng làm held-out.

Để chạy lại trên máy khác: chép `questions.json` vào một thư mục chạy mới và chép hai tệp tách vấn đề vào `<thư mục>/decompose-sonnet/` với tên `subqueries.jsonl` và `manifest.json`.
