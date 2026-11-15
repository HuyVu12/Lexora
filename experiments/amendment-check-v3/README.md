# Bảng kiểm cạnh sửa đổi của corpus v3 (tạo lại 16/11/2026)

Bảng này phục vụ việc kiểm tra ở mục 4.2 của kế hoạch nghiên cứu: hai người đối chiếu từng cạnh sửa đổi do quy tắc sinh ra với nguyên văn, rồi luận văn báo cáo số cạnh đúng, sai và chưa giải quyết.
Cột `verdict` và `note` đang trống: chưa ai kiểm, nên không được trình bày bảng này như kết quả đã kiểm.
Bảng ngày 15/11/2026 (68 cạnh, `amendment-rules-v1`) đã được thay bằng bảng này trước khi có ai điền.

## Nguồn

- Cạnh sửa đổi: `data/kb/amendments-scope-v3-v48feefc6d53b-v2/edges.jsonl` (`amendment-rules-v2`, chỉ dùng quy tắc, không gọi model); thư mục cạnh v1 `data/kb/amendments-scope-v3-v48feefc6d53b` giữ nguyên.
- Corpus: `data/normalized/experiment-scope-v3-v48feefc6d53b` (phạm vi thực nghiệm v3, đã khóa ngày 11/11/2026).
- Tổng cộng 100 cạnh: 35 `resolved`, 2 `resolved_parent` (37 cạnh giải được, như v1), 22 `unresolved`, 40 `external`, 1 `document`.
- So với v1: 68 cạnh cũ giữ nguyên đích và trạng thái; mỗi cạnh có thêm phạm vi (`scope`); thêm 32 cạnh "hết hiệu lực" đọc từ Điều "Hiệu lực thi hành" của các văn bản.
- Lệnh tạo bảng (báo lỗi nếu tệp đã có, để không ghi đè bảng đã điền):

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli amendment-build data/normalized/experiment-scope-v3-v48feefc6d53b --config configs/amendments-v1.json --output data/kb/<thư-mục-mới>
.venv\Scripts\python -m legal_ai.cli amendment-sheet data/kb/amendments-scope-v3-v48feefc6d53b-v2 --sheet experiments/amendment-check-v3/check-sheet.csv
```

## Số cạnh theo loại

| Loại (`kind`) | Ý nghĩa | Số cạnh |
|---|---|---|
| `modify` | "Sửa đổi, bổ sung ..." | 33 (22 giải được) |
| `replace_phrase` | "Thay thế cụm từ ..." | 18 (12 giải được) |
| `repeal` | "Bãi bỏ ..." | 11 (1 giải được) |
| `add` | "Bổ sung ..." | 6 (2 nối tới đơn vị cha) |
| `expire` | "... hết hiệu lực" có nêu Điều, khoản | 12 (đều ngoài corpus) |
| `expire_document` | "... hết hiệu lực" cho cả một văn bản | 19 (1 trong corpus: NĐ 12/2022 do NĐ 283/2026 tuyên bố) |
| `expire_subject` | "... hết hiệu lực" theo nội dung, không nêu Điều, khoản | 1 (chưa giải quyết) |

Cột `kind` của bảng ghi thêm phạm vi khi khác thường: "chỉ tên hoặc câu dẫn, không thay các điểm, khoản bên dưới" (một cạnh: "Sửa đổi, bổ sung tên khoản 8 Điều 9" của NĐ 70/2023) và "chỉ đơn vị chứa cụm từ cũ" (các lệnh thay cụm từ).

## Cách làm cho hai người kiểm

1. Mỗi người chép `check-sheet.csv` thành tệp riêng, ví dụ `check-sheet-kha.csv` và `check-sheet-vu.csv`, và làm độc lập, không trao đổi trước khi xong.
2. Mở tệp bằng Excel hoặc LibreOffice (tệp là UTF-8 có BOM nên tiếng Việt hiển thị đúng); không sửa, xóa hay sắp xếp lại các cột khác ngoài `verdict` và `note`.
3. Với mỗi dòng, đọc cột `instruction` (nguyên văn câu lệnh) và cột `amending_unit` (đơn vị chứa câu lệnh đó).
4. So cột `target_named` (đích mà quy tắc đọc được từ câu lệnh) với câu lệnh: số điểm, số khoản, số Điều và văn bản bị sửa có đúng như câu lệnh viết không.
5. Với dòng `resolved`, mở cột `target_text`: đây phải đúng là đơn vị mà câu lệnh nhắm tới (đúng số khoản, đúng số điểm, đúng văn bản).
6. Với dòng có lời văn mới, so cột `new_wording_text` với `target_text`: lời văn mới phải là lời văn thay cho chính đơn vị ở `target_text`, không phải của đơn vị khác.
7. Với lệnh "Thay thế cụm từ A bằng cụm từ B tại khoản X": kiểm cụm từ A có xuất hiện trong `target_text` không.
8. So cột `kind` với động từ đầu câu lệnh: "Sửa đổi, bổ sung" hoặc "Sửa đổi" là `modify`, "Bổ sung" là `add`, "Bãi bỏ" là `repeal`, "Thay thế cụm từ" là `replace_phrase`, câu có "hết hiệu lực" là một trong ba loại `expire`.
9. Với lệnh chỉ sửa tên hoặc câu dẫn ("Sửa đổi, bổ sung tên khoản ..."), kiểm cột `kind` có ghi "chỉ tên hoặc câu dẫn".
10. Với dòng `expire_document`: kiểm câu có tuyên bố cả văn bản được nêu hết hiệu lực không; với `expire_subject`: kiểm câu chỉ nêu phạm vi theo nội dung ("Nội dung về ...") mà không nêu Điều, khoản.
11. So cột `effective_from` với ngày hiệu lực ghi trong Điều "Hiệu lực thi hành" của văn bản sửa đổi; quy tắc dùng ngày hiệu lực của cả văn bản và không đọc ngày riêng trong từng câu lệnh.
12. Với dòng `unresolved` hoặc `external`: kiểm xem đích có thật sự không có trong corpus không, bằng cách tìm Điều, khoản, điểm đó trong văn bản bị sửa (nếu văn bản có trong corpus); cột `reason` ghi lý do quy tắc không giải được.
13. Ghi một mã vào cột `verdict` và, khi không phải `dung`, ghi ngắn lý do vào `note`.

## Mã kết luận

| Mã | Khi nào dùng |
|---|---|
| `dung` | Dòng đúng như nguyên văn: đúng đích, đúng loại, đúng phạm vi; với dòng `unresolved` hoặc `external`, đích được nêu đúng là không có trong corpus; với `expire_subject`, câu đúng là nêu phạm vi theo nội dung |
| `sai_dich` | Sai đích: đơn vị khác, văn bản khác, hoặc đích có trong corpus mà quy tắc ghi là không giải được |
| `sai_loai` | Đúng đích nhưng sai loại hoặc sai phạm vi, ví dụ lệnh bãi bỏ bị ghi là sửa đổi, hoặc lệnh chỉ sửa tên khoản bị ghi là thay cả khoản |
| `khac` | Trường hợp khác: dòng không phải câu lệnh, sai ngày, hoặc không quyết được; ghi rõ ở `note` |

Đây là việc so chữ, không cần và không được dùng nhận định pháp lý: chỉ so số Điều, khoản, điểm, tên văn bản và cụm từ giữa các cột.

## Tính kết quả

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli amendment-score experiments/amendment-check-v3/check-sheet-kha.csv --compare experiments/amendment-check-v3/check-sheet-vu.csv
```

Lệnh in số cạnh theo từng mã kết luận, tách theo trạng thái (`resolved`, `resolved_parent`, `unresolved`, `external`, `document`) và theo loại, cùng tỉ lệ đúng trên số dòng đã kiểm.
Với `--compare`, lệnh in tỉ lệ đồng ý thô, Cohen's kappa trên bốn mã và trên đúng/không đúng, và danh sách cạnh hai người kết luận khác nhau để đối soát.
Sau khi đối soát, ghi kết luận chung vào một tệp thứ ba và chấm tệp đó để lấy số báo cáo.

## Giới hạn cần nêu trong luận văn

### Hết hiệu lực một phần theo nội dung

Khoản 2 Điều 35 NĐ 219/2025/NĐ-CP viết: "Nội dung về lao động nước ngoài làm việc tại Việt Nam quy định tại Nghị định số 152/2020/NĐ-CP ... được sửa đổi, bổ sung tại Nghị định số 70/2023/NĐ-CP ... hết hiệu lực thi hành kể từ ngày Nghị định này có hiệu lực".
Câu này nêu phạm vi theo nội dung, không nêu Điều, khoản, nên quy tắc ghi một cạnh `expire_subject` ở trạng thái `unresolved` và trạng thái đơn vị không áp dụng nó.
Văn bản bị ảnh hưởng: NĐ 152/2020/NĐ-CP và lời văn sửa đổi của nó trong NĐ 70/2023/NĐ-CP.
Metadata vbpl.vn lưu trong bản chụp đã ghim (`document.json`, không tải lại):

| Văn bản | `effFrom` | `effTo` | `effStatus` | `updatedDate` |
|---|---|---|---|---|
| NĐ 152/2020/NĐ-CP (vbpl 152669) | 2021-02-15T00:00:00 | 2026-11-15T00:00:00 | "Hết hiệu lực một phần" (HHL1P) | 2026-10-01T17:42:28 |
| NĐ 219/2025/NĐ-CP (vbpl 180273) | 2025-08-07T00:00:00 | 2026-12-05T00:00:00 | "Còn hiệu lực" (CHL) | 2026-11-05T08:05:30 |
| NĐ 70/2023/NĐ-CP (vbpl 162330) | 2023-09-18T00:00:00 | null | "Hết hiệu lực một phần" (HHL1P) | 2026-05-08T18:37:54 |

Như vậy vbpl.vn báo NĐ 152/2020 còn áp dụng đến 15/11/2026, trong khi nguyên văn NĐ 219/2025 cho phần lao động nước ngoài hết hiệu lực từ 07/08/2025; vbpl.vn cũng báo NĐ 219/2025 "Còn hiệu lực" nhưng có `effTo` 05/12/2026.
Nhóm không giải thích hai điểm này bằng nhận định pháp lý; luận văn nêu sự chênh lệch như trên.

### Điều bị chặn khi trích Điều vào corpus v3

Bước trích Điều (`ingestion/excerpt.py`) chặn một Điều khi bộ phân tích gặp tiêu đề lặp hoặc tiêu đề lạc chỗ trong phạm vi của Điều đó.
Các Điều sau không có trong corpus v3 (corpus đã khóa, không sửa):

| Văn bản | Điều | Lý do | Nguyên nhân trong nguyên văn |
|---|---|---|---|
| NĐ 152/2020/NĐ-CP | Điều 30. Trách nhiệm thi hành | `duplicate_heading` | Khoản 5 có hai điểm cùng ký hiệu "d)": "d) Quyết định việc cho phép nhà thầu được tuyển dụng người lao động nước ngoài ..." và "d) Chấp thuận những vị trí công việc được sử dụng người lao động nước ngoài trên địa bàn ..." |
| NĐ 145/2020/NĐ-CP | Điều 113. Quyền, trách nhiệm của người lao động khi ngừng đình công | `duplicate_heading` | Văn bản có hai tiêu đề "Chương XI": "Chương XI GIẢI QUYẾT TRANH CHẤP LAO ĐỘNG" và "Chương XI ĐIỀU KHOẢN THI HÀNH"; tiêu đề thứ hai nằm ngay sau Điều 113 nên Điều 113 bị chặn dù lời văn của nó nguyên vẹn |
| NĐ 283/2026/NĐ-CP | Điều 1. Phạm vi điều chỉnh | `orphan_heading` | Các điểm a), b), c) đứng trước khoản đầu tiên không có số "1." (đã ghi trong nhật ký quyết định 11/11) |
| Bộ luật Lao động 2019 | Điều 219. Sửa đổi, bổ sung một số điều của các luật có liên quan đến lao động | `quoted_text` | Điều sửa luật khác, trích dẫn khoản của luật khác; không thêm vào v3 |

Hai Điều sửa đổi khác bị chặn vì `quoted_text` (Điều 1 NĐ 70/2023, Điều 139 Luật BHXH 41/2024) đã được đưa vào v3 có chủ đích (`include_amending`).
Hệ quả: 10 cạnh nhắm Điều 30 NĐ 152/2020 (năm cạnh sửa đổi, năm cạnh bãi bỏ) có lý do `article_not_found`; đích có trong nguyên văn nhưng không có trong corpus, nên các dòng này vẫn có thể là `dung`, người kiểm ghi thêm điều này vào `note`.
Ngoài ra, vì tiêu đề "Chương XI" thứ hai bị bỏ qua, Điều 114 và Điều 115 NĐ 145/2020 nằm dưới Mục 4 Chương XI trong corpus v3 (mã `145-2020-nd-cp/chapter-xi/section-4/article-114`), không dưới một chương riêng.

Từ 15/11/2026, `excerpt` có tùy chọn `cut_stray_headings` (mặc định tắt, nên các phiên bản corpus đã dựng vẫn dựng lại y hệt): khi bật, Điều chỉ chứa một tiêu đề chương hoặc mục bị lặp không bị chặn nữa và phần trích dừng trước tiêu đề đó.
Một corpus v4 bật tùy chọn này sẽ có thêm Điều 113 NĐ 145/2020 (2 khoản); Điều 30 NĐ 152/2020 vẫn bị chặn vì chọn điểm nào là "đ)" là một suy đoán, và Điều 1 NĐ 283/2026 vẫn bị chặn.
Việc nối tùy chọn này vào `corpus-scope` chưa làm.
