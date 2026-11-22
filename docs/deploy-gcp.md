# Triển khai Lexora trên VM GCP (vlexora.duckdns.org)

Bản chạy chung để hai người gán nhãn trên cùng một store.
VM e2-micro (Debian 13) dùng chung với 9Router và trang học `goc-hoc`; Lexora chiếm khoảng 85 MB RAM.

## Bố trí

| Thành phần | Vị trí |
|---|---|
| Code, giao diện đã build, tài liệu | `~/lexora/app` (giải nén từ `git archive` của `src prompts configs docs/guides ...` cộng `frontend/build`) |
| Môi trường Python | `~/lexora/venv`, chỉ nhóm `web` (không torch) |
| Store | `~/lexora/data/kb/lexora.sqlite` |
| Danh mục văn bản, bản chụp vbpl.vn | `~/lexora/data/catalog/`, `~/lexora/data/raw/vbpl/` |
| Cài đặt 9Router | `~/lexora/app/.env` (quyền 600): `9ROUTER_URL=http://127.0.0.1:20128`, khóa và các `MODEL_*` |
| Service | `/etc/systemd/system/lexora.service`, lắng nghe `172.18.0.1:8770` (cổng của mạng Docker `goc-hoc_default`, không ra Internet) |
| HTTPS | Caddy của `goc-hoc` (`~/goc-hoc/study-app/deploy/caddy/Caddyfile`), khối `vlexora.duckdns.org` chuyển tới `172.18.0.1:8770` |
| Sao lưu | `~/lexora/backup.sh`, cron 03:30 mỗi ngày, giữ 14 bản trong `~/lexora/backups/` |

Cờ khởi động: `--public-host vlexora.duckdns.org --bind 172.18.0.1 --port 8770 --allow-vbpl --router-model MODEL_OSS_120B --extract-model MODEL_OSS_120B --approve-router` (ngân sách 300 lượt trả lời, 200 lượt tách quy phạm mỗi lần khởi động).
Đề xuất nhãn bằng model cần Claude Code nên không bật trên VM; 152 câu của bộ câu hỏi v1 đã có đề xuất lưu sẵn.

## Thao tác thường gặp

```sh
sudo systemctl status lexora        # trạng thái
journalctl -u lexora -n 50          # nhật ký (không ghi URL hay nội dung request)
sudo systemctl restart lexora       # khởi động lại (đặt lại ngân sách lượt gọi)
```

Cập nhật code từ máy cá nhân (chạy từ thư mục gốc, sau khi `main` đã có bản cần cài và `frontend` đã build lại từ đúng bản đó):

```sh
git archive --format=tar -o code.tar origin/main src prompts configs docs/guides pyproject.toml README.md
tar --force-local -rf code.tar frontend/build && gzip -f code.tar     # --force-local: tar trên Windows hiểu nhầm "C:" là máy từ xa
scp code.tar.gz gcp:lexora/
```

Trên VM, sao lưu trước rồi mới thay code:

```sh
cd ~/lexora
venv/bin/python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" data/kb/lexora.sqlite backups/truoc-<việc>-<ngày>.sqlite
tar -czf backups/app-truoc-<việc>-<ngày>.tar.gz -C app src prompts configs docs/guides frontend/build pyproject.toml README.md
mv app/frontend/build backups/frontend-build-truoc-<việc>-<ngày>   # giải nén chồng lên sẽ để lại tệp giao diện cũ
cd app && tar -xzf ../code.tar.gz && sudo systemctl restart lexora
```

- Bản sao lưu đặt tên `truoc-...` để nằm ngoài vòng xoay 14 bản `lexora-*.sqlite` của `backup.sh`; xóa tay khi không cần nữa.
- Trước khi khởi động lại, kiểm tra không có bản nháp đang tách quy phạm bằng AI (tab Giám sát hoặc trường `extraction` của bản nháp) vì khởi động lại đánh dấu việc tách là `interrupted`.
- Một số bản cập nhật tự đổi cấu trúc store ở lần mở đầu (ví dụ 22/11 thêm `revision_summaries`, `draft_summaries`, `chat_session_meta`); vì vậy bước sao lưu là bắt buộc.
- Sau khi khởi động: `systemctl is-active lexora`, `https://vlexora.duckdns.org/login` trả 200, tệp `_app/immutable/entry/start.*.js` trong trang khớp với `frontend/build/index.html` ở máy cá nhân, và `pragma quick_check` của store là `ok`.
- Quay lại bản cũ: dừng dịch vụ, chép bản `truoc-...sqlite` về `data/kb/lexora.sqlite`, giải nén `app-truoc-...tar.gz` vào `app` (đổi lại thư mục `frontend/build`), rồi khởi động lại.

Đồng bộ kết quả thực nghiệm (trang Kết quả, tab Thực nghiệm và Báo cáo đọc trực tiếp từ thư mục này) sau mỗi lượt chạy mới trên máy cá nhân:
nén `experiments/runs` (bỏ thư mục `audit-rejections-v1` có tệp giải mã và các tệp `.log`) cùng `data/normalized/experiment-scope-v1-veaeaad4a6edc`, chép lên rồi giải nén trong `~/lexora/app`; không cần khởi động lại.

Bảng kiểm tra quy phạm bị loại được nhập vào store bằng `kb-audit-import`; tệp giải mã nằm riêng ở `~/lexora/data/audit/key.json` (quyền 600) và không được phục vụ qua web.
Tài liệu trên trang Tài liệu là các tệp trong `docs/guides/` (kèm hình trong `docs/guides/assets/`), nằm trong gói code.

Lấy store về máy để chạy thực nghiệm: `scp gcp:lexora/backups/lexora-<ngày>.sqlite data/kb/` (bản sao lưu nhất quán, không chép tệp đang mở).

## An toàn

- Trang mở ra Internet: mọi tài khoản đã đổi sang mật khẩu ngẫu nhiên khi triển khai; khóa tạm sau 5 lần sai; cookie chỉ gửi qua HTTPS; POST cần token và Origin `https://vlexora.duckdns.org`.
- Tên miền khác hoặc truy cập thẳng vào IP bị từ chối.
- Khóa 9Router chỉ nằm trong `.env` trên VM, không có trong repo hay nhật ký.
- Trước khi sửa Caddyfile luôn có bản `Caddyfile.bak-<thời điểm>` bên cạnh.
