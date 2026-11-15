# Bảng kiểm cạnh sửa đổi của corpus v3 (15/11/2026)

Bảng này phục vụ việc kiểm tra ở mục 4.2 của kế hoạch nghiên cứu: hai người đối chiếu từng cạnh sửa đổi do quy tắc sinh ra với nguyên văn, rồi luận văn báo cáo số cạnh đúng, sai và chưa giải quyết.
Cột `verdict` và `note` đang trống: chưa ai kiểm, nên không được trình bày bảng này như kết quả đã kiểm.

## Nguồn

- Cạnh sửa đổi: `data/kb/amendments-scope-v3-v48feefc6d53b/edges.jsonl` (`amendment-rules-v1`, chỉ dùng quy tắc, không gọi model).
- Corpus: `data/normalized/experiment-scope-v3-v48feefc6d53b` (phạm vi thực nghiệm v3, đã khóa ngày 11/11/2026).
- Tổng cộng 68 cạnh: 35 `resolved`, 2 `resolved_parent` (37 cạnh giải được), 21 `unresolved`, 10 `external`.
- Lệnh tạo bảng (chạy lại sẽ báo lỗi nếu tệp đã có, để không ghi đè bảng đã điền):

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli amendment-sheet data/kb/amendments-scope-v3-v48feefc6d53b --sheet experiments/amendment-check-v3/check-sheet.csv
```

## Cách làm cho hai người kiểm

1. Mỗi người chép `check-sheet.csv` thành tệp riêng, ví dụ `check-sheet-kha.csv` và `check-sheet-vu.csv`, và làm độc lập, không trao đổi trước khi xong.
2. Mở tệp bằng Excel hoặc LibreOffice (tệp là UTF-8 có BOM nên tiếng Việt hiển thị đúng); không sửa, xóa hay sắp xếp lại các cột khác ngoài `verdict` và `note`.
3. Với mỗi dòng, đọc cột `instruction` (nguyên văn câu lệnh sửa đổi) và cột `amending_unit` (đơn vị chứa câu lệnh đó).
4. So cột `target_named` (đích mà quy tắc đọc được từ câu lệnh) với câu lệnh: số điểm, số khoản, số Điều và văn bản bị sửa có đúng như câu lệnh viết không.
5. Với dòng `resolved`, mở cột `target_text`: đây phải đúng là đơn vị mà câu lệnh nhắm tới (đúng số khoản, đúng số điểm, đúng văn bản).
6. Với dòng có lời văn mới, so cột `new_wording_text` với `target_text`: lời văn mới phải là lời văn thay cho chính đơn vị ở `target_text`, không phải của đơn vị khác.
7. Với lệnh "Thay thế cụm từ A bằng cụm từ B tại khoản X": kiểm cụm từ A có xuất hiện trong `target_text` không.
8. So cột `kind` với động từ đầu câu lệnh: "Sửa đổi, bổ sung" hoặc "Sửa đổi" là `modify`, "Bổ sung" là `add`, "Bãi bỏ" là `repeal`, "Thay thế cụm từ" là `replace_phrase`.
9. So cột `effective_from` với ngày hiệu lực ghi trong Điều "Hiệu lực thi hành" của văn bản sửa đổi; quy tắc dùng ngày hiệu lực của cả văn bản và không đọc ngày riêng trong từng câu lệnh.
10. Với dòng `unresolved` hoặc `external`: kiểm xem đích có thật sự không có trong corpus không, bằng cách tìm Điều, khoản, điểm đó trong văn bản bị sửa (nếu văn bản có trong corpus); cột `reason` ghi lý do quy tắc không giải được.
11. Ghi một mã vào cột `verdict` và, khi không phải `dung`, ghi ngắn lý do vào `note`.

## Mã kết luận

| Mã | Khi nào dùng |
|---|---|
| `dung` | Dòng đúng như nguyên văn: đúng đích, đúng loại; với dòng `unresolved` hoặc `external`, đích được nêu đúng là không có trong corpus |
| `sai_dich` | Sai đích: đơn vị khác, văn bản khác, hoặc đích có trong corpus mà quy tắc ghi là không giải được |
| `sai_loai` | Đúng đích nhưng sai loại, ví dụ lệnh bãi bỏ bị ghi là sửa đổi |
| `khac` | Trường hợp khác: dòng không phải câu lệnh sửa đổi, sai ngày, hoặc không quyết được; ghi rõ ở `note` |

Đây là việc so chữ, không cần và không được dùng nhận định pháp lý: chỉ so số Điều, khoản, điểm, tên văn bản và cụm từ giữa các cột.

## Tính kết quả

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli amendment-score experiments/amendment-check-v3/check-sheet-kha.csv --compare experiments/amendment-check-v3/check-sheet-vu.csv
```

Lệnh in số cạnh theo từng mã kết luận, tách theo trạng thái (`resolved`, `resolved_parent`, `unresolved`, `external`) và theo loại, cùng tỉ lệ đúng trên số dòng đã kiểm.
Với `--compare`, lệnh in tỉ lệ đồng ý thô, Cohen's kappa trên bốn mã và trên đúng/không đúng, và danh sách cạnh hai người kết luận khác nhau để đối soát.
Sau khi đối soát, ghi kết luận chung vào một tệp thứ ba và chấm tệp đó để lấy số báo cáo.

## Điểm cần chú ý khi kiểm (do người tạo bảng thấy, chưa kiểm)

- Cạnh của câu lệnh "Sửa đổi, bổ sung tên khoản 8 Điều 9" (NĐ 70/2023) được ghi là `modify` trên cả khoản 8 Điều 9 NĐ 152/2020, trong khi câu lệnh chỉ đổi câu dẫn của khoản; truy xuất có lọc hiệu lực coi lời văn mới là thay toàn bộ khoản 8.
- Mười cạnh nhắm Điều 30 NĐ 152/2020 được ghi `article_not_found` (năm cạnh sửa đổi, năm cạnh bãi bỏ): trong corpus, NĐ 152/2020 chỉ có đến Điều 29.
  Bản chụp vbpl.vn đã ghim của NĐ 152/2020 có "Điều 30. Trách nhiệm thi hành", nhưng bước trích Điều (`ingestion/excerpt.py`) chặn Điều này với lý do `duplicate_heading`, nên Điều 30 không vào corpus v3.
  Theo nghĩa của mã kết luận, đích quả thật không có trong corpus nên các dòng này vẫn có thể là `dung`; người kiểm ghi thêm vào `note` là đích có trong nguyên văn để báo cáo tách riêng lỗi thiếu Điều của corpus; dữ liệu chưa được sửa.
- Mười cạnh `external` sửa văn bản ngoài corpus (Luật BHXH 58/2014, BLTTDS 92/2015, NĐ 35/2022, Luật Việc làm 38/2013, Luật Người cao tuổi 39/2009, NĐ 128/2025); năm cạnh từ BLLĐ 2019 không có đơn vị chứa câu lệnh vì các Điều sửa luật khác của BLLĐ không nằm trong corpus.
