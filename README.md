# Lexora: tra cứu pháp luật lao động có kiểm chứng

Đồ án RAG trên kho tri thức pháp luật lao động Việt Nam có bằng chứng.
Mọi khẳng định đều truy được về đúng câu trong văn bản gốc, kèm vị trí ký tự và mã băm SHA-256 của bản đã chuẩn hóa.
Quy phạm do máy đề xuất chỉ được dùng sau khi người duyệt chấp nhận; Lexora không xác minh hiệu lực pháp luật và không phải tư vấn pháp lý.

## Trạng thái (07/11/2026)

- Ứng dụng web chạy trên máy cục bộ (FastAPI + SvelteKit, song ngữ Việt/Anh) với ba vai trò: quản trị, người duyệt, người tra cứu.
- Nhập văn bản vào kho tri thức: tìm trong danh mục 171.547 văn bản hoặc dán link vbpl.vn rồi chọn các Điều cần nhập; hoặc tải tệp TXT/HTML/DOCX/PDF có lớp chữ.
- Tách quy phạm theo quy tắc, hoặc bằng AI (Opus 5.5 qua Claude Code) cho kho công khai; người duyệt duyệt từng quy phạm trên nguyên văn rồi công bố thành phiên bản mới của kho.
- Hỏi đáp có dẫn nguồn trên 1-5 kho; sơ đồ tri thức trong app.
- Nghiên cứu: corpus có phiên bản khóa bằng mã băm, chạy truy xuất ĐK1/ĐK2 với Recall@K, gán nhãn bộ câu hỏi bởi hai người độc lập rồi đối soát.
- Chưa có: bộ câu hỏi thật, ĐK3/ĐK4, sinh và chấm câu trả lời theo giao thức.

Chi tiết tiến độ và việc tiếp theo: [progress-2026-11-07](docs/planning/progress-2026-11-07.md).

## Chạy ứng dụng

Cần Python 3.11+, Node (để build giao diện) và Chrome hoặc Edge (cho kiểm thử trên trình duyệt).

```powershell
python -m venv .venv; .venv\Scripts\python -m pip install -e ".[web,web-test,catalog]"
cd frontend; npm install; npm run build; cd ..
.venv\Scripts\python -m legal_ai.auth create-admin --store data/kb/app.sqlite --username admin
.venv\Scripts\python -m legal_ai.web --store data/kb/app.sqlite --port 8766
```

Mở `http://127.0.0.1:8766`.
Các tính năng gọi mạng chỉ bật khi thêm cờ, và mỗi lần gọi đều hỏi xác nhận trong giao diện:

| Cờ | Tác dụng |
|---|---|
| `--allow-vbpl` | Lấy văn bản chính thống từ vbpl.vn, mỗi lần một văn bản |
| `--extract-claude-model claude-opus-5-5 --approve-claude` | Tách quy phạm bằng Opus qua Claude Code (kho công khai) |
| `--proposal-model claude-opus-5-5 --approve-claude` | Opus đề xuất nhãn và soạn nháp câu hỏi |

Danh mục tìm kiếm được nhận tự động khi có `data/catalog/catalog-v1.sqlite`.
Hướng dẫn đầy đủ: [apps/demo/README.md](apps/demo/README.md).

## Kiểm thử

```powershell
.venv\Scripts\python -m unittest discover -s tests -v      # toàn bộ test offline
python -m unittest discover -s tests -v                    # chỉ thư viện chuẩn (test web và danh mục tự bỏ qua)
node scripts/check_app_browser.cjs http://127.0.0.1:<port> <thư mục ảnh>   # kiểm thử trên trình duyệt thật, store mới
```

## Cấu trúc

- `src/legal_ai/`: mã nguồn.
  Lõi pipeline (lấy văn bản, chuẩn hóa, tách cấu trúc, lược đồ, kiểm chứng, trích xuất, truy xuất) chỉ dùng thư viện chuẩn để tái lập thực nghiệm; `web/` là lớp FastAPI, `research/` là corpus và bộ câu hỏi.
- `frontend/`: giao diện SvelteKit (TypeScript), build tĩnh và được FastAPI phục vụ.
- `configs/`: nguồn văn bản đã ghim, cấu hình đồ thị, cấu hình ĐK1-ĐK4.
- `prompts/`: prompt có phiên bản cho các lần gọi model.
- `tests/`: test offline và dữ liệu tổng hợp; `scripts/`: kiểm thử trình duyệt và tiện ích.
- `data/`, `experiments/runs/`: dữ liệu và kết quả cục bộ, không đưa lên Git.
- `docs/`: đề cương, thiết kế, kế hoạch, quyết định, hướng dẫn.

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/planning/progress-2026-11-07.md](docs/planning/progress-2026-11-07.md) | Đã làm gì, việc tiếp theo |
| [docs/decisions.md](docs/decisions.md) | Nhật ký quyết định |
| [docs/architecture.md](docs/architecture.md) | Kiến trúc hiện tại |
| [docs/features/README.md](docs/features/README.md) | Danh sách tính năng và tài liệu từng tính năng |
| [docs/annotation-guidelines.md](docs/annotation-guidelines.md) | Hướng dẫn gán nhãn bộ câu hỏi |
| [docs/evaluation-protocol.md](docs/evaluation-protocol.md) | Giao thức thực nghiệm ĐK1-ĐK4 |
| [docs/planning/target-stack-2026-11-06.md](docs/planning/target-stack-2026-11-06.md) | Công nghệ và các bước chuyển đổi |
| [AGENTS.md](AGENTS.md) | Quy tắc làm việc cho agent (hệ thống bên ngoài, quy ước, kiểm chứng) |

Phân công: Kha phụ trách lược đồ, trích xuất, kiểm chứng, kho tri thức; Vũ phụ trách truy xuất, RAG, ĐK1-ĐK2; cả hai cùng thu thập dữ liệu, gán nhãn chéo, đánh giá và viết báo cáo.
