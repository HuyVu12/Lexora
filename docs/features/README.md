# Đặc tả tính năng Lexora

Các tài liệu trong thư mục này mô tả tính năng và hướng phát triển sản phẩm. Trạng thái đặc tả không đồng nghĩa tính năng đã được triển khai hoặc đã được đưa vào lịch/Jira.

| Mã | Tính năng | Trạng thái | Tài liệu |
|---|---|---|---|
| F-KB-01 | Kho tri thức pháp lý riêng cho luật sư | Đã ghi nhận yêu cầu; thiết kế đề xuất, chưa triển khai | [Đặc tả chi tiết](private-legal-knowledge-base.md) |
| F-KB-02 | Vòng đời kho: nhập, review/chỉnh sửa, tạo mới hoặc gộp có xem trước, hỏi đáp nhiều kho | Thiết kế chi tiết 06/11; demo 08/11 làm phần D1-D5 | [Thiết kế chi tiết](knowledge-base-workflow.md) |
| RKB-CHAT | Nguồn local đã ghim và chat theo revision được duyệt | Đã có UI local và regression tests | [Reviewed KB chat](reviewed-kb-chat.md) |
| KG-PILOT | Graph cấu trúc/dẫn chiếu có evidence | Đã có bản local để review | [Graph pilot](knowledge-graph-pilot.md) |
| ER-PILOT | Graph thực thể–quan hệ lấy quy phạm làm trung tâm | Rule pilot có thành phần semantic, tất cả needs_review | [Entity/relation graph](entity-relation-graph.md) |

Ưu tiên demo 08/11 đã chuyển sang upload → review/confirm KB → hỏi đáp, do Vũ phụ trách. Đây mới là phạm vi thực thi đã đưa vào Jira, chưa có toàn bộ luồng chạy được: [kế hoạch tuần và provider/quota](../planning/demo-upload-review-chat-2026-11-03.md).

Tài liệu nền: [kiến trúc](../architecture.md), [hợp đồng dữ liệu](../data-contracts.md), [thiết kế kỹ thuật](../planning/technical-design-plan.md), [kế hoạch tiến độ](../planning/implementation-plan.md).
