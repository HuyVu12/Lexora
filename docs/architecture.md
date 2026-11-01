# Kiến trúc MVP

## Phạm vi theo đề cương
Pháp luật lao động Việt Nam: dự kiến 8–12 văn bản, 60–100 điều khoản; gold extraction 40–60 điều khoản; bộ RAG khoảng 150 câu, giữ lại 30% held-out. Đây là mục tiêu cần xác nhận sau pilot, không phải dữ liệu đã có.

## Luồng xử lý
Nguồn chính thống → snapshot bất biến + checksum → chuẩn hóa → phân cấp Chương/Điều/Khoản/Điểm → extraction rule-based hoặc LLM → KB ứng viên → validation tự động → KB hợp lệ → index → retrieval → context → answer + evidence.

Nhánh ĐK1 chia đoạn cố định từ bản chuẩn hóa; ĐK2 chia theo cấu trúc; ĐK3 dùng KB LLM trước validation; ĐK4 dùng chính KB đó sau validation. Lưu riêng từng nhánh, không ghi đè KB trước kiểm chứng. Review thủ công không nhập ngầm vào ĐK4; nếu có thì ghi thành biến thể riêng.

## Quyết định thiết kế dự thảo
- Một codebase Python, chạy batch bằng CLI; giao diện mỏng gọi cùng service.
- JSONL làm định dạng trao đổi ban đầu; chọn SQLite hoặc kho khác sau pilot. Không bắt buộc database server.
- Adapter cho embedding, LLM và vector index; không khóa nhà cung cấp API miễn phí.
- Metadata hiệu lực là thông tin có nguồn, không suy diễn pháp luật tại một thời điểm bất kỳ.
- Chỉ dùng evidence hợp lệ trong câu trả lời; dẫn chiếu chưa giải quyết được phải có trạng thái rõ ràng.
- Không đủ nguồn hoặc câu hỏi vượt phạm vi thời gian: yêu cầu làm rõ hoặc từ chối có lý do.

## Hợp đồng giữa hai thành viên
Kha bàn giao `documents.jsonl`, `units.jsonl`, `claims.raw.jsonl`, `claims.validated.jsonl`, `validation-report.jsonl` và manifest phiên bản. Vũ nhận qua schema chung, không đọc cấu trúc nội bộ của extractor. Ngày 08/11 cần một lát cắt end-to-end nhỏ, không yêu cầu toàn bộ corpus hoàn chỉnh.

## MVP và mở rộng
MVP bắt buộc schema/ref/evidence validation, retrieval, dẫn nguồn và bốn điều kiện đánh giá. Graph traversal nâng cao, semantic conflict detection và review UI chỉ làm sau mốc MVP 27/11; không đánh đổi bộ đánh giá lấy giao diện đẹp.
