# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Người xem chính hiện nay là hội đồng chấm đồ án tốt nghiệp và giảng viên.
Khi bảo vệ, nhóm sinh viên trực tiếp thao tác demo, hội đồng theo dõi qua máy chiếu hoặc màn hình lớn.
Vì vậy mọi màn hình phải đọc được từ xa và tự giải thích được khi người trình bày lướt qua nhanh.

Ngoài buổi bảo vệ, nhóm dùng giao diện để trình diễn và kiểm thử.
Công việc nghiên cứu chính (xây dữ liệu, chạy thực nghiệm) đi qua CLI.

Từ 06/11/2026 sản phẩm được định hướng cho người dùng thật, không chỉ để trình diễn.
Người dùng thật là pháp chế và nhân sự doanh nghiệp.
Người duyệt (pháp chế, luật sư nội bộ) nhập văn bản, duyệt và công bố quy phạm; người tra cứu (nhân sự) hỏi đáp trên kho đã duyệt để xử lý công việc lao động hằng ngày.
Kết quả vẫn không phải tư vấn pháp lý; người tra cứu luôn được dẫn về nguyên văn để tự đối chiếu.
Giai đoạn đầu chạy trên máy cục bộ, có đăng nhập với ba vai trò (chốt 06/11/2026): quản trị tạo, khóa tài khoản và đổi vai trò; người duyệt nhập, duyệt và công bố; người tra cứu chỉ hỏi đáp và xem các kho đã công bố, không thấy bản nháp.
Tài khoản quản trị đầu tiên tạo bằng lệnh trên máy; không có tự đăng ký.

## Product Purpose

Lexora là đồ án tốt nghiệp về hỏi đáp pháp luật lao động Việt Nam theo hướng RAG, trên một kho tri thức có cấu trúc và được kiểm chứng.
Văn bản luật được tách thành các quy phạm (chủ thể, hành vi, tính quy phạm, điều kiện, ngoại lệ...), mỗi thành phần neo vào đoạn trích nguyên văn.
Người duyệt đối chiếu từng quy phạm với nguyên văn; chỉ quy phạm đã duyệt mới được dùng để trả lời, kèm trích dẫn kiểm tra được.

Câu hỏi nghiên cứu: so với truy xuất trên đoạn cắt cố định hoặc cắt theo cấu trúc, kho quy phạm có bằng chứng và đã kiểm chứng có giúp truy xuất đúng căn cứ hơn, trích dẫn chính xác hơn và từ chối đúng khi thiếu căn cứ hay không.

Thành công trong buổi bảo vệ: hội đồng hiểu đề tài giải quyết vấn đề gì, thấy được luồng nhập, duyệt, hỏi đáp có trích dẫn hoạt động thật, và thấy rõ phần nào đã làm xong, phần nào còn trong kế hoạch.

## Positioning

Mỗi câu trả lời chỉ về đúng câu trong luật: trích dẫn khớp nguyên văn đến từng ký tự, kèm vị trí ký tự Unicode và mã SHA-256 của văn bản đã chuẩn hóa.
Máy chỉ đề xuất; con người quyết định tri thức nào được vào kho, và mọi chỉnh sửa đều neo vào nguyên văn.
Không tìm thấy căn cứ thì hệ thống nói rõ là không có, thay vì đoán.

## Operating Context

Chạy cục bộ trên một máy, server loopback một người dùng (`python -m legal_ai.demo`).
Luồng chính trên giao diện: nhập văn bản (thư viện có checksum, tệp TXT, dán nội dung), duyệt quy phạm cạnh nguyên văn, xem trước và công bố thành phiên bản mới của kho, hỏi đáp trên một đến năm kho, xem sơ đồ quy phạm và sơ đồ cấu trúc văn bản.
Thiết kế thực nghiệm gồm bốn cấu hình ĐK1 đến ĐK4 (đoạn cắt cố định, đoạn theo cấu trúc, kho quy phạm do mô hình ngôn ngữ trích xuất trước và sau kiểm chứng).

## Capabilities and Constraints

Hiện tại: backend Python 3.11+, chỉ dùng thư viện chuẩn; không có bước build, không có phụ thuộc npm.
Giao diện là HTML, CSS và JavaScript thuần do server phục vụ; hai trang sơ đồ là tệp HTML tự chứa với CSP chặt.

Công nghệ mục tiêu (đã chốt 06/11/2026, chưa triển khai; chi tiết trong `docs/planning/target-stack-2026-11-06.md`):
lõi pipeline giữ Python thuần để tái lập thực nghiệm; lớp web FastAPI + Pydantic; PostgreSQL (pgvector khi cần) ở bước sau; frontend Svelte 5 + SvelteKit (xuất tĩnh) với TypeScript; giữ SQLite ở bước đầu; sơ đồ bằng Cytoscape.js; LLM tiếp tục qua 9Router.
Mặc định không gọi mạng; gọi mô hình ngôn ngữ qua 9Router là tùy chọn, phải được bật rõ ràng và chỉ dùng cho kho công khai.

Thuật ngữ cốt lõi có định nghĩa kèm ví dụ hiện khi rê chuột, nguồn duy nhất là `src/legal_ai/glossary.py`.
Quy phạm trích xuất luôn ở trạng thái cần duyệt cho đến khi người duyệt chấp nhận; không được trình bày như sự thật pháp lý đã xác minh.
Hiệu lực pháp luật của văn bản chưa được xác minh.

Yêu cầu đã chốt nhưng chưa hiện thực: giao diện song ngữ Việt và Anh.
Cách chọn ngôn ngữ và phạm vi dịch (giao diện, thuật ngữ, nội dung trang giới thiệu) chưa quyết định; văn bản luật và trích dẫn luôn giữ nguyên tiếng Việt.

## Brand Commitments

Tên sản phẩm: Lexora.
Không ghi tên trường, giảng viên hướng dẫn hay thành viên nhóm trên giao diện.

## Evidence on Hand

Dữ liệu demo là dữ liệu minh họa tổng hợp, luôn được gắn nhãn "Dữ liệu minh họa".
Có bản chụp VBPL và artifact pilot cục bộ trong `data/` (không đưa vào Git).
Chưa có kết quả thực nghiệm, số liệu đánh giá hay phản hồi người dùng; không được bịa số liệu, kết quả hoặc lời nhận xét.
Các con số về bộ dữ liệu (khoảng 150 câu hỏi, 40 đến 60 điều khoản gán nhãn) là mục tiêu theo đề cương, chưa phải dữ liệu đã có.

## Product Principles

1. Truy vết trước, trôi chảy sau: mọi phát biểu phải dẫn được về nguyên văn; thiếu căn cứ thì nói rõ.
2. Trung thực về trạng thái: luôn tách bạch phần đã làm xong với phần còn trong kế hoạch, và đã duyệt với chưa duyệt.
3. Tự giải thích: người không chuyên luật vẫn hiểu được từng thuật ngữ và từng bước mà không cần người trình bày giảng lại.
4. Riêng tư mặc định: không gửi dữ liệu ra ngoài máy nếu người dùng chưa đồng ý cho từng lượt.

## Accessibility & Inclusion

Yêu cầu WCAG 2.2 mức AA: đủ tương phản, thao tác được hoàn toàn bằng bàn phím, có trạng thái focus rõ ràng.
Phải đọc được trên máy chiếu ở khoảng cách phòng bảo vệ.
Giao diện song ngữ Việt và Anh (xem phần ràng buộc ở trên).
