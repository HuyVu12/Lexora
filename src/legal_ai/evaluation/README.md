# evaluation

`retrieval_run.py` (`retrieval-run-v1`): chạy truy xuất một điều kiện (ĐK1 hoặc ĐK2) trên một bundle, xếp hạng bằng BM25 và tính Recall@K trên đơn vị pháp lý chuẩn.
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

Chưa có: đóng gói context, sinh câu trả lời, chấm citation, grounding, correctness, abstention, ĐK3/ĐK4.
