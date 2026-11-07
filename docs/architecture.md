# Kiến trúc Lexora

Cập nhật 07/11/2026; thay bản dự thảo MVP ngày 01/11.
Sơ đồ chi tiết và thuật toán: `docs/planning/technical-design-plan.md`; công nghệ và các bước chuyển đổi: `docs/planning/target-stack-2026-11-06.md`.

## Phạm vi theo đề cương

Pháp luật lao động Việt Nam: dự kiến 8-12 văn bản; gold extraction 40-60 điều khoản; bộ câu hỏi khoảng 150 câu, giữ khoảng 30% held-out.
Đây là mục tiêu; hiện corpus nghiên cứu có 2 văn bản và chưa có bộ câu hỏi thật.

## Các lớp

| Lớp | Vị trí | Vai trò |
|---|---|---|
| Lõi pipeline | `src/legal_ai/` (trừ `web/`, `research/`) | Python thư viện chuẩn, tái lập được: lấy văn bản, chuẩn hóa, tách cấu trúc, lược đồ `1.0.0-pilot`, kiểm chứng bằng chứng, trích xuất quy phạm, truy xuất BM25, đồ thị, hỏi đáp có dẫn nguồn |
| Nghiên cứu | `src/legal_ai/research/`, `indexing/`, `evaluation/` | Corpus có phiên bản khóa, bộ câu hỏi và đề xuất của model, chạy truy xuất ĐK1/ĐK2 |
| Lớp web | `src/legal_ai/web/` | FastAPI + Pydantic: tài khoản ba vai trò, phiên HttpOnly, token POST, kiểm tra Host/Origin, giới hạn kích thước, CSP, không ghi log request |
| Giao diện | `frontend/` | Svelte 5 + SvelteKit (TypeScript), build tĩnh và được lớp web phục vụ; song ngữ Việt/Anh |
| Lưu trữ | Tệp SQLite của workspace | Kho tri thức (`kb-store-v1`), tài khoản, corpus (`corpus-store-v1`), bộ câu hỏi (`questions-store-v1`); danh mục văn bản là tệp SQLite riêng (`catalog-v1`) |
| Model | `src/legal_ai/providers/` | Claude Code (`claude -p`, Opus 5.5) hoặc 9Router; mỗi provider một model, ngân sách gọi, không thử lại, ghi nhật ký |

## Luồng sản phẩm: kho tri thức

1. Nguồn: danh mục cục bộ hoặc link vbpl.vn (bản chụp JSON bất biến kèm SHA-256), tệp TXT/HTML/DOCX/PDF, hoặc văn bản dán.
2. Với văn bản dài, người duyệt chọn các Điều; Lexora cắt đúng nguyên văn kèm tiêu đề Chương/Mục.
3. Chuẩn hóa và tách Chương/Mục/Điều/Khoản/Điểm; mọi bằng chứng neo vào bản đã chuẩn hóa.
4. Tách quy phạm theo quy tắc (`norm-rules-v2`); câu quy tắc chưa tách được có thể gửi model (`norm-llm-v1`, chỉ kho công khai), mọi cụm model đề xuất phải khớp nguyên văn.
5. Người duyệt quyết định từng quy phạm và từng câu chưa có quy phạm, xem trước thay đổi, công bố thành phiên bản mới; phiên bản cũ không đổi.
6. Hỏi đáp chỉ dùng bằng chứng của quy phạm đã duyệt, trên các phiên bản kho được ghim vào cuộc trò chuyện.

## Luồng nghiên cứu: ĐK1-ĐK4

1. Corpus: thêm văn bản, xem cảnh báo parser, khóa phiên bản (mã băm bundle).
2. Bộ câu hỏi trên phiên bản đã khóa: hai người gán nhãn độc lập (loại câu, hành vi trả lời/từ chối, đơn vị liên quan), trao đổi bằng tệp, đối soát, khóa với chia dev/held-out theo nhóm diễn đạt.
3. ĐK1 cắt đoạn cố định, ĐK2 theo đơn vị pháp lý; cùng truy xuất BM25 và cùng cách tính Recall@K trên đơn vị chuẩn.
4. ĐK3 dùng kho quy phạm do model trích xuất trước kiểm chứng, ĐK4 dùng chính kho đó sau kiểm chứng (chưa làm).
5. Sinh câu trả lời bằng Opus 5.5 cho cả bốn điều kiện và chấm theo `docs/evaluation-protocol.md` (chưa làm).

Mỗi nhánh lưu riêng, không ghi đè; người duyệt không sửa ngầm dữ liệu của ĐK3/ĐK4.

## Nguyên tắc

- Mọi khẳng định truy được về đúng câu trong nguồn (vị trí ký tự Unicode, SHA-256); trích dẫn sai vị trí hoặc mã băm bị chặn.
- Metadata hiệu lực là thông tin có nguồn; không suy diễn hiệu lực pháp luật tại một thời điểm.
- Dẫn chiếu chưa giải quyết được giữ trạng thái rõ ràng, không tự tạo đích.
- Thiếu căn cứ hoặc câu hỏi vượt phạm vi thì từ chối có lý do.
- Không dùng LangChain, LlamaIndex hay graph database; không chia microservice.
