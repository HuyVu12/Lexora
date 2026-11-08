# Kiểm tra tay quy phạm bị loại (`rejection-audit-v1`)

Bộ kiểm chứng loại một quy phạm khi một giá trị hoặc từ tình thái không nằm nguyên văn trong chính câu của nó.
Điều đó không có nghĩa quy phạm sai.
Mục tiêu của bước này là đo xem trong số quy phạm bị loại có bao nhiêu thật sự sai, và trong số quy phạm được giữ có bao nhiêu sai.

## 1. Phân tích tự động

`kb-compare` tự phân loại mọi quy phạm bị loại theo chỗ tìm thấy giá trị thiếu, ghi ở mục "Bị loại vì đâu" của `docs/results/extraction-models.md` và trang Kết quả:

- mượn ngữ cảnh: mọi giá trị thiếu đều có ở câu khác của cùng đơn vị hoặc ở đơn vị cha (câu dẫn của khoản, tên Điều);
- có giá trị không tìm thấy: ít nhất một giá trị không có ở đâu trong đơn vị và các đơn vị cha;
- chỉ sai nghĩa từ tình thái: từ tình thái có trong câu nhưng thuộc loại khác (ví dụ "phải" gán cho quyền);
- khác: lỗi schema, toàn vẹn hoặc trùng lặp.

Con số tự động chỉ cho biết chữ lấy từ đâu, không cho biết đúng hay sai về pháp lý.

## 2. Bảng gán nhãn

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python -m legal_ai.cli kb-audit-sheet experiments/runs/kb-scope-v1-gemma4-31b experiments/runs/kb-scope-v1-gpt-oss-120b experiments/runs/kb-scope-v1-nemotron-3-ultra experiments/runs/kb-scope-v1-nemotron-3-super --sheet experiments/runs/audit-rejections-v1/sheet.csv --key experiments/runs/audit-rejections-v1/key.json --rejected 20 --accepted 6
```

- Mỗi lượt lấy mẫu có hạt giống cố định 20 quy phạm bị loại và 6 quy phạm được giữ, trộn chung; bảng hiện có 104 dòng.
- Người gán nhãn không thấy tên model, không biết quy phạm bị loại hay được giữ, không thấy lý do của bộ kiểm chứng.
- Tệp `key.json` ánh xạ từng dòng về model, quy phạm và quyết định; không đưa cho người gán nhãn.
- Mỗi người gán trên một bản sao riêng của `sheet.csv`, không trao đổi trước khi đối soát.

Các cột: `context` (tên Điều, câu dẫn của khoản và điểm cha), `unit_text` (nguyên văn đơn vị), `sentence` (câu được trích xuất), `norm` (quy phạm model đưa ra), `label`, `note`.

## 3. Nhãn

So quy phạm với luật (đọc cả `context`), không so với cách diễn đạt mong muốn.
Khi nhiều nhãn cùng đúng, chọn nhãn đứng trước trong danh sách:

| Nhãn | Khi nào |
|---|---|
| `sai` | Quy phạm nói điều luật không nói, mâu thuẫn với luật, sai chủ thể, sai tính quy phạm hoặc bỏ mất điều kiện, ngoại lệ làm đổi nghĩa |
| `dien_dat` | Đúng nghĩa nhưng giá trị bị viết lại, rút gọn hoặc ghép từ nhiều chỗ, không còn là nguyên văn |
| `dung_ngu_canh` | Đúng, nhưng có chữ lấy từ câu dẫn của khoản hoặc tên Điều thay vì từ chính câu |
| `dung` | Đúng và nguyên văn trong câu |
| `khong_ro` | Không quyết định được; ghi lý do vào `note` |

Ví dụ: điểm e) "Đủ tuổi nghỉ hưu ..., trừ trường hợp các bên có thỏa thuận khác" dưới câu dẫn "2. Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:", quy phạm "Chủ thể: Người lao động; Hành vi: đơn phương chấm dứt; tính quy phạm: quyền" là `dung_ngu_canh`.

## 4. Chấm và đối soát

```powershell
.venv\Scripts\python -m legal_ai.cli kb-audit-score <bảng của người 1> --key experiments/runs/audit-rejections-v1/key.json --compare <bảng của người 2>
```

- Theo từng model và từng quyết định của bộ kiểm chứng: số nhãn mỗi loại, tỉ lệ `sai` trên các dòng đã quyết định (bỏ `khong_ro`), và bảng chéo giữa phân loại tự động với nhãn người.
- `--compare` cho Cohen's kappa trên năm nhãn và trên hai lớp sai / không sai.
- Báo cáo: tỉ lệ sai trong nhóm bị loại là độ chính xác của bộ kiểm chứng; tỉ lệ sai trong nhóm được giữ là phần lỗi lọt qua ĐK4 (thường là lỗi ngữ nghĩa với trích dẫn nguyên văn).
