# So sánh ĐK1-ĐK4 qua ba lớp đo (chạy thử, 10/11/2026)

Mục tiêu: kiểm tra từng cặp ĐK2 so với ĐK1, ĐK3 so với ĐK2, ĐK4 so với ĐK3, và báo cáo cả những cặp không đạt.
Đây là chạy thử trên tập dev: nhãn đáp án do model đề xuất, chưa có người duyệt; giám khảo là Sonnet 5.5, chưa đối chiếu với người chấm.
Mọi khác biệt là trung bình theo cặp câu hỏi, kèm khoảng tin cậy bootstrap 95% (5.000 lần, hạt giống cố định) và số câu thắng/thua.

## Thiết lập

Corpus v2 (`experiment-scope-v2-ve5261858b8f3`, 9 văn bản, 711 Điều), truy xuất hybrid BM25 + BGE-M3, cùng 3.000 token ngữ cảnh cho model sinh ở mọi ĐK.
ĐK3/ĐK4 là thiết kế chính: bản ghi ĐK2 cộng một dòng cấu trúc cho mỗi quy phạm (`claims_view: compact`), mở rộng theo dẫn chiếu hai chiều; KB tách bằng gpt-oss-120b (`kb-scope-v2-gpt-oss-120b`).
Ba bộ câu hỏi:

- Bộ tình huống v1: 44 câu từ vụ việc thật, có tách vấn đề dùng chung (`decompose-v1`); câu trả lời của gpt-oss-120b (9Router, đã chạy 09/11) và Claude Haiku 5.5.
- Bộ xung đột v1 (mới): 25 câu cần kết hợp 2-4 văn bản chồng chéo, chi tiết hóa, ngoại lệ, sửa đổi hoặc chế tài (`experiments/question-drafts-conflict-v1`, 5 loại × 5 câu, Claude soạn); không tách vấn đề; câu trả lời của Haiku.
- Thí nghiệm cài lỗi (mới): KB có 125 lỗi nhìn thấy được trong dòng quy phạm (chủ thể bịa 74, đảo tính quy phạm 45, đổi số 6) trên mọi quy phạm của đơn vị đáp án bộ tình huống (`cli kb-plant`); ĐK4 là bộ kiểm chứng chạy trên ĐK3 đó.

Giám khảo mới `judge-v2.md` (`cli answer-outcome-judge`) chấm mù, không thấy ĐK: mỗi phát biểu (có căn cứ, trích dẫn đúng, sai luật), mỗi vấn đề pháp lý (0/1/2), kết luận so với cách tòa hoặc kết luận chuẩn giải quyết (0/1/2), độ đúng (0/1/2).
Lượt gọi: Sonnet chấm 351 + 88 + 100 + 138 mục và tách quan hệ 711 Điều; Haiku trả lời 88 + 100 + 138 câu (tổng 1.714 lượt qua Claude Code).

## Kết quả

### ĐK2 so với ĐK1: đạt về truy vết, không khác về độ đúng

Độ chính xác trích dẫn theo ký tự (phần chữ được trích dẫn nằm trong đơn vị đáp án):

| Bộ, model | ĐK1 | ĐK2 | Chênh [KTC 95%] | Thắng/thua |
|---|---|---|---|---|
| Tình huống, gpt-oss | 0,134 | 0,343 | +0,209 [+0,149; +0,275] | 36/6 |
| Tình huống, Haiku | 0,092 | 0,244 | +0,152 [+0,113; +0,194] | 39/3 |
| Xung đột, Haiku | 0,131 | 0,315 | +0,210 [+0,140; +0,293] | 22/1 |

Giám khảo không thấy khác biệt về độ đúng hay kết luận (tình huống: Haiku +0,03 [-0,03; +0,11], gpt-oss +0,01 [-0,07; +0,09]; xung đột: +0,02 [-0,10; +0,14]).
Ở cùng ngân sách token, truy xuất ĐK2 ngang ĐK1; ở cùng K thì ĐK1 phủ nhiều hơn vì mỗi đoạn 384 token chạm nhiều đơn vị.
Kết luận: ĐK2 cho cùng chất lượng câu trả lời nhưng căn cứ trích dẫn chính xác gấp 2,5-3 lần, khớp yêu cầu truy vết của đề tài.

### ĐK3 so với ĐK2: không nhất quán, chưa chứng minh được

| Chỉ số | Tình huống, Haiku | Tình huống, gpt-oss | Xung đột, Haiku |
|---|---|---|---|
| Độ đúng | -0,080 [-0,14; -0,03] | -0,057 [-0,12; +0,01] | -0,020 [-0,08; +0,04] |
| Khớp kết luận | -0,045 [-0,11; +0,02] | -0,011 [-0,10; +0,08] | +0,020 [-0,04; +0,08] |
| Vấn đề giải quyết được | -0,026 [-0,07; +0,02] | -0,007 [-0,06; +0,04] | +0,085 [+0,03; +0,14], 13/2 |
| Trích dẫn theo ký tự | -0,021 [-0,056; +0,012] | +0,012 [-0,063; +0,086] | +0,011 [-0,064; +0,079] |

Truy xuất: bộ tình huống R@5 +0,048 [+0,004; +0,092]; bộ xung đột R@1.000 token -0,088 [-0,152; -0,022].
ĐK3 chỉ hơn rõ ở số vấn đề giải quyết được trên bộ xung đột, một phần nhờ mở rộng đồ thị đưa thêm đơn vị đáp án vào ngữ cảnh (8 khối trên bộ xung đột, 24 khối trên bộ tình huống); trên bộ tình huống với Haiku thì độ đúng còn thấp hơn ĐK2.

### ĐK4 so với ĐK3: bộ kiểm chứng làm sạch KB, nhưng chưa thấy lợi ích ở câu trả lời

- Bộ kiểm chứng loại 122/125 lỗi cài khỏi ĐK4 (chủ thể bịa 74/74, đổi số 6/6, đảo tính quy phạm 42/45); số câu có lỗi cài trong ngữ cảnh giảm từ 43/44 (ĐK3) xuống 5/44 (ĐK4).
- Nhưng lỗi không lan sang câu trả lời: Haiku không lặp lại chủ thể bịa hay số bị đổi lần nào, và độ đúng của ĐK3 khi có lỗi cài bằng khi sạch (+0,000 [-0,068; +0,068]); model sinh dựa vào nguyên văn in ngay trên dòng quy phạm.
- Loại quy phạm khỏi đơn vị đáp án làm giảm truy xuất của ĐK4 (R@5 -0,048 [-0,080; -0,023] so với ĐK4 sạch), vì dòng quy phạm đúng vẫn giúp khớp từ khóa.
- Dữ liệu tự nhiên: bộ kiểm chứng chỉ loại khoảng 5% quy phạm (3.631 còn 3.451); trích dẫn theo ký tự với Haiku nhích lên +0,039 [+0,017; +0,063] trên bộ tình huống, +0,051 [-0,009; +0,127] trên bộ xung đột, gpt-oss +0,013 [-0,055; +0,091]; độ đúng trên bộ xung đột +0,04 [0,00; +0,10] với 2/0 câu thắng/thua, nằm trong mức dao động của việc sinh lại (cùng ngữ cảnh gần như trùng, ĐK3 sạch so với ĐK3 cài lỗi dao động ±0,07).

### ĐK3/ĐK4 có đồ thị quan hệ giữa các Điều (Sonnet), và mức nhiễu

Sau khi có kết quả trên, người dùng chọn hoàn tất đồ thị quan hệ có kiểu giữa các Điều (`relation-run-v1`, thiết kế từ 09/11): Claude Sonnet 5.5 qua Claude Code chạy đủ 711 Điều (711 lượt, 0 lỗi), 2.130 quan hệ được chấp nhận (điều kiện 716, chi tiết 633, thủ tục 401, hệ quả 284, ngoại lệ 96), cấu hình `configs/experiments/corpus-v2/dk{3,4}-relation-sonnet.json`.
Lựa chọn dùng biến thể này được đưa ra sau khi đã thấy kết quả của thiết kế chính, nên chỉ là thăm dò.

- Truy xuất: bộ xung đột R@5 so với ĐK3 không đồ thị quan hệ +0,040 [-0,026; +0,108]; bộ tình huống R@2.000 token -0,035 [-0,078; +0,009].
- Câu trả lời (Haiku, Sonnet chấm), ĐK3 có quan hệ so với ĐK2: bộ tình huống độ đúng -0,068 [-0,12; -0,02]; bộ xung đột độ đúng +0,060 [-0,06; +0,18], vấn đề giải quyết được +0,063 [-0,00; +0,13].
- ĐK4 so với ĐK3 khi cùng có quan hệ, ngữ cảnh gần như trùng nhau (R@5 bằng nhau trên cả hai bộ): bộ tình huống độ đúng +0,068 [+0,01; +0,14], bộ xung đột -0,100 [-0,18; -0,02].

Hai chênh lệch cuối ngược chiều nhau dù ngữ cảnh gần như không đổi, nên chúng chủ yếu là dao động của việc sinh câu trả lời (không đặt được seed) và của giám khảo.
Với 25-44 câu, chênh lệch độ đúng cỡ 0,05-0,10 giữa ĐK3 và ĐK4, và phần lớn các chênh lệch ĐK3 so với ĐK2, nằm trong mức nhiễu này, kể cả khi một khoảng tin cậy đơn lẻ không chứa 0.
Chênh lệch trích dẫn theo ký tự ĐK2 so với ĐK1 (+0,15 đến +0,21, 36/6, 39/3, 22/1) lớn hơn hẳn mức nhiễu.

### Điểm theo điều kiện (giám khảo Sonnet, thang 0-1)

| Bộ, model | Chỉ số | ĐK1 | ĐK2 | ĐK3 | ĐK4 |
|---|---|---|---|---|---|
| Tình huống, Haiku | Độ đúng | 0,386 | 0,420 | 0,341 | 0,352 |
| Tình huống, Haiku | Khớp kết luận | 0,352 | 0,398 | 0,352 | 0,330 |
| Tình huống, gpt-oss | Độ đúng | 0,352 | 0,364 | 0,307 | 0,337 |
| Xung đột, Haiku | Độ đúng | 0,420 | 0,440 | 0,420 | 0,460 |
| Xung đột, Haiku | Khớp kết luận | 0,420 | 0,480 | 0,500 | 0,540 |
| Xung đột, Haiku | Vấn đề giải quyết được | 0,513 | 0,453 | 0,538 | 0,548 |

Không câu trả lời nào được giám khảo chấm độ đúng 2 trên bộ tình huống; điểm thấp ở mọi ĐK cho thấy giới hạn chung (corpus thiếu văn bản tòa đã dùng, nhãn đáp án chưa đủ), không riêng một ĐK.

## Nhận định

- ĐK2 > ĐK1 đứng vững ở chỉ số truy vết trên cả ba bộ và hai model; không có bằng chứng ĐK2 trả lời đúng hơn.
- ĐK3 > ĐK2 và ĐK4 > ĐK3 chưa chứng minh được với các chỉ số chất lượng câu trả lời; xu hướng ĐK1 < ĐK2 < ĐK3 < ĐK4 chỉ xuất hiện ở điểm khớp kết luận trên bộ xung đột (25 câu, chưa có ý nghĩa thống kê theo từng cặp).
- Lý do chính rút ra từ thí nghiệm cài lỗi: với thiết kế "nguyên văn + dòng quy phạm", model sinh gần như bỏ qua dòng quy phạm, nên cả lợi ích (ĐK3) lẫn phần làm sạch (ĐK4) khó tác động tới câu trả lời. Giá trị của ĐK4 hiện đo được ở tầng KB (RQ2: chặn lỗi trước khi vào KB, đồ thị và giao diện duyệt), không ở tầng câu trả lời.
- Thêm đồ thị quan hệ giữa các Điều không đổi kết luận.
- Không nên điều chỉnh thiết kế ĐK3/ĐK4 dựa trên chính các kết quả này rồi báo cáo trên cùng bộ câu; mọi thay đổi phải chốt trên dev và đo lại trên held-out có nhãn người.
- Để phát hiện chênh lệch cỡ 0,05 cần nhiều câu hơn (khoảng 150-200 câu cho mỗi so sánh), và nên sinh câu trả lời hai lần mỗi câu để tách nhiễu sinh khỏi khác biệt giữa các ĐK.

## Giới hạn

Nhãn đáp án, vấn đề và kết luận chuẩn do model soạn, chưa có người duyệt; giám khảo là một model, chưa đo đồng thuận với người; 25-44 câu mỗi bộ nên khác biệt nhỏ hơn khoảng 0,05-0,10 khó phát hiện; nhiều phép so sánh nên một vài khoảng tin cậy không chứa 0 có thể do ngẫu nhiên; model sinh không đặt được seed nên lưu toàn bộ đầu ra để tái lập.

## Tệp và lệnh

- Bộ tình huống: `experiments/runs/dryrun-cases-v1/` (`judge-v2/`, `judge-planted/`, `answers-haiku-dk3-planted`, `answers-haiku-dk4-planted`, `hybrid-dec-dk*-planted`, `questions-outcome.json`).
- Bộ xung đột: `experiments/runs/dryrun-conflict-v1/` (`questions.json`, `hybrid-dk*`, `answers-haiku-dk*`, `judge-v2/`, `run.sh`, `run-answers.sh`).
- KB cài lỗi: `experiments/runs/kb-scope-v2-gpt-oss-120b-planted-cases/` (`planted.jsonl`), cấu hình `configs/experiments/corpus-v2/dk{3,4}-compact-planted.json`.
- Đồ thị quan hệ: `experiments/runs/relations-v2-sonnet/`; truy xuất `hybrid-dec-dk*-relsonnet`, `hybrid-dk*-relsonnet`; câu trả lời `answers-haiku-dk*-relsonnet`; chấm `judge-relsonnet/` ở cả hai bộ; `experiments/runs/run-relsonnet.sh`.
- Lệnh mới: `cli kb-plant`, `cli answer-outcome-judge`, `cli answer-outcome-score`; prompt `prompts/judge-v2.md`.
