# Đặc tả tính năng Lexora

Các tài liệu trong thư mục này mô tả tính năng và hướng phát triển sản phẩm.
Trạng thái đặc tả không đồng nghĩa tính năng đã được triển khai hoặc đã đưa vào lịch/Jira; cột Trạng thái ghi rõ phần nào đã chạy.

| Mã | Tính năng | Trạng thái (07/11/2026) | Tài liệu |
|---|---|---|---|
| F-KB-02 | Vòng đời kho tri thức: nhập (danh mục, link vbpl.vn chọn Điều, tệp, dán), duyệt và sửa quy phạm, tạo mới hoặc gộp có xem trước, công bố phiên bản, hỏi đáp nhiều kho | Đã triển khai trong app FastAPI + SvelteKit; tách bằng AI qua Claude Code hoặc 9Router cho kho công khai | [Thiết kế chi tiết](knowledge-base-workflow.md) |
| RKB-CHAT | Hỏi đáp theo phiên bản kho đã duyệt, dẫn nguồn nguyên văn | Đã triển khai, có regression test và E2E | [Reviewed KB chat](reviewed-kb-chat.md) |
| RES-QA | Corpus nghiên cứu, gán nhãn bộ câu hỏi độc lập, đối soát và khóa bộ câu hỏi | Đã triển khai bản đầu; chưa có bộ câu hỏi thật | [Corpus và gán nhãn](question-annotation.md) |
| KG-PILOT | Đồ thị cấu trúc và dẫn chiếu có bằng chứng | Bản pilot 02/11; trong app thay bằng trang sơ đồ Cytoscape | [Graph pilot](knowledge-graph-pilot.md) |
| ER-PILOT | Đồ thị thực thể-quan hệ lấy quy phạm làm trung tâm | Bản pilot 03/11; nền của bộ quy tắc `norm-rules-v2` | [Entity/relation graph](entity-relation-graph.md) |
| F-KB-01 | Kho tri thức pháp lý riêng cho luật sư | Yêu cầu và thiết kế đề xuất, chưa triển khai | [Đặc tả chi tiết](private-legal-knowledge-base.md) |

Tài liệu nền: [kiến trúc](../architecture.md), [hợp đồng dữ liệu](../data-contracts.md), [hướng dẫn gán nhãn](../annotation-guidelines.md), [giao thức thực nghiệm](../evaluation-protocol.md), [tiến độ và việc tiếp theo](../planning/progress-2026-11-07.md).
