# Triển khai Lexora trên VM GCP (vlexora.duckdns.org)

Bản chạy chung để hai người gán nhãn trên cùng một store.
VM e2-micro (Debian 13) dùng chung với 9Router và trang học `goc-hoc`; Lexora chiếm khoảng 85 MB RAM.

## Bố trí

| Thành phần | Vị trí |
|---|---|
| Code, giao diện đã build | `~/lexora/app` (giải nén từ `git archive` cộng `frontend/build`) |
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

Cập nhật code từ máy cá nhân:

```powershell
git archive --format=tar -o code.tar HEAD src prompts configs pyproject.toml README.md   # rồi thêm frontend/build vào tar
scp code.tar.gz gcp:lexora/
ssh gcp "cd ~/lexora/app && tar -xzf ../code.tar.gz && sudo systemctl restart lexora"
```

Lấy store về máy để chạy thực nghiệm: `scp gcp:lexora/backups/lexora-<ngày>.sqlite data/kb/` (bản sao lưu nhất quán, không chép tệp đang mở).

## An toàn

- Trang mở ra Internet: mọi tài khoản đã đổi sang mật khẩu ngẫu nhiên khi triển khai; khóa tạm sau 5 lần sai; cookie chỉ gửi qua HTTPS; POST cần token và Origin `https://vlexora.duckdns.org`.
- Tên miền khác hoặc truy cập thẳng vào IP bị từ chối.
- Khóa 9Router chỉ nằm trong `.env` trên VM, không có trong repo hay nhật ký.
- Trước khi sửa Caddyfile luôn có bản `Caddyfile.bak-<thời điểm>` bên cạnh.
