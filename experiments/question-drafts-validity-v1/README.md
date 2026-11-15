# Bộ câu hỏi hiệu lực v1 (nháp do model soạn, 15/11/2026)

Bộ này do model soạn: Claude Opus 5.5, chạy trong một phiên agent của Claude Code, ngày 15/11/2026.
Trạng thái: nháp của model, chưa có người duyệt (`annotation_status: model_draft`, khối `drafted_by` trong từng câu).
Không được báo cáo bộ này như nhãn người; hai người gán nhãn phải đối chiếu từng dòng của bảng kiểm trước khi dùng cho số liệu chính.

## Mục đích

Bộ câu thực hiện mục 4.5 của kế hoạch nghiên cứu (`docs/planning/research-plan-2026-11-11.md`): đo tỉ lệ ngữ cảnh và trích dẫn chứa đơn vị lỗi thời (H3) và recall đơn vị đúng phiên bản.
Mỗi câu có ngày áp dụng (`as_of`), tập đơn vị đáp án tại ngày đó (`relevant_unit_ids`) và tập đơn vị lỗi thời (`stale_unit_ids`).
Hai tập này suy ra từ ngày hiệu lực vbpl.vn báo cho từng văn bản và từ cạnh sửa đổi, không từ nhận định pháp lý.
Từ 16/11/2026 bộ dùng cạnh `amendment-rules-v2` (`data/kb/amendments-scope-v3-v48feefc6d53b-v2`) và trạng thái `unit-status-v2` (trạng thái theo từng đơn vị); dựng lại với quy tắc mới, không câu nào đổi tập đáp án, tập lỗi thời hay tập chưa có hiệu lực.

## Tệp

| Tệp | Nội dung |
|---|---|
| `pairs.py` | Sinh tất định hai tệp cặp ứng viên từ corpus v3 đã khóa và cạnh sửa đổi |
| `pairs-expired.jsonl` | 428 cặp đơn vị NĐ 12/2022 và NĐ 283/2026 có lời văn giống nhau (326 cặp giống hệt), ghép theo tên Điều rồi theo độ giống chữ |
| `pairs-amended.jsonl` | 34 cặp (đơn vị bị sửa, đơn vị chứa lời văn mới) từ các cạnh `modify` và `replace_phrase` đã giải được của `amendment-rules-v2`; 25 cặp có ghi chú về NĐ 219/2025 |
| `drafts.json` | Câu hỏi do model soạn, kèm cặp đơn vị, trích dẫn nguyên văn và lý do |
| `build.py` | Tạo `questions.json` và `check-sheet.csv` từ `drafts.json`, chạy toàn bộ kiểm tra trước khi ghi |
| `validate.py` | Bộ kiểm tra tự động, chạy lại được bất cứ lúc nào; trả mã lỗi 1 nếu có lỗi |
| `questions.json` | Tệp câu hỏi đúng định dạng `run-retrieval` và `answer-run` đọc |
| `check-sheet.csv` | Bảng kiểm cho hai người: mỗi dòng một cặp (câu, đơn vị), 84 dòng |
| `unit.py` | In nguyên văn một đơn vị của corpus v3, liệt kê đơn vị con, hoặc tìm đơn vị chứa một chuỗi |

Chạy lại từ thư mục gốc của kho:

```powershell
.venv\Scripts\python experiments/question-drafts-validity-v1/pairs.py
.venv\Scripts\python experiments/question-drafts-validity-v1/build.py
.venv\Scripts\python experiments/question-drafts-validity-v1/validate.py
```

## Số câu theo nhóm

| Nhóm (`group`) | Số câu | Ngày áp dụng | Đáp án | Lỗi thời |
|---|---|---|---|---|
| `expired_document`: chế tài có căn cứ ở cả NĐ 12/2022 và NĐ 283/2026 | 10 | 2026-11-11 | Đơn vị NĐ 283/2026 | Đơn vị tương ứng của NĐ 12/2022 (hết hiệu lực từ 2026-09-10 theo vbpl.vn) |
| `unit_amendment`: khoản đã bị sửa và khoản sửa | 10 | 2026-11-11 (8 câu), năm 2024 (2 câu) | Đơn vị chứa lời văn mới | Đơn vị bị sửa |
| `past_date`: câu ghi rõ ngày xảy ra việc | 5 | Ngày nêu trong câu (2022-2025) | Đơn vị có hiệu lực ở ngày đó | Rỗng ở 4 câu, một đơn vị ở hl-c04 |
| `control`: không liên quan tới thay đổi hiệu lực | 5 | 2026-11-11 | Đơn vị Bộ luật Lao động | Rỗng |

Không nhóm nào thiếu câu so với kế hoạch.
Nhóm `expired_document` có 10 cặp an toàn: mỗi cặp có một cụm chữ chung được trích nguyên văn từ cả hai đơn vị, và với điểm chỉ ghi mức phạt theo số người thì câu dẫn của khoản chứa hành vi cũng được trích từ cả hai nghị định.
Tám cặp lấy từ `pairs-expired.jsonl`; hai cặp ghép tay (hl-a02 thử việc, hl-a05 chậm đóng bảo hiểm xã hội) vì lời văn đổi nhiều, và cặp khoản 1 Điều 6 NĐ 12/2022 với khoản 1 Điều 7 NĐ 283/2026 (tổ chức bị phạt gấp đôi cá nhân) cũng ghép tay vì hai Điều thuộc Chương I, ngoài phạm vi ghép tự động.
Nhóm `unit_amendment` dùng 10 trong 34 cặp của `pairs-amended.jsonl`: 6 cặp Luật BHXH 2024 sửa Luật ATVSLĐ 2015 và 4 cặp NĐ 70/2023 sửa NĐ 152/2020.

## Định dạng của một câu

Trường pipeline đọc: `question_id`, `question`, `question_type` (`temporal` cho ba nhóm hiệu lực, `lookup` cho nhóm đối chứng), `family_id` (mỗi câu một nhóm), `expected_status` (`answer`), `as_of`, `relevant_unit_ids`, `stale_unit_ids`.
Trường `not_yet_effective_unit_ids` (đơn vị của văn bản sau, chưa có hiệu lực ở ngày áp dụng) cũng được pipeline đọc: `run-retrieval` báo `wrong_version_context_rate_at_tokens` và `answer-score` báo `wrong_version_citation_rate` (đơn vị lỗi thời hoặc chưa có hiệu lực), là chỉ số bổ sung; chỉ số chính của H3 vẫn chỉ tính đơn vị lỗi thời.
Trường thêm cho người kiểm: `group`, `pairs` (cặp NĐ 12/2022 và NĐ 283/2026 kèm cụm chữ chung `shared` và câu dẫn `context`), `amendments` (cặp đơn vị bị sửa và đơn vị sửa), `quotes` (trích nguyên văn), `rationale`, `annotation_status`, `drafted_by`.
Chưa chia dev/held-out: việc chia làm khi khóa bộ trong app, theo quy tắc của các bộ khác.

## Kiểm tra tự động (`validate.py`, kết quả: đạt, 0 lỗi)

- Mã câu không trùng; nhóm, loại câu (`QUESTION_TYPES` của app) và hành vi mong đợi hợp lệ; mọi câu có `as_of` đúng dạng ngày; mọi câu có ít nhất một đơn vị đáp án; không đơn vị nào vừa là đáp án vừa lỗi thời.
- Mọi mã đơn vị có trong bundle v3 `data/normalized/experiment-scope-v3-v48feefc6d53b`.
- Mọi trích dẫn là chuỗi con chính xác của đơn vị của nó; cụm chữ chung của một cặp có trong cả hai đơn vị (so không phân biệt hoa thường); câu dẫn là của chính đơn vị trong cặp hoặc đơn vị cha của nó.
- Tập lỗi thời của mỗi câu đúng bằng các đơn vị được liệt kê (đáp án và lỗi thời) mà `kb/validity.py` (`unit-status-v2`) báo là hết hiệu lực, bị bãi bỏ hoặc đã sửa đổi tại `as_of`; mọi đơn vị đáp án còn hiệu lực; mọi đơn vị ở `not_yet_effective_unit_ids` chưa có hiệu lực.
- Cặp không ghép tay phải có trong `pairs-expired.jsonl`; mỗi cặp sửa đổi phải là một cạnh đã giải được với đúng đơn vị bị sửa và đơn vị sửa, và ngày hiệu lực của cạnh khớp vai trò của hai đơn vị.
- Cặp thuộc phần lao động nước ngoài của NĐ 152/2020 phải có ngày áp dụng trước 2025-08-07.
- Câu đối chứng không có đơn vị lỗi thời, không có đơn vị chưa có hiệu lực, không có cặp; mọi câu khác có ít nhất một đơn vị lỗi thời hoặc chưa có hiệu lực.

## Cách kiểm cho hai người (`check-sheet.csv`)

Mỗi người chép bảng thành tệp riêng và làm độc lập; tệp là UTF-8 có BOM nên Excel hiển thị đúng tiếng Việt.
Mỗi dòng là một đơn vị của một câu, với vai trò `đáp án`, `lỗi thời` hoặc `chưa có hiệu lực`.
Cột `reason` nêu căn cứ máy dùng: ngày hiệu lực vbpl.vn báo, hoặc câu lệnh sửa đổi kèm ngày hiệu lực.
Cột `quotes` là các đoạn nguyên văn; cột `context` là tên Điều và câu dẫn của khoản chứa đơn vị; cột `unit_text` là nguyên văn đơn vị.
Người kiểm chỉ so chữ và ngày, không cần nhận định pháp lý:

1. Dòng `lỗi thời` của nhóm `expired_document`: so cụm chữ chung và câu dẫn ở cột `quotes` với `unit_text` và `context` của cả hai đơn vị trong cặp; hai đơn vị phải mô tả cùng một hành vi.
2. Dòng `lỗi thời` của nhóm `unit_amendment`: mở đơn vị sửa (dòng `đáp án` của cùng câu) và kiểm câu lệnh "Sửa đổi, bổ sung ..." trong đó nêu đúng số khoản, số điểm, số Điều của đơn vị lỗi thời.
3. Dòng `đáp án`: kiểm `unit_text` (cùng `context`) có chứa thông tin câu hỏi hỏi không, ví dụ mức phạt, thời hạn, điều được dẫn chiếu.
4. Dòng `chưa có hiệu lực`: kiểm ngày ở cột `reason` muộn hơn `as_of`.
5. Ghi `co` hoặc `khong` vào `annotator_agrees`; khi ghi `khong`, nêu lý do ngắn ở `annotator_note`.

## Giới hạn

1. Câu hỏi, đơn vị đáp án và lý do do model soạn; chỉ phần cơ học (mã đơn vị, trích dẫn, trạng thái theo ngày) được kiểm tự động.
2. Ngày hiệu lực là điều vbpl.vn báo tại ngày truy cập (07/11 và 11/11/2026), không phải xác nhận của nhóm.
3. Khoản 2 Điều 35 NĐ 219/2025 viết: "Nội dung về lao động nước ngoài làm việc tại Việt Nam quy định tại Nghị định số 152/2020/NĐ-CP ... được sửa đổi, bổ sung tại Nghị định số 70/2023/NĐ-CP ... hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực" (hiệu lực từ 07/08/2025), trong khi vbpl.vn báo NĐ 152/2020 hết hiệu lực từ 15/11/2026; quy tắc chỉ ghi câu này thành một cạnh `expire_subject` chưa giải quyết (xem `experiments/amendment-check-v3/README.md`), và `unit-status-v2` không áp dụng nó.
   Vì vậy các câu về phần lao động nước ngoài của NĐ 152/2020 (hl-b09, hl-b10, hl-c03, hl-c04) đặt ngày áp dụng trước 07/08/2025; hl-b07 và hl-b08 (Chương III, người lao động Việt Nam) dùng 2026-11-11 và phụ thuộc vào ngày 15/11/2026 vbpl.vn báo.
4. Đơn vị chưa có hiệu lực không phải đơn vị lỗi thời, nên 4 câu nhóm `past_date` có tập lỗi thời rỗng và không góp vào tỉ lệ ngữ cảnh lỗi thời (chỉ số chính, khai báo trước).
   Việc đưa văn bản ra đời sau ngày xảy ra việc vào ngữ cảnh hoặc trích dẫn vẫn là sai phiên bản, nên được đo riêng bằng chỉ số bổ sung "sai phiên bản" (đơn vị lỗi thời hoặc chưa có hiệu lực, 25 câu có tập này).
5. Khoản 1 Điều 67 NĐ 283/2026 cho áp dụng nghị định có hiệu lực tại thời điểm thực hiện hành vi với vi phạm đã kết thúc trước 10/09/2026; `as_of` chỉ mô hình một ngày, nên hl-c01 và hl-c02 đặt ngày phát hiện và xử phạt trùng ngày xảy ra việc để tránh câu phụ thuộc quy định chuyển tiếp.
6. Bộ được soạn với `unit-status-v1`, khi một khoản có điểm con bị sửa bị coi là đã sửa đổi; vì vậy hl-b05 không có câu dẫn của khoản 2 Điều 44 và hl-b08 không hỏi thời hạn báo cáo nằm ở câu dẫn của khoản 4 Điều 27.
   Với `unit-status-v2` hai câu dẫn này còn hiệu lực; hai câu hỏi được giữ nguyên vì tập đáp án tối thiểu của chúng không đổi.
7. Câu hỏi về doanh nghiệp có thêm quy tắc tổ chức bị phạt gấp đôi (khoản 1 Điều 7 NĐ 283/2026 là đáp án, khoản 1 Điều 6 NĐ 12/2022 là lỗi thời); các đơn vị này lặp lại ở 10 câu nhóm `expired_document` và 2 câu nhóm `past_date`.
8. Tập đáp án là căn cứ tối thiểu cho điều câu hỏi hỏi, không phải mọi quy định liên quan; ví dụ biện pháp khắc phục hậu quả không được đưa vào.
9. Ở 8 trong 10 câu nhóm `expired_document`, lời văn của hai nghị định giống nhau (hl-a07 chỉ khác ký hiệu điểm): các câu này đo việc trích đúng văn bản còn hiệu lực, không đo việc nêu đúng mức phạt mới; chỉ hl-a02 và hl-a05 có lời văn đổi.
10. Câu hỏi "hiện nay" dùng ngày áp dụng 2026-11-11, ngày khóa corpus v3; ngày mặc định cho câu không ghi `as_of` vẫn là câu hỏi mở của nhóm, và bộ này không phụ thuộc vào lựa chọn đó.

## Chạy thử truy xuất (kiểm tra công cụ, không phải kết quả)

Chạy lại ngày 16/11/2026 bằng BM25 trên corpus v3 sau khi sửa lỗi đóng gói P2 và chuyển sang `amendment-rules-v2`, `unit-status-v2`; thư mục `experiments/runs/validity-dryrun-2026-11-16/` (ngoài Git), cấu hình chung `shared-bm25.json` (ĐK2 đóng gói P2 như quyết định 11/11, ĐK1 luôn P0, ngày mặc định 2026-11-11).
Lượt ngày 15/11 ở `experiments/runs/validity-dryrun-2026-11-15/` giữ nguyên để so.
Không dùng hybrid vì cần tính vector cho câu hỏi và cho các đoạn mới của corpus v3, việc này ghi thêm vào bộ đệm vector dùng chung.
Số liệu dưới đây đo trên nhãn nháp của model, chỉ để kiểm công cụ chạy đúng, không được báo cáo như kết quả.

| Điều kiện | Ngữ cảnh có đơn vị lỗi thời (500 / 1.000 / 3.000 token, 21 câu) | Ngữ cảnh có đơn vị sai phiên bản (25 câu) | Recall đơn vị đúng phiên bản (30 câu) |
|---|---|---|---|
| ĐK1-hl (`validity/dk1-hl.json`, lọc theo văn bản) | 0,38 / 0,43 / 0,52 | 0,32 / 0,36 / 0,44 | 0,51 / 0,59 / 0,71 |
| ĐK2 lọc hiệu lực (`validity/dk2.json`, P2) | 0,00 / 0,00 / 0,00 | 0,00 / 0,00 / 0,00 | 0,50 / 0,60 / 0,68 |
| ĐK2 lọc hiệu lực, đóng gói P0 (đối chứng) | 0,00 / 0,00 / 0,00 | 0,00 / 0,00 / 0,00 | 0,55 / 0,63 / 0,68 |
| ĐK1-128 không lọc (`dk1-128.json`) | 0,62 / 0,62 / 0,81 | 0,60 / 0,60 / 0,80 | 0,47 / 0,52 / 0,64 |
| ĐK2 không lọc (`dk2.json`, P2) | 0,48 / 0,52 / 0,71 | 0,48 / 0,52 / 0,72 | 0,32 / 0,44 / 0,59 |

Ngày 15/11, ĐK2 lọc hiệu lực với P2 còn tỉ lệ 0,10 / 0,14 / 0,14 vì `indexing/packing.py` thêm Khoản, Điểm anh em mà không qua bộ lọc hiệu lực.
Từ 16/11, mỗi đơn vị anh em đi qua cùng quy tắc với đơn vị được xếp hạng (`kb.validity.RecordFilter`): bị loại, kèm ghi chú, hoặc được thay bằng đơn vị chứa lời văn mới; ở mọi ngân sách (250 đến 6.000 token) tỉ lệ ngữ cảnh lỗi thời của ĐK2 lọc hiệu lực với P2 bằng 0.
