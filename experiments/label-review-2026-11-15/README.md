# Rà soát nhãn bằng model trên corpus v3 (15/11/2026)

Đây là nhãn **model rà soát**, không phải nhãn người và không phải kết luận pháp lý đã kiểm chứng.
Ba agent Claude (Opus 5.5 qua Claude Code) đối chiếu từng đơn vị của nhãn 12/11 (`experiments/label-review-2026-11-12/`) với nguyên văn corpus v3 đã khóa (`v48feefc6d53b`, 14 văn bản, 7.056 đơn vị) cho ba bộ khó: tình huống, xung đột, phức tạp.
Kết quả được nhập vào app thành **đề xuất của model**; người gán (Vũ, chế độ có xem đề xuất) giữ hoặc sửa từng trường, app ghi lại trường nào giữ, trường nào sửa.
Kha gán độc lập, không xem đề xuất.
Luận văn không được báo cáo các nhãn này như nhãn người.

## Tệp

| Tệp | Nội dung |
|---|---|
| `cases.jsonl`, `conflict.jsonl`, `complex.jsonl` | Kết quả gốc của từng agent: đơn vị giữ, bỏ, thêm (kèm nguyên văn), đơn vị lỗi thời và đơn vị thay thế, ngày áp dụng, độ tin cậy, ghi chú |
| `build-*.py`, `cases_quotes.py` | Mã dựng ba tệp trên |
| `check-*.py` | Bộ kiểm tra của từng bộ (đơn vị có trong v3, trích dẫn đúng nguyên văn, hiệu lực tại ngày áp dụng theo `unit-status-v2` và cạnh `amendment-rules-v2`) |
| `merge.py` | Chạy ba bộ kiểm tra rồi gộp; chạy lại được bất cứ lúc nào |
| `<bộ>-reviewed.json` | Tệp câu hỏi cho pipeline (`run-retrieval`, `answer-run`, `answer-outcome-judge`), `annotation_status: model_review`, khối `model_review` giữ nhãn 12/11, điều đã đổi và lý do |
| `<bộ>-check-sheet.csv` | Bảng kiểm cho người (UTF-8 có BOM, mở được bằng Excel): mỗi dòng một cặp câu và đơn vị, kết luận giữ, thêm, bỏ, lỗi thời, lý do, nguyên văn, tên đơn vị kèm văn bản, hai cột trống để người gán ghi đồng ý hay không |
| `<bộ>-drafts.json` | Tệp nhập cho lệnh `question-drafts` (câu hỏi, loại câu, hành vi mong đợi, đơn vị, lý do ngắn, nhóm diễn đạt) |
| `guideline-2026-11-15.md` | Hướng dẫn gán nhãn ngắn gắn vào ba bộ khi nhập |
| `verify-import.py` | Kiểm tra chỉ đọc sau khi nhập vào store |
| `summary.json` | Số liệu tổng |

## Quy ước đã áp dụng

Theo các dòng ngày 15/11/2026 của `docs/decisions.md`:

1. Câu không ghi ngày được hiểu là hỏi tại ngày khóa corpus v3 (11/11/2026); đáp án là đơn vị còn hiệu lực tại ngày đó.
   Đơn vị của văn bản hết hiệu lực (NĐ 12/2022 từ 10/09/2026) hoặc đã bị sửa, bãi bỏ là lỗi thời; đơn vị thay thế (thường là NĐ 283/2026) vào đáp án, kèm nguyên văn của cả hai đơn vị.
2. Câu có ngày, và câu tình huống có ngày xảy ra việc, theo quy định có hiệu lực tại ngày đó (trường `as_of`).
3. Quy định được nhắc lại ở hai văn bản thì chọn cả hai đơn vị, khi văn bản thứ hai nêu cùng quy tắc.
4. Bộ tình huống loại 9 câu tin cậy thấp (k01, k09, k15, k17, k24, k25, k26, k40, k41), còn 35 câu; nhãn chỉ gồm đơn vị bản án dựa vào; vấn đề tòa không xét bị bỏ khỏi danh sách vấn đề.

Khi gộp, một đơn vị bị bỏ khỏi danh sách nếu đơn vị con của nó cũng có trong danh sách, giống lượt 12/11.
Câu không có ngày được ghi `as_of` là 2026-11-11, đúng bằng `validity_as_of` của `configs/experiments/shared.json`.
13 câu tình huống mà sự việc xảy ra trước khi luật trong corpus có hiệu lực không có `as_of`; pipeline dùng ngày mặc định 2026-11-11, cũng là ngày các đơn vị của chúng được kiểm hiệu lực.

## Số liệu (sau quy ước bỏ đơn vị cha)

| Bộ | Câu | Đơn vị 12/11 | Đơn vị 15/11 | Giữ | Thêm | Bỏ | Lỗi thời | Chưa có hiệu lực | Câu không đổi | Đổi trả lời/từ chối | Tin cậy cao / vừa / thấp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tình huống | 35 (9 câu bị loại) | 192 | 155 | 149 | 6 | 43 | 0 | 2 | 13 | 0 | 2 / 21 / 12 |
| Xung đột | 25 | 156 | 175 | 144 | 31 | 2 | 18 | 0 | 14 | 0 | 19 / 5 / 1 |
| Phức tạp | 30 | 119 | 144 | 111 | 33 | 0 | 8 | 0 | 19 | 0 | 16 / 14 / 0 |

"Giữ" và "Thêm" đếm đơn vị còn lại sau quy ước; ở bộ xung đột 38 đơn vị cha bị bỏ vì đã có đơn vị con.
Số đơn vị 12/11 của bộ tình huống tính cả 9 câu nay bị loại thì là 192; 35 câu còn lại có ít đơn vị hơn chủ yếu vì quy ước chỉ giữ căn cứ bản án dựa vào.

## Chỗ ba lượt rà làm khác nhau và cách gộp

- Cặp đơn vị lỗi thời và đơn vị thay được ghi theo ba cách (`stale_unit_id`/`new_unit_id`, `unit_id`/`replaced_by`, hoặc chỉ trong danh sách bỏ); `merge.py` đưa về một dạng trong khối `model_review.stale_pairs`.
- Ở k02 và k38, đơn vị khoản 4 Điều 13 Luật BHXH 41/2024 được ghi là lỗi thời, nhưng tại ngày sự việc (2023) luật này **chưa có hiệu lực**; nó được đưa vào `not_yet_effective_unit_ids`, trường mà chỉ số trích dẫn sai phiên bản của `answer-run` đọc.
- Nhãn 12/11 được ghi theo ba dạng (danh sách, khối có `relevant_unit_ids`, hoặc không ghi); `merge.py` lấy thống nhất từ `experiments/label-review-2026-11-12/`.
- Ba bộ kiểm tra từng dùng cạnh `amendment-rules-v1`; nay trỏ tới `data/kb/amendments-scope-v3-v48feefc6d53b-v2` và đều đạt với `unit-status-v2`.
  `build-cases.py` vẫn đọc cạnh v1 khi dựng; kết quả của nó qua được bộ kiểm tra v2 nên không cần dựng lại.

## Điểm người gán cần quyết định

Bộ tình huống:

- 13 câu sự việc theo luật cũ (cờ `old_law_case: true`, trường `event_date`): k03 (2019-07-01), k10 (2018-08-01), k16 (2011-08), k18 (2020-08), k20 (2020-05), k21 (2016-02), k22 (2016-11-25), k23 (2013-12), k28 (2016-06), k29 (2020-11-01), k32 (2019-11-12), k36 (2017-10-16), k42 (2017-10-16).
  Đơn vị là quy định tương ứng hiện hành chứ không phải luật tòa áp dụng; nhóm cần quyết định giữ hay loại cả nhóm này (một bộ lọc theo cờ là đủ).
- k00, k04, k07, k14, k20, k31: ghi chú đề nghị mở bản án để quyết định thêm hay bỏ một đơn vị cụ thể (xem cột ghi chú trong bảng kiểm).

Bộ xung đột:

- 5 câu có kết quả tham chiếu cần sửa (`model_review.outcome_issue`, cột `flags` của bảng kiểm): x04 (tên cơ quan nhận thông báo làm thêm giờ: Sở Nội vụ theo NĐ 283/2026 hay Sở Lao động - Thương binh và Xã hội theo NĐ 145/2020), x10, x20, x21 (số hiệu điều NĐ 12/2022 phải đổi sang NĐ 283/2026, con số không đổi), x17 (phải viết lại vì cả hai trường hợp nay có căn cứ phạt trong NĐ 283/2026).
  `reference_outcome` trong tệp được giữ nguyên để người sửa.
- x17 và x22: ngày áp dụng được hiểu là 11/11/2026 vì câu chỉ nói "năm 2026" và "dịp Tết".
  Nếu hiểu là trước 10/09/2026 (Tết tháng 2/2026) thì NĐ 12/2022 còn hiệu lực và nhãn 12/11 đúng; x17 còn cần kiểm việc NĐ 283/2026 gọi "Luật Bảo hiểm xã hội" là Luật 41/2024.

Bộ phức tạp:

- cq24, cq25, cq26 (và x10, x17, x20, x21, x22 của bộ xung đột) dùng cả khoản 1 Điều 7 NĐ 283/2026 (tổ chức bị phạt gấp 02 lần) lẫn điểm b khoản 2 Điều 7 (doanh nghiệp thuộc danh sách tổ chức); cần chọn giữ cả hai hay một.
- cq00, cq08: đơn vị khoản 3 Điều 12 TT 10/2020 (lương tính trợ cấp thôi việc) nằm dưới Điều 12 "Hiệu lực thi hành" theo cách tách của corpus, có thể là lỗi tách Điều; cần đối chiếu bản gốc.
- cq22: ba đơn vị về thời gian tính trợ cấp mất việc làm là đề xuất mới, có thể bỏ nếu cho rằng câu chỉ hỏi mức trợ cấp theo năm.
- cq25 (khoản 2 Điều 90 BLLĐ, khoản 1 Điều 4 NĐ 293/2025) và cq20, cq28 (điểm b, c khoản 2, khoản 3 Điều 70 NĐ 145/2020): có thể thêm, lượt rà không thêm.
- Bộ luật Lao động và NĐ 145/2020 được vbpl.vn ghi "hết hiệu lực một phần" nhưng không có cạnh nào nói phần nào; mọi đơn vị của hai văn bản này được coi là còn hiệu lực.

## Chạy lại

```powershell
.venv\Scripts\python experiments\label-review-2026-11-15\merge.py
```

Kết quả mong đợi: ba dòng `check-...py: ok`, rồi `cases: 35 questions (9 excluded), 155 units ...`, `conflict: 25 questions ... 175 units ...`, `complex: 30 questions ... 144 units ...`.

## Nhập vào máy chủ (vlexora.duckdns.org)

Đã thử toàn bộ các bước dưới trên một bản sao của bản sao lưu `data/kb/vm-lexora-20261115.sqlite`: phiên bản corpus v3 vào đúng mã và mã băm, ba bộ có 35, 25 và 30 câu kèm đề xuất, bộ câu hỏi thực nghiệm v1 (152 câu, 152 nhãn) không đổi.
Chỉ chạy sau khi code mới (có lệnh `corpus-version-import`) đã được cập nhật lên máy chủ theo `docs/deploy-gcp.md`.
Mỗi lệnh `question-drafts` chỉ chạy **một lần**; chạy lại sẽ tạo thêm một bộ trùng.

### Trên máy cá nhân (PowerShell, tại thư mục Lexora)

Bước 1. Ghi phiên bản corpus v3 và các tệp nhập vào một thư mục tạm.

```powershell
$env:PYTHONPATH = 'src'
$D = 'upload\experiments\label-review-2026-11-15'
New-Item -ItemType Directory -Force $D | Out-Null
.venv\Scripts\python -m legal_ai.cli corpus-version-export --store data/kb/research-scope-v3-20261111.sqlite --version v48feefc6d53b --output "$D\corpus-v3-v48feefc6d53b.json"
Copy-Item experiments\label-review-2026-11-15\cases-drafts.json, experiments\label-review-2026-11-15\conflict-drafts.json, experiments\label-review-2026-11-15\complex-drafts.json, experiments\label-review-2026-11-15\guideline-2026-11-15.md, experiments\label-review-2026-11-15\verify-import.py $D
```

Kết quả mong đợi của lệnh export: `"version_id": "v48feefc6d53b"`, `"bundle_sha256": "84932db6a555c7a11fdd9a2c47c40845f84a9dd5316609dbb04fe9b26e70ef8b"`, `"documents": 14`, `"units": 7056`.
Nếu báo `output file exists`, xóa thư mục `upload` rồi làm lại bước 1.

Bước 2. Nén và chép lên máy chủ.

```powershell
tar -czf hardsets.tar.gz -C upload experiments
scp hardsets.tar.gz gcp:lexora/
```

### Trên máy chủ (`ssh gcp`)

Bước 3. Dừng app và sao lưu store (app dừng vài phút, không ai gán nhãn được trong lúc này).

```sh
sudo systemctl stop lexora
cp -p ~/lexora/data/kb/lexora.sqlite ~/lexora/backups/lexora-truoc-bo-kho.sqlite
ls -l ~/lexora/backups/lexora-truoc-bo-kho.sqlite
```

Kết quả mong đợi: một dòng có kích thước tệp, bằng kích thước của `~/lexora/data/kb/lexora.sqlite`.

Bước 4. Giải nén và thêm phiên bản corpus v3 vào store.

```sh
cd ~/lexora/app && tar -xzf ../hardsets.tar.gz
D=experiments/label-review-2026-11-15
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli corpus-version-import $D/corpus-v3-v48feefc6d53b.json --store ~/lexora/data/kb/lexora.sqlite --actor admin --expect-version v48feefc6d53b
```

Kết quả mong đợi: `"version_id": "v48feefc6d53b"`, `"documents": 14`, `"units": 7056`, `"created": true`.
Nếu là `"created": false` thì phiên bản đã có sẵn và giống hệt; cứ tiếp tục.
Thay `admin` bằng tên tài khoản của người chạy nếu khác (chỉ để ghi ai nhập).

Bước 5. Tạo ba bộ câu hỏi kèm đề xuất (mỗi lệnh một lần).

```sh
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli question-drafts $D/cases-drafts.json --store ~/lexora/data/kb/lexora.sqlite --actor admin --author "claude-opus-5-5 (rà soát model 15/11/2026)" --version v48feefc6d53b --name "Bộ tình huống v1 (corpus v3, đề xuất rà soát 15/11)" --guideline $D/guideline-2026-11-15.md
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli question-drafts $D/conflict-drafts.json --store ~/lexora/data/kb/lexora.sqlite --actor admin --author "claude-opus-5-5 (rà soát model 15/11/2026)" --version v48feefc6d53b --name "Bộ xung đột v1 (corpus v3, đề xuất rà soát 15/11)" --guideline $D/guideline-2026-11-15.md
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli question-drafts $D/complex-drafts.json --store ~/lexora/data/kb/lexora.sqlite --actor admin --author "claude-opus-5-5 (rà soát model 15/11/2026)" --version v48feefc6d53b --name "Bộ phức tạp v1 (corpus v3, đề xuất rà soát 15/11)" --guideline $D/guideline-2026-11-15.md
```

Kết quả mong đợi, theo thứ tự: `"added": 35, "families": 31`, rồi `"added": 25, "families": 25`, rồi `"added": 30, "families": 24` (mỗi lần kèm một `set_id` mới).
Nếu một lệnh báo `error:`, dừng lại, không chạy lệnh sau, và gửi nguyên dòng lỗi cho nhóm.

Bước 6. Kiểm tra (chỉ đọc, so với bản sao lưu ở bước 3).

```sh
~/lexora/venv/bin/python $D/verify-import.py --store ~/lexora/data/kb/lexora.sqlite --backup ~/lexora/backups/lexora-truoc-bo-kho.sqlite
```

Kết quả mong đợi ở dòng cuối: `OK: corpus v3 and the three hard sets are in the store; existing data unchanged`.
Phía trên là báo cáo: ba bộ có `"questions"` 35, 25, 30, `"labels": 0`, và `existing_sets_untouched` vẫn có "Bộ câu hỏi thực nghiệm v1" với 152 câu và đúng số nhãn như trước.

Bước 7. Bật lại app.

```sh
sudo systemctl start lexora
sudo systemctl status lexora --no-pager
```

Kết quả mong đợi: dòng `Active: active (running)`.
Mở https://vlexora.duckdns.org, vào Nghiên cứu, mục Bộ câu hỏi: có ba bộ mới gắn với "Phạm vi thực nghiệm v3 (nháp)", phiên bản 1, với 35, 25 và 30 câu.

### Nếu bước 6 báo FAILED

Không bật app ngay; trả store về bản sao lưu rồi mới bật lại, và gửi toàn bộ kết quả của bước 6 cho nhóm.

```sh
cp -p ~/lexora/backups/lexora-truoc-bo-kho.sqlite ~/lexora/data/kb/lexora.sqlite
sudo systemctl start lexora
```
