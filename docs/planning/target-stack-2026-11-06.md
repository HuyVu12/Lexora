# Công nghệ mục tiêu: hướng tới người dùng thật

Ngày quyết định: 06/11/2026.
Trạng thái: đã chốt định hướng, **chưa triển khai**.
Nhật ký: `docs/decisions.md`.

## Bối cảnh

Đến 06/11/2026, giao diện Lexora chỉ dùng để trình diễn trước hội đồng chấm và để kiểm thử.
Người dùng quyết định chuyển định hướng sang người dùng thật, nên công nghệ phải phục vụ được nhiều người dùng, bảo trì lâu dài và mở rộng giao diện.
Đồ án vẫn cần pipeline ĐK1–ĐK4 tái lập được, vì vậy phần lõi nghiên cứu không đổi.

## Nguyên tắc

- Lõi pipeline (lấy văn bản, chuẩn hóa, lược đồ, kiểm chứng, trích xuất, truy xuất, đánh giá) giữ là thư viện Python thuần, chỉ dùng thư viện chuẩn, để hội đồng chạy lại được mà không cần cài gì.
- Thư viện mới chỉ thêm ở lớp web, frontend và môi trường thực nghiệm; lớp web gọi vào lõi chứ không viết lại logic của lõi.
- Mọi bằng chứng vẫn phải khớp nguyên văn, kèm vị trí ký tự Unicode và SHA-256; công nghệ mới không được nới quy tắc này.
- Cài thư viện hoặc gọi dịch vụ ngoài cần người dùng duyệt trước, theo `AGENTS.md`.

## Hiện trạng và mục tiêu

| Lớp | Hiện trạng | Mục tiêu |
|---|---|---|
| Lõi pipeline | Python 3.11+, thư viện chuẩn | Giữ nguyên |
| Lớp web | Đã chuyển: FastAPI (`src/legal_ai/web/`); server cũ `demo.py` đã gỡ 07/11 | FastAPI + Pydantic, chạy bằng Uvicorn; API có kiểu dữ liệu và tài liệu OpenAPI |
| Lưu trữ | SQLite (`kb-store-v1`) | Giữ SQLite ở các bước đầu; sau đó PostgreSQL, thêm pgvector khi kho đủ lớn |
| Frontend | Đã chuyển: SvelteKit (`frontend/`); giao diện cũ đã gỡ 07/11 | Svelte 5 + SvelteKit (xuất tĩnh), TypeScript, Vite |
| Sơ đồ | SVG vẽ tay trong `kb/entity-viewer.html`, `kb/viewer.html` | Cytoscape.js; vẫn xuất được một tệp HTML tự chứa (ví dụ `vite-plugin-singlefile`) |
| Ngôn ngữ giao diện | Chỉ tiếng Việt | Song ngữ Việt và Anh; văn bản luật và trích dẫn luôn giữ tiếng Việt |
| Truy cập | Chưa kiểm tra | WCAG 2.2 AA, đọc được trên máy chiếu |
| Font | Font hệ thống | Tự host font có đủ dấu tiếng Việt (ví dụ Be Vietnam Pro, Noto Serif), không gọi Google Fonts lúc chạy |
| Thuật ngữ | `src/legal_ai/glossary.py` | Giữ một nguồn duy nhất, thêm bản tiếng Anh |
| Truy xuất | BM25 không phân biệt dấu, dense RRF tùy chọn (`rag/dense.py`) | BM25 làm mốc; thử tách từ tiếng Việt (`underthesea` hoặc `pyvi`); embedding (BGE-M3, multilingual-e5-large, `bkai-foundation-models/vietnamese-bi-encoder`) và reranker (bge-reranker-v2-m3) chọn bằng số đo trên tập dev |
| LLM | Qua 9Router (`providers/router.py`) | Giữ lớp 9Router; mỗi lần chạy cố định một model, ghi phiên bản, temperature và seed vào manifest trong `experiments/` |
| Đánh giá | Giao thức trong `docs/evaluation-protocol.md`, chưa có script | Tự viết các chỉ số đã định nghĩa; LLM làm giám khảo chỉ bổ sung cho người chấm |

Thư viện nặng như torch và sentence-transformers chỉ cài trong môi trường thực nghiệm (máy GPU), không đưa vào lõi hay lớp web.

## Không dùng

- LangChain, LlamaIndex: che prompt và cách cắt đoạn, trong khi đề tài cần kiểm soát vị trí ký tự và tính tái lập.
- Graph database (Neo4j): sơ đồ nhỏ, lưu trong SQLite hoặc PostgreSQL là đủ.
- Microservice: một ứng dụng web gọi vào lõi là đủ.

## Các bước chuyển đổi đề xuất

Các bước này làm trước pipeline ĐK1–ĐK4 (đã chốt 06/11/2026).

1. **Xong 06/11/2026.** Tách lớp API: viết FastAPI bọc các hàm hiện có của `ReviewStore`, `ChatService`, `SourceLibrary`; giữ nguyên hành vi, token và kiểm tra Host/Origin; giữ server cũ cho đến khi bộ test và E2E chạy được trên API mới.
   Kết quả: `src/legal_ai/web/app.py` (`create_app`), `src/legal_ai/web/setup.py` (phần dùng chung với `demo.py`), `python -m legal_ai.web`; `tests/test_web_api.py` đạt 5/5 và `scripts/check_demo_browser.cjs` chạy hết luồng trên Uvicorn với giao diện cũ. Phiên bản gói ghi trong `pyproject.toml` (extra `web`, `web-test`).
2. Chuyển lưu trữ: thêm lớp lưu trữ PostgreSQL bên cạnh SQLite, viết script chuyển dữ liệu, chạy cùng bộ test trên cả hai.
   **Lùi lại (07/11/2026):** làm sau khi đóng băng MVP (27/11); từ 09/11 ưu tiên dữ liệu nghiên cứu và pipeline ĐK1-ĐK4.
3. **Xong 07/11/2026.** Frontend mới: dựng lại các màn hình hiện có bằng TypeScript + Vite, kèm song ngữ và WCAG AA ngay từ đầu.
   Kết quả: `frontend/` (SvelteKit 3, Svelte 5) với đăng nhập ba vai trò (`src/legal_ai/auth.py`), hướng thị giác "Bản luật đã đánh dấu", song ngữ Việt và Anh bằng từ điển có kiểm tra kiểu (không dùng Paraglide vì bản build của nó tải và chạy plugin từ CDN), thuật ngữ song ngữ từ máy chủ; `scripts/check_app_browser.cjs` là bài E2E mới; giao diện cũ (`demo.py`, `demo.html`, `demo.css`, `demo-app.js`, `scripts/check_demo_browser.cjs`) đã gỡ ngày 07/11/2026 theo quyết định của người dùng; kiểm thử HTTP của nó chuyển sang `tests/test_web_api.py`.
4. **Xong 07/11/2026.** Sơ đồ: chuyển hai trang sơ đồ sang Cytoscape.js.
   Kết quả: trang `/kb/:id/graph` trong app (chế độ Quy phạm và Cấu trúc văn bản, phóng to, kéo, cột bằng chứng nguyên văn, cùng hệ thiết kế, có đăng nhập và song ngữ) đọc `GET /api/kb/graph`; hai tệp HTML tự chứa (`kb/viewer.html`, `kb/entity-viewer.html`) vẫn được giữ cho bản xuất của `cli graph-build` và các smoke test DOM.
5. Truy xuất và LLM: đo embedding, reranker và model trên tập dev rồi chốt.

## Đã chốt thêm (06/11/2026)

- Frontend: Svelte 5 + SvelteKit, xuất tĩnh (SPA, `adapter-static`) để lớp web FastAPI phục vụ; TypeScript; song ngữ bằng từ điển có kiểm tra kiểu (Paraglide bị loại, xem bước 3); Cytoscape.js cho sơ đồ.
- Người dùng thật: pháp chế và nhân sự doanh nghiệp. Hai vai trò dự kiến: người duyệt (pháp chế, luật sư nội bộ) nhập và duyệt quy phạm; người tra cứu (nhân sự) chỉ hỏi đáp trên kho đã duyệt.
- Thứ tự: chuyển công nghệ trước, pipeline ĐK1–ĐK4 sau.
- Triển khai: máy cục bộ trước.
- Lưu trữ: giữ SQLite ở các bước đầu (lớp API, frontend); PostgreSQL làm sau, khi đó mới quyết định chạy bằng Docker hay cài trực tiếp.
- GPU: nhóm có thể dùng GPU (máy Lightning) để chạy model mã nguồn mở; máy phát triển cục bộ không có GPU NVIDIA.
- Người dùng cho phép cài gói từ PyPI vào virtualenv `.venv` của dự án và gói npm vào thư mục frontend cho bước chuyển đổi đầu; không bao gồm GitHub, Jira, 9Router hay Docker image.

## Bước 2: frontend (chốt 06/11/2026)

- Làm lại toàn bộ phần nhìn theo hướng thị giác "Bản luật đã đánh dấu" (chọn qua vòng quyết định của impeccable, bản phác `.impeccable/mocks/decision/model-pick.html`): luật trên nền giấy trắng, mỗi vai trò quy phạm một màu dạ quang tô trên chữ, mỗi quy phạm một cờ giấy ở lề, ghi chú người duyệt như nét bút chì; màu luôn đi kèm nhãn chữ.
- Đăng nhập làm ngay ở bước này: ba vai trò quản trị, người duyệt, người tra cứu; tài khoản quản trị đầu tiên tạo bằng lệnh; người tra cứu thấy mọi kho đã công bố.
- Song ngữ Việt và Anh, WCAG 2.2 AA, ưu tiên máy tính; hai trang sơ đồ để bước 4.

## Chưa chốt

- Đã chốt 07/11/2026: Opus 5.5 qua Claude Code cho trích xuất ĐK3/ĐK4 và sinh câu trả lời; Sonnet 5.5 làm giám khảo bổ sung (xem `docs/decisions.md`).
- Cách chạy PostgreSQL (Docker hay cài trực tiếp); thời điểm đã chốt là sau 27/11.
- Nơi triển khai sau giai đoạn cục bộ và chính sách dữ liệu cho kho riêng tư khi có nhiều người dùng.
