# Giám sát hệ thống: vai trò `dev` và trang Giám sát

Trang Giám sát (`/dev`) cho nhóm theo dõi lượt gọi model, mức sử dụng, tiến độ thực nghiệm và báo cáo gửi giảng viên ngay trong app.
Trang chỉ hiện số đếm và metadata, không bao giờ hiện nội dung câu hỏi, prompt, câu trả lời hay nguyên văn luật.

## 1. Vai trò

| Vai trò | Xem trang Giám sát | Đổi hạn mức, công tắc, ghi chú báo cáo | Việc khác |
|---|---|---|---|
| `dev` | Có | Có | Hỏi đáp như người tra cứu; xem trang Nghiên cứu > Kết quả |
| `admin` | Có | Không | Quản lý tài khoản, mọi việc của người duyệt |
| `reviewer`, `reader` | Không | Không | Như cũ |

- Tạo tài khoản `dev`: quản trị vào Tài khoản, chọn vai trò "Giám sát"; hoặc `demo-build` tạo sẵn tài khoản `dev` với mật khẩu in một lần.
- Store cũ (trước vai trò `dev`) được tự nâng cấp khi app mở, giữ nguyên tài khoản, phiên đăng nhập và chủ sở hữu cuộc trò chuyện.

## 2. Những gì được ghi lại (`ops-store-v1`, cùng tệp SQLite của workspace)

- `model_calls`: mỗi lượt gọi model của app (trả lời bằng model, tách quy phạm, đề xuất nhãn, embedding) gồm thời điểm, tính năng, mục đích, nhà cung cấp, model, tài khoản kích hoạt, kết quả (thành công, lỗi, bị chặn), mã lỗi, số request, token vào/ra/suy luận, chi phí niêm yết, thời gian.
- `usage_events`: đăng nhập (thành công, sai mật khẩu, bị khóa) và câu hỏi (chế độ, có tìm theo ngữ nghĩa, trạng thái, số trích dẫn, số kho, thời gian trả lời).
- `ops_settings`, `ops_changes`: hạn mức, công tắc, ghi chú báo cáo và lịch sử thay đổi (ai, lúc nào, trước và sau).
- Các lượt chạy bằng dòng lệnh (`kb-extract`, `answer-run`...) không đi qua app; tab Thực nghiệm đọc chúng từ `experiments/runs/`.

## 3. Hạn mức và công tắc

- Mỗi tính năng có một công tắc và một hạn mức mỗi ngày (theo ngày của máy chủ); để trống là không giới hạn.
- Lượt gọi bị chặn trước khi gửi đi (mã `disabled_by_dev` hoặc `daily_limit_reached`), được ghi là "bị chặn" và không tính vào hạn mức.
- Hạn mức này nằm trên ngân sách lượt chạy đặt bằng cờ khi khởi động (`--proposal-max-calls`, `--extract-claude-max-calls`...); cả hai đều phải còn thì lượt gọi mới đi.
- Cảnh báo: tỉ lệ lỗi hôm nay trên 20% (từ 5 lượt), tính năng bị tắt, đã dùng từ 80% hạn mức hoặc ngân sách lượt chạy, có lượt bị chặn.
- Nhãn trạng thái cạnh tiêu đề trang (mọi tab) cho biết không có cảnh báo hay có bao nhiêu cảnh báo, kèm giờ cập nhật; bấm vào để xem danh sách ở tab Tổng quan.
- Các tab Tổng quan, Gọi model và Sử dụng tự làm mới mỗi phút khi trang đang mở; nút làm mới nằm cạnh giờ cập nhật.

## 4. Các tab

| Tab | Nội dung |
|---|---|
| Tổng quan | Cảnh báo (chỉ khi có); bốn số hôm nay (gọi model, câu hỏi, lượt lỗi kèm bị chặn, token kèm chi phí) với biểu đồ cột nhỏ 14 ngày và tổng 7 ngày, gộp thành một dòng khi cả tuần không có hoạt động; mỗi tính năng gọi model một dòng: trạng thái (đang bật, đã tắt, hết hạn mức, chưa bật trong lần chạy này), model, lượt hôm nay so với hạn mức và ngân sách lượt chạy, công tắc và hạn mức (chỉ dev sửa); tách quy phạm đang chạy và thay đổi gần đây khi có; thông tin hệ thống mở ở cuối trang |
| Gọi model | Biểu đồ theo ngày (theo kết quả, theo tính năng) khi khoảng thời gian có lượt gọi, bảng theo model (lỗi, token, trung vị, p95, chi phí), mã lỗi khi có, 10 lượt gần nhất (mở rộng tới 50) |
| Sử dụng | Phiên đăng nhập, câu hỏi, tỉ lệ không tìm thấy căn cứ, thời gian trả lời, biểu đồ câu hỏi và đăng nhập, cách trả lời, tài khoản theo vai trò |
| Kho tri thức | Các kho, bản nháp đang chờ và số quy phạm chưa quyết định, số lần công bố theo người duyệt, bộ câu hỏi, bộ gold |
| Thực nghiệm | Số lượt chạy theo loại, các lượt trích xuất, tiến độ bảng kiểm tra quy phạm bị loại, mọi lượt chạy |
| Báo cáo | Trạng thái RQ1-RQ3, so sánh model, "Bị loại vì đâu", ghi chú của nhóm; nút tải tệp HTML tự chứa để gửi giảng viên |

Thông tin hệ thống (commit, thời điểm khởi động và build giao diện, Python, store, các tính năng bật khi khởi động; không hiện khóa trong `.env`) mở bằng nút "Thông tin hệ thống" ở cuối tab Tổng quan; liên kết cũ `/dev#system` mở sẵn phần này.

## 5. Báo cáo gửi giảng viên

- Số liệu lấy trực tiếp từ `experiments/runs/` và store mỗi lần mở tab, nên luôn là số mới nhất.
- Ghi chú (giới hạn, việc tiếp theo, xin ý kiến) do tài khoản `dev` soạn trong app, mỗi dòng một ý, tối đa 12 dòng mỗi mục.
- "Tải báo cáo HTML" trả về một tệp HTML tự chứa (`/api/dev/report.html`), mở được trên mọi trình duyệt và gửi kèm thư; giảng viên không cần tài khoản.

## 6. API

`GET /api/dev/overview` (kèm `trend`: 14 ngày gần nhất, mỗi ngày số lượt gọi, lỗi, bị chặn, token, chi phí, câu hỏi và lượt đăng nhập thành công), `/api/dev/calls?days=`, `/api/dev/usage?days=`, `/api/dev/kb`, `/api/dev/system`, `/api/dev/experiments`, `/api/dev/report`, `/api/dev/report.html` (admin và dev); `POST /api/dev/controls`, `/api/dev/notes` (chỉ dev).
