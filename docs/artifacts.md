# Tạo phẩm ngoài Git và sao lưu

`data/`, `experiments/runs/` và `models/` nằm ngoài Git.
Một số tạo phẩm trong đó tốn tiền gọi model hoặc nhiều giờ máy để tạo lại, nên phải được sao lưu thay vì chạy lại.

## Sao lưu

```powershell
python scripts/backup_artifacts.py                  # chép tệp mới hoặc đã đổi ra ~/Lexora-artifacts, kèm manifest.json (kích thước, mtime, SHA-256)
python scripts/backup_artifacts.py --dry-run        # chỉ liệt kê
python scripts/backup_artifacts.py --dest <thư mục> # đích khác, phải nằm ngoài repo
```

Script chép `data/`, `experiments/runs/` và `models/bge-m3-vectors*.sqlite`.
Tệp SQLite được chép qua API sao lưu của SQLite nên vẫn nhất quán khi đang có tiến trình ghi.
Không tệp nào trong bản sao lưu bị xóa, nên tệp lỡ xóa trong repo vẫn còn ở đó.
Chạy lại sau mỗi lượt gọi model hoặc lượt mã hóa dài.
Thư mục đích nằm trên cùng ổ đĩa với repo, nên bảo vệ trước việc xóa nhầm hoặc clone lại, chưa bảo vệ trước hỏng ổ.

Không sao lưu vì tạo lại nhanh:

- `models/bge-m3`: trọng số BAAI/bge-m3, tải lại đúng revision ghi trong `configs/experiments/shared.json`.
- `models/bge-m3-openvino`: chuyển lại từ cùng trọng số khi chạy `run-retrieval --embed-device openvino-gpu` (khoảng 1 phút).

## Khôi phục

Chép thư mục tương ứng từ bản sao lưu về đúng đường dẫn trong repo, rồi kiểm mã băm với `manifest.json` nếu cần.
Bộ đệm vector được khóa theo model, revision, mã băm trọng số, độ dài tối đa và mã băm của chữ, nên chép về là dùng lại được ngay.

## Tạo phẩm tốn kém

| Đường dẫn | Nội dung | Chi phí để tạo lại |
|---|---|---|
| `models/bge-m3-vectors.sqlite` | Bộ đệm vector BGE-M3 của mọi bản ghi và câu hỏi đã chạy | Nhiều giờ CPU, khoảng 1 giờ trên GPU Iris Xe cho mỗi biến thể kho |
| `experiments/runs/kb-scope-v3-sonnet` | Kho quy phạm corpus v3, Claude Sonnet 5.5, 863 lô | 16,97 USD |
| `experiments/runs/kb-keys-gen-pilot-sonnet` | Khóa tìm kiếm do Sonnet soạn, 520 lô, 2.434 đơn vị | 14,38 USD |
| `experiments/runs/kb-scope-v1-gpt-oss-120b`, `kb-scope-v2-gpt-oss-120b` và các `kb-scope-v1-*` | Kho quy phạm do gpt-oss-120b và các model so sánh trích qua 9Router | Lượt gọi 9Router, hiện hay lỗi 503 |
| `experiments/runs/relations-v2-sonnet` | Đồ thị quan hệ giữa các Điều, 711 lượt Sonnet | Lượt gọi Claude Code |
| `experiments/runs/dryrun-cases-v1`, `dryrun-conflict-v1` và các thư mục `answers-*`, `judge*` | Câu trả lời Haiku, gpt-oss và điểm giám khảo Sonnet của các lượt chạy thử | Khoảng 1.700 lượt Claude Code |
| `experiments/runs/kb-inherit-2026-11-23` | Kho dẫn xuất với `claims-inherit-v1` và `kb-validator-v4` | Offline, vài phút |
| `data/raw` | Bản chụp văn bản đã tải từ vbpl.vn | Lượt tải mạng cần duyệt từng văn bản |
| `data/kb/research-scope-v3-20261111.sqlite` và các store khác | Corpus đã khóa, store của app | Dựng lại từ bản chụp, mã phiên bản phải khớp |
