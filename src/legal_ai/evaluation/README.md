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
Điều kiện có khối `validity` (`configs/experiments/validity/`) lọc theo ngày của câu hỏi (`as_of`, mặc định `shared.validity_as_of`): mức đơn vị bỏ đơn vị hết hiệu lực, bị bãi bỏ hoặc chưa có hiệu lực và ghi chú đơn vị đã bị sửa đổi; mức văn bản (ĐK1-hl) chỉ xét ngày hiệu lực của văn bản. Câu có `stale_unit_ids` được đo tỉ lệ ngữ cảnh chứa đơn vị lỗi thời; câu có thêm `not_yet_effective_unit_ids` được đo chỉ số bổ sung `wrong_version_context_rate_at_tokens` (đơn vị lỗi thời hoặc chưa có hiệu lực). Mỗi dự đoán ghi `validity.as_of` và `as_of_source` (`question` hoặc `default`); khi đóng gói P2, Khoản, Điểm anh em đi qua cùng quy tắc hiệu lực (`kb.validity.RecordFilter`) ở cả lượt truy xuất lẫn lượt sinh câu trả lời.
Với `shared.query_slots` (lượt `cli query-slots`), mọi điều kiện xếp hạng bằng câu tìm kiếm theo chủ đề; ĐK3-q/ĐK4-q (`record: norm_lines`, `query.aliases`) chỉ giữ đơn vị có quy phạm khớp tính quy phạm, trường bắt buộc và chủ thể (`retrieval/norm_query.py`).

`answer_run.py` dùng cùng cách đóng gói của lượt truy xuất (nhóm theo Điều thì prompt `answer-v4.md`); `score` thêm tải kiểm chứng (`cited_tokens_per_statement`, `single_leaf_citation_rate`) và, cho bộ hiệu lực, `stale_citation_rate`.
Không câu nào bị bỏ âm thầm: `score` đếm câu trả lời lỗi (`errors`) và câu trả lời có câu hỏi không nằm trong tệp câu hỏi (`answers_not_in_questions`); `answer_grading.make_sheet` không đưa câu trả lời lỗi vào bảng chấm nhưng ghi chúng vào khóa (`failed`, kèm mã lỗi; `not_in_questions`), và `score_sheet`, `agreement`, `outcome_judge.score` báo `failed_answers` theo điều kiện (null với khóa cũ chưa có trường này).
`outcome_judge.score` gắn nhãn theo thư mục lượt sinh khi hai lượt cùng model và điều kiện nằm chung một bảng (`DK1:<tên thư mục>`), và mỗi cặp so sánh liệt kê câu chỉ một bên có (`unpaired`).
`preflight.py` kiểm thêm ĐK2-ĐK4 cùng `context_packing`, cùng `query_slots`, ĐK3/ĐK4 cùng khối `query`, `validity`, và các điều kiện có lọc hiệu lực cùng ngày mặc định, cùng cạnh sửa đổi và phiên bản trạng thái.
`budget_report.py` (`cli budget-report`): bảng và hình SVG recall theo ngân sách từ `metrics.json` của các lượt đã chạy.

`stats.py` (`paired-stats-v1`, `cli paired-stats`): so sánh ghép cặp theo câu hỏi giữa các lượt có nhãn cho bảng B6 và mức nhiễu cho bảng B7 (nguyên tắc 6 và 7 của kế hoạch nghiên cứu).
Chênh lệch là lượt sau trừ lượt trước trên từng câu cả hai lượt đều có giá trị; bootstrap ghép cặp lấy mẫu lại các chênh lệch 10.000 lần (`--rounds`) với hạt giống dạng chuỗi (`--seed`, ghi vào báo cáo), khởi tạo lại cho từng so sánh.
Báo cáo có chênh lệch trung bình, khoảng tin cậy 95% theo phân vị, số thắng/thua/hòa và p hai phía: tỉ lệ trung bình lấy mẫu lại, sau khi dời về giả thuyết không chênh lệch, cách 0 ít nhất bằng chênh lệch quan sát, tính bằng (1 + số lần) / (1 + số vòng).
Hiệu chỉnh Holm áp cho họ so sánh khai báo bằng `--pairs` (mặc định ĐK1:ĐK2, ĐK2:ĐK3, ĐK3:ĐK4, ĐK1:ĐK4, viết `DK1:DK2`); `--exploratory` là so sánh thăm dò, chỉ có p thô.
`--repeat DK1=<dir>` là lượt sinh thứ hai của cùng điều kiện (nhiễu sinh); `--regrade` là lượt chấm thứ hai trên cùng câu trả lời (nhiễu giám khảo): một lượt `answer-outcome-judge` khác cho `judge.*`, hoặc một bảng đã chấm khác cùng khóa cho `grades.*`.
Nhiễu được báo theo từng nhãn và gộp mọi nhãn: chênh lệch ghép cặp kèm khoảng tin cậy, trung bình trị tuyệt đối chênh lệch từng câu, số câu đổi giá trị; bảng in ra đặt nhiễu sinh cạnh mỗi chênh lệch giữa hai điều kiện.
Tên chỉ số mang nguồn dữ liệu, không tính lại trong CLI: `retrieval.<tên>` đọc `predictions.jsonl` (`recall@K`, `complete@K`, `context_tokens@K`, `recall_at_tokens@B`, `complete_at_tokens@B`, `stale_context_at_tokens@B`, `recall_at_adaptive`), `answer.<tên>` dùng `answer_run.question_scores` (cần `--questions`), `grades.<tên>` dùng `answer_grading.item_scores` (cần `--sheet`, `--key`), `judge.<tên>` dùng `outcome_judge.item_scores` (cần thêm `--judge`).
Câu có ở lượt này mà thiếu, không chấm được (câu trả lời lỗi, mục chưa chấm) hoặc không có giá trị ở lượt kia được liệt kê trong báo cáo và in thành cảnh báo, không bị bỏ âm thầm; câu mà chỉ số không áp dụng ở cả hai lượt (ví dụ recall của câu cần từ chối) được đếm riêng.
Chỉ số mức câu của câu phát biểu (`grounding_full`, `cited_tokens_per_statement`...) là tỉ lệ của riêng câu đó, nên trung bình theo câu khác số gộp mọi phát biểu của `score_sheet` và `answer_run.score`.
Lệnh chỉ đọc các lượt và ghi báo cáo JSON vào một tệp mới (không ghi đè):

```powershell
$env:PYTHONPATH = 'src'
python -m legal_ai.cli paired-stats --metric judge.correctness --runs DK1=<answers-dk1> DK2=<answers-dk2> DK3=<answers-dk3> DK4=<answers-dk4> --sheet <judge>/sheet.csv --key <judge>/key.json --judge <judge>/sonnet --repeat DK1=<answers-dk1-lan2> --output docs/results/<moi>.json
python -m legal_ai.cli paired-stats --metric retrieval.recall_at_tokens@3000 --runs DK1=<run-dk1> DK2=<run-dk2> DK3=<run-dk3> DK4=<run-dk4> --output <moi>.json
```

Chưa có: chấm grounding và correctness tự động (do người chấm theo `answer_sheet`).
