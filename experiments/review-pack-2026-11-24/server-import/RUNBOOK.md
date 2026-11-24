# Nhập bộ hiệu lực và bộ cần liên kết lên máy chủ gán nhãn (24/11/2026)

Hai bộ được nhập thành bộ câu hỏi trên phiên bản corpus `v48feefc6d53b` (đã có trong store máy chủ từ 15/11), nhãn của model là đề xuất.
Vũ gán ở chế độ có xem đề xuất; Kha gán độc lập, không thấy đề xuất.
Mỗi lệnh `question-drafts` chỉ chạy **một lần**; chạy lại sẽ tạo thêm một bộ trùng.

Đã chạy thử trên bản sao `data/kb/vm-lexora-20261124.sqlite` (tệp gốc không bị sửa): bộ hiệu lực `qf78b006a859a` (30 câu), bộ cần liên kết `qcb34bf366b6e` (35 câu), 65 đề xuất, không nhãn mới, bốn bộ cũ và 152 nhãn của bộ tra cứu không đổi; `verify.py` báo OK.
Mã máy chủ `cfd78cf` đã có lệnh `question-drafts` và `import_drafts` giống hệt mã hiện tại, nên không cần cập nhật code.
Mã bộ trên máy chủ sẽ khác mã thử (sinh từ thời điểm).

## Tệp

| Tệp | Việc |
|---|---|
| `validity-drafts.json`, `link-drafts.json` | Tệp nhập (30 và 35 câu), dựng bởi `build-drafts.py` |
| `guideline-validity-2026-11-24.md`, `guideline-link-2026-11-24.md` | Hướng dẫn gán nhãn gắn vào từng bộ |
| `verify.py` | Kiểm tra chỉ đọc sau khi nhập |

## Máy cá nhân (PowerShell, tại thư mục Lexora)

```powershell
$D = 'experiments\review-pack-2026-11-24\server-import'
tar -czf serverimport.tar.gz -C experiments/review-pack-2026-11-24 server-import/validity-drafts.json server-import/link-drafts.json server-import/guideline-validity-2026-11-24.md server-import/guideline-link-2026-11-24.md server-import/verify.py
scp serverimport.tar.gz gcp:lexora/
```

## Máy chủ (`ssh gcp`)

Bước 1. Dừng app và sao lưu store (tên `truoc-...` để nằm ngoài vòng xoay 14 bản).

```sh
sudo systemctl stop lexora
cd ~/lexora
venv/bin/python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" data/kb/lexora.sqlite backups/truoc-bo-hieu-luc-lien-ket-20261124.sqlite
ls -l data/kb/lexora.sqlite backups/truoc-bo-hieu-luc-lien-ket-20261124.sqlite
```

Kiểm tra không còn nháp đang tách quy phạm bằng AI trước khi dừng (khởi động lại đánh dấu `interrupted`).

Bước 2. Giải nén và nhập (hai lệnh, mỗi lệnh một lần).

```sh
cd ~/lexora/app && tar -xzf ../serverimport.tar.gz
D=server-import
S=~/lexora/data/kb/lexora.sqlite
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli question-drafts $D/validity-drafts.json --store $S --actor admin --author "claude-opus-5-5 (nháp model hiệu lực 15-16/11/2026)" --version v48feefc6d53b --name "Bộ hiệu lực v1 (corpus v3, nháp model 16/11)" --guideline $D/guideline-validity-2026-11-24.md
PYTHONPATH=src ~/lexora/venv/bin/python -m legal_ai.cli question-drafts $D/link-drafts.json --store $S --actor admin --author "claude-sonnet-5-5 (nháp model cần liên kết 23/11/2026)" --version v48feefc6d53b --name "Bộ cần liên kết v1 (corpus v3, nháp model 23/11)" --guideline $D/guideline-link-2026-11-24.md
```

Kết quả mong đợi: `"added": 30, "families": 30` và `"added": 35, "families": 35`, mỗi lệnh in một `set_id`.
Lệnh có thể mất 1-2 phút (store lớn); không chạy lại khi chưa thấy kết quả.

Bước 3. Kiểm tra chỉ đọc.

```sh
PYTHONPATH=src ~/lexora/venv/bin/python $D/verify.py --store $S --backup ~/lexora/backups/truoc-bo-hieu-luc-lien-ket-20261124.sqlite
sqlite3 $S "pragma quick_check" 2>/dev/null || ~/lexora/venv/bin/python -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('pragma quick_check').fetchone())" $S
```

Kết quả mong đợi: dòng cuối `OK: ...`, mã thoát 0, `new_rows` có `question_sets: 2`, `questions: 65`, `question_proposals: 65`, các bảng khác 0; `quick_check` là `ok`.
Nếu `FAILED`, không khởi động app; làm phần quay lại.

Bước 4. Khởi động và kiểm tra.

```sh
sudo systemctl start lexora && systemctl is-active lexora
```

Đăng nhập tài khoản gán nhãn, thấy hai bộ mới trong trang bộ câu hỏi; mở một câu của bộ hiệu lực: chế độ có đề xuất hiện lý do có ngày áp dụng và đơn vị lỗi thời không được chọn.

## Quay lại

```sh
sudo systemctl stop lexora
cp -p ~/lexora/backups/truoc-bo-hieu-luc-lien-ket-20261124.sqlite ~/lexora/data/kb/lexora.sqlite
sudo systemctl start lexora
```

Chỉ quay lại khi chưa ai gán nhãn vào hai bộ mới (nhãn gán sau bước 4 sẽ mất); nếu đã có nhãn mà hai bộ sai, báo coordinator để xóa riêng hai bộ thay vì phục hồi toàn store.
Sau khi chắc chắn ổn, xóa tay bản `truoc-...` khi không cần.

## Ghi chú

- App cũ không có trường ngày áp dụng: ngày nằm trong chữ của câu (câu có ngày) hoặc theo quy ước ngày khóa 11/11/2026 trong hướng dẫn; ngày và đơn vị lỗi thời cũng ghi ở lý do của đề xuất.
- Loại câu: bộ hiệu lực dùng `temporal` (25) và `lookup` (5, đối chứng); bộ cần liên kết dùng `synthesis` (30) và `lookup` (5, đối chứng); loại `link` và `control` của tệp gốc không có trong app nên đã ánh xạ như vậy.
- Mọi câu có hành vi `answer`; không có câu `refuse`.
