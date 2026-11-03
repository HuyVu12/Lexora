# Nhật ký quyết định

| Ngày | Quyết định | Căn cứ / trạng thái |
|---|---|---|
| 31/10/2026 | Bắt đầu từ chưa có code/dữ liệu | Người dùng xác nhận |
| 31/10/2026 | Giữ lịch 08/11, 27/11, 20/12 và phân công đề cương | Người dùng xác nhận |
| 31/10/2026 | Lightning AI dự kiến, ưu tiên miễn phí, chưa có ngân sách GPU | Người dùng xác nhận; chưa kiểm tra tài khoản |
| 31/10/2026 | Skeleton Python module; trao đổi JSONL; model/index/storage chờ pilot | Đề xuất triển khai, chưa có benchmark |
| 01/11/2026 | Giữ hai người và hạn 20/12; Lightning Free; ưu tiên chất lượng demo; có thể mở rộng phạm vi; sơ đồ dùng Mermaid | Người dùng xác nhận |
| 01/11/2026 | Thêm thiết kế kỹ thuật chi tiết; tách hồ sơ DEMO và ĐK1–ĐK4; đề xuất hybrid retrieval, evidence-first answer và pilot model | Xem `planning/technical-design-plan.md`; schema/model/tham số vẫn cần pilot, chưa triển khai |
| 02/11/2026 | Pilot đầu tiên chọn hợp đồng/thử việc, ưu tiên `vbpl.vn`; cho phép tải hai văn bản chính thống | Người dùng xác nhận trong phiên làm việc; không mở quyền ghi Jira/GitHub |
| 02/11/2026 | Triển khai schema `1.0.0-pilot`, parser/evidence checks, CPU lexical retrieval và provider boundary để review local | Chưa phải schema NormClaim/validator đầy đủ hoặc ĐK1–ĐK4; giữ status pháp lý unknown, không dùng paid fallback |
| 02/11/2026 | Đổi trọng tâm trước mắt sang knowledge graph: xem Điều/Khoản, dẫn chiếu, quy phạm và mở bằng chứng | Người dùng xác nhận; triển khai local riêng trong `docs/features/knowledge-graph-pilot.md`, chưa cập nhật Jira/GitHub |
| 03/11/2026 | Ưu tiên graph thực thể–quan hệ, quy phạm làm trung tâm, thành phần có bằng chứng riêng | Người dùng yêu cầu triển khai; quy tắc local hiện tạo 8 ứng viên semantic và 4 fallback, tất cả needs_review; chưa gọi model hoặc cập nhật external |
| 03/11/2026 | Demo tuần này giao Vũ: upload → entities/KB nháp → người dùng confirm → hỏi đáp trên published revision; ưu tiên free qua 9Router đã host | Người dùng xác nhận. Đã cập nhật 32 Jira issue và tạo SCRUM-99–102, đọc lại đủ 36 issue; status giữ To Do. Catalog router đọc được, chưa gọi inference hoặc xác minh quota upstream còn lại. Xem `planning/demo-upload-review-chat-2026-11-03.md` |

Các mục cần chốt trước 03/11: quota/GPU thực tế; model và embedding revision; schema entity/relation; danh sách corpus; lưu trữ/index; số giờ làm của từng thành viên. Nếu quá hạn, ghi quyết định thu hẹp hoặc điều chỉnh với giảng viên.
