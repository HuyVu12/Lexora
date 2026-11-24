# Định dạng mã mục và nhãn của bảng kiểm tra quy phạm bị loại

Bộ trên app: `a18ba17ef7635` ("Kiểm tra quy phạm bị loại v1", tạo bởi `phapche` ngày 08/11/2026) trong `data/kb/vm-lexora-20261124.sqlite`, bảng `audit_sets`.
Cột `items` của bộ này trùng từng dòng, đúng thứ tự và đúng nội dung (`item_id`, `context`, `unit_text`, `sentence`, `norm`) với `experiments/runs/audit-rejections-v1/sheet.csv`; `audit_build.py` kiểm điều này mỗi lần chạy.
Khi soạn gợi ý, agent chỉ đọc cột `items` (mở store ở chế độ chỉ đọc), không đọc cột `key`, bảng `audit_final` hay `key.json`.

## Mã mục

- Mã mục là `item_id` của bảng, dạng `R` + 10 ký tự hex, ví dụ `R9606202419`.
- Trong `data/audit.json`, `id` của mỗi mục chính là `item_id` này.

## Nhãn

- Năm nhãn của `legal_ai.evaluation.rejection_audit.LABELS`: `sai`, `dien_dat`, `dung_ngu_canh`, `dung`, `khong_ro`.
- `value` của các `options` trong `data/audit.json` đúng là năm nhãn này; mỗi option có `csv: {"label": <nhãn>}` (cột `label` của CSV `kb-audit-score`).
- Ghi chú tối đa 2000 ký tự (`AuditStore.save_label`).

## Nhập nhãn cho `huyvu`

`src/legal_ai/research/audit.py` lưu mỗi nhãn bằng `AuditStore.save_label(set_id, item_id, annotator, annotator_name, label, note)` vào bảng `audit_labels` (khóa chính `set_id, item_id, annotator`).

```powershell
python scripts/review_pack/convert.py audit review-audit-vu.json --output audit-huyvu.json
python scripts/review_pack/convert.py audit review-audit-vu.json --output audit-huyvu.json --store <store> --set a18ba17ef7635 --apply
```

Lệnh thứ nhất ra `{"annotator": "huyvu", "annotator_name": "Huy Vũ", "labels": [{"item_id", "label", "note"}]}`.
Lệnh thứ hai lưu thêm vào store qua `AuditStore`; đã thử 24/11/2026 trên một bản sao tạm của `vm-lexora-20261124.sqlite`: 104/104 nhãn được nhận.
Store dùng chung trên máy chủ là nơi nhận nhãn thật; việc ghi lên máy chủ cần người dùng duyệt.
