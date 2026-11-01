# Legal AI — Hỏi đáp pháp luật lao động

Khung triển khai đồ án RAG với Legal Knowledge Base có cấu trúc và kiểm chứng.
**Trạng thái:** skeleton và kế hoạch; chưa có dữ liệu thật, mô hình, hoặc pipeline chạy được.

## Bắt đầu
1. Đọc `docs/planning/implementation-plan.md` để xem lịch và tiêu chí bàn giao.
   Bản chi tiết: [kiến trúc, thuật toán và kế hoạch kỹ thuật](docs/planning/technical-design-plan.md), gồm sơ đồ Mermaid và cấu hình demo theo Lightning Free.
2. Đọc `docs/architecture.md` và `docs/data-contracts.md` trước khi xây module.
3. Kha phụ trách schema/extraction/validation/KB; Vũ phụ trách retrieval/RAG/ĐK1–ĐK2.
4. Hai thành viên cùng thu thập dữ liệu, gán nhãn chéo, đánh giá và viết báo cáo.

## Cấu trúc
- `src/legal_ai/`: module Python theo các bước pipeline, hiện chỉ có mô tả trách nhiệm.
- `configs/`: cấu hình dự thảo, bốn điều kiện thực nghiệm riêng biệt.
- `data/`: nguồn, bản chuẩn hóa, KB, tập đánh giá và chỉ mục; chưa có dữ liệu thật.
- `prompts/`: nơi quản lý phiên bản prompt extraction, answer và evaluation.
- `tests/`: các nhóm kiểm thử cần xây; chưa có test tự động.
- `experiments/`: manifest và kết quả thực nghiệm tái lập.
- `apps/demo/`: giao diện demo tối thiểu, triển khai sau pipeline.
- `scripts/`: các entry point CLI sẽ xây trong tuần đầu.
- `docs/`: đề cương gốc, thiết kế, kế hoạch, guideline và báo cáo.
- `infra/lightning/`: quy trình vận hành máy tính toán.

## Chạy và kiểm tra
Chưa có lệnh chạy ứng dụng hoặc dependency lockfile. Các lệnh CLI trong kế hoạch là giao diện dự kiến, chưa được triển khai. Có thể kiểm tra cây thư mục bằng `rg --files --hidden`.

Dùng Python cho pipeline; lựa chọn thư viện, mô hình và nơi lưu vector được chốt sau pilot. Không cần dựng microservice hoặc graph database cho MVP. Giữ nguyên `AGENTS.md` đã có; thông tin cấu trúc mới nằm trong README này.
