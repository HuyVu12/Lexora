# evaluation

`retrieval_run.py` (`retrieval-run-v1`): chạy truy xuất một điều kiện (ĐK1-ĐK4) trên một bundle, xếp hạng bằng BM25, dense hoặc hybrid và tính Recall@K trên đơn vị pháp lý chuẩn.
Không gọi mạng, không gọi model, không sinh câu trả lời.

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.cli run-retrieval data/normalized/full-v1 --condition configs/experiments/dk1.json --output experiments/runs/<run-id-moi>
```

Mỗi thư mục run có `manifest.json` (đầu vào kèm SHA-256, tham số, môi trường, commit Git), `records.jsonl`, `predictions.jsonl`, `metrics.json`, `errors.jsonl`.
Recall@K của một câu = số đơn vị gold được top-K bản ghi phủ / số đơn vị gold; một Khoản phủ Điều gold chứa nó.
Câu không có đơn vị gold (cần từ chối) bị loại khỏi trung bình và được đếm riêng.
Mỗi K còn báo số token chỉ mục trung bình của top-K, để thấy recall cao nhờ context dài.
Run chỉ được đánh dấu `frozen` khi cả cấu hình chung và cấu hình điều kiện có `status: frozen`.

Recall theo ngân sách token (mặc định 250, 500, 1.000, 1.500, 2.000, 3.000, 4.000, 6.000) đóng gói bản ghi bằng chính hàm của lượt sinh câu trả lời (`indexing/packing.py`, `context_packing` P0/P1/P2 trong cấu hình chung; ĐK1 luôn P0).
`metrics.json` có thêm tỉ lệ câu tìm đủ theo ngân sách và `tokens_to_reach`: ngân sách nhỏ nhất để recall trung bình đạt 0,4 và 0,8, tính chính xác từ các điểm gãy của từng câu.
Predictions giữ đủ bản ghi để lấp ngân sách lớn nhất; xếp hạng hybrid nối thêm phần đuôi theo RRF trên toàn danh sách, phần đầu không đổi.
Điều kiện có khối `validity` (`configs/experiments/validity/`) lọc theo ngày của câu hỏi (`as_of`, mặc định `shared.validity_as_of`): mức đơn vị bỏ đơn vị hết hiệu lực, bị bãi bỏ hoặc chưa có hiệu lực và ghi chú đơn vị đã bị sửa đổi; mức văn bản (ĐK1-hl) chỉ xét ngày hiệu lực của văn bản. Câu có `stale_unit_ids` được đo tỉ lệ ngữ cảnh chứa đơn vị lỗi thời.
Với `shared.query_slots` (lượt `cli query-slots`), mọi điều kiện xếp hạng bằng câu tìm kiếm theo chủ đề; ĐK3-q/ĐK4-q (`record: norm_lines`, `query.aliases`) chỉ giữ đơn vị có quy phạm khớp tính quy phạm, trường bắt buộc và chủ thể (`retrieval/norm_query.py`).

`answer_run.py` dùng cùng cách đóng gói của lượt truy xuất (nhóm theo Điều thì prompt `answer-v4.md`); `score` thêm tải kiểm chứng (`cited_tokens_per_statement`, `single_leaf_citation_rate`) và, cho bộ hiệu lực, `stale_citation_rate`.
`preflight.py` kiểm thêm ĐK2-ĐK4 cùng `context_packing`, cùng `query_slots`, và ĐK3/ĐK4 cùng khối `query`, `validity`.
`budget_report.py` (`cli budget-report`): bảng và hình SVG recall theo ngân sách từ `metrics.json` của các lượt đã chạy.

Chưa có: chấm grounding và correctness tự động (do người chấm theo `answer_sheet`).
