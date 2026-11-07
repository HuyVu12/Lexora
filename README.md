# Legal AI — Hỏi đáp pháp luật lao động

Khung triển khai đồ án RAG với Legal Knowledge Base có cấu trúc và kiểm chứng.
**Trạng thái:** đã có pilot local cho snapshot VBPL → parser/schema → kiểm tra evidence → tra cứu nguồn bằng BM25. Bản demo mới có nhập TXT, duyệt gộp revision và hỏi đáp trên tri thức đã duyệt; generation qua 9Router là tùy chọn. Chưa có LLM extraction hoặc pipeline nghiên cứu ĐK1–ĐK4 hoàn chỉnh. Xem [luồng demo và chat](docs/features/reviewed-kb-chat.md).

**Trọng tâm mới:** [Knowledge graph và evidence viewer local](docs/features/knowledge-graph-pilot.md). Đã có giao diện graph tự chứa dữ liệu, mở được bằng browser; quy phạm mới là ứng viên needs_review cho đến khi người dùng duyệt nhập. Chưa có GraphRAG nghiên cứu hoàn chỉnh.

**Bản mới 03/11:** [Graph thực thể–quan hệ với quy phạm làm trung tâm](docs/features/entity-relation-graph.md), đã tách chủ thể/hành động/đối tượng/tính quy phạm và ràng buộc có quote riêng trên một phần pilot. Mở `data/kb/entity-relation-review/index.html` để review.

## Bắt đầu
1. Đọc `docs/planning/implementation-plan.md` để xem lịch và tiêu chí bàn giao.
   Bản chi tiết: [kiến trúc, thuật toán và kế hoạch kỹ thuật](docs/planning/technical-design-plan.md), gồm sơ đồ Mermaid và cấu hình demo theo Lightning Free.
2. Đọc `docs/architecture.md` và `docs/data-contracts.md` trước khi xây module.
3. Kha phụ trách schema/extraction/validation/KB; Vũ phụ trách retrieval/RAG/ĐK1–ĐK2.
4. Hai thành viên cùng thu thập dữ liệu, gán nhãn chéo, đánh giá và viết báo cáo.

## Cấu trúc
- `src/legal_ai/`: module Python; schema, ingestion, normalization, validation kỹ thuật, provider boundary và BM25 đã có code.
- `configs/`: cấu hình dự thảo, bốn điều kiện thực nghiệm riêng biệt.
- `data/`: hai snapshot VBPL và artifact pilot local; bulk data được loại khỏi Git.
- `prompts/`: nơi quản lý phiên bản prompt extraction, answer và evaluation.
- `tests/`: unittest offline, fixture tổng hợp và câu pilot nháp.
- `experiments/`: manifest và kết quả thực nghiệm tái lập.
- `apps/demo/`: hướng dẫn chạy ứng dụng local; lớp web ở `src/legal_ai/web/`, giao diện SvelteKit ở `frontend/`.
- `scripts/`: các entry point CLI sẽ xây trong tuần đầu.
- `docs/`: đề cương gốc, thiết kế, kế hoạch, guideline và báo cáo.
- `infra/lightning/`: quy trình vận hành máy tính toán.

## Chạy và kiểm tra
Yêu cầu Python 3.11+, runtime chỉ dùng thư viện chuẩn. Không cần cài package hoặc truy cập mạng để review trên artifact đã tải:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m legal_ai.cli search data/normalized/pilot-v2 'Tiền lương thử việc ít nhất bao nhiêu phần trăm?' --top-k 2
```

Hướng dẫn build/validate/evaluate và giới hạn: [gói review local](docs/planning/local-pilot-review-2026-11-02.md). Các lệnh thí nghiệm LLM trong kế hoạch vẫn chưa được triển khai. `pyproject.toml` có metadata đóng gói; chưa kiểm chứng build/install và không cần dùng cho review.

Dùng Python cho pipeline; lựa chọn thư viện, mô hình và nơi lưu vector được chốt sau pilot. Không cần dựng microservice hoặc graph database cho MVP. Giữ nguyên `AGENTS.md` đã có; thông tin cấu trúc mới nằm trong README này.
