# Recall theo ngân sách token và đóng gói theo Điều (chạy thử, 11/11/2026)

Kết quả của WP2 và WP3 trong `docs/planning/research-plan-2026-11-11.md`.
Đây là chạy thử trên tập dev: nhãn đáp án do model soạn, chưa có người duyệt, nên mọi con số chỉ để chọn cấu hình và kiểm tra công cụ, chưa dùng để kết luận.
Bảng đầy đủ và hình: `budget-curves-2026-11-11-bang.md` (sinh bằng `cli budget-report`).

## Thiết lập

Corpus v2 (`experiment-scope-v2-ve5261858b8f3`, 9 văn bản, 711 Điều), truy xuất hybrid BM25 + BGE-M3 cục bộ, không gọi model.
Bốn bộ câu hỏi chạy thử: tra cứu (131 câu có nhãn), phức tạp (30), xung đột (25), tình huống (44, có tách vấn đề `decompose-gptoss`).
ĐK1 `dk1.json`, ĐK2 `dk2.json`, ĐK3 và ĐK4 `corpus-v2/dk{3,4}-compact.json` (thiết kế chính ở mục 6 của kế hoạch).
Bộ phức tạp nay chạy trên corpus v2, nên số khác bảng 2.1 của kế hoạch (bảng đó dùng corpus v1); các lượt v2 cũ khớp số mới.
Lượt chạy: `experiments/runs/budget-2026-11-11/`, lệnh trong `experiments/runs/run-budget-curves.sh`.

## Thay đổi phương pháp trước khi đo

1. Recall theo ngân sách dùng đúng hàm đóng gói của lượt sinh câu trả lời (`indexing/packing.py`), nên hai nơi không thể lệch nhau.
2. Trước đây mỗi câu chỉ giữ 50 bản ghi đã xếp hạng, và hybrid chỉ trộn 30 ứng viên đầu của mỗi danh sách; với bản ghi ĐK2 khoảng 45 token, danh sách cạn trước 3.000 token, nên đường cong ĐK2 bị cắt cụt ở ngân sách lớn.
   Nay danh sách giữ đủ bản ghi cho ngân sách lớn nhất và hybrid nối thêm phần đuôi theo RRF trên toàn danh sách; phần đầu không đổi.
3. Mở rộng theo đồ thị của ĐK3/ĐK4 chỉ xét 50 ứng viên đầu như trước, phần sau nối thêm không mở rộng.
   Lần chạy đầu cho đồ thị xét cả danh sách sâu hơn và làm recall ĐK3 bộ xung đột ở 2.000 token rơi từ 0,43 xuống 0,39; sau khi sửa, số khớp lượt cũ.
4. Tiêu chí hoàn thành của WP2 đạt: mọi giá trị ở 500, 1.000, 2.000 token của các lượt cùng cấu hình cũ được tái lập đúng đến hai chữ số.

## Recall theo ngân sách (P0, danh sách phẳng)

| Bộ | Điều kiện | 500 | 1.000 | 2.000 | 3.000 | 6.000 |
|---|---|---|---|---|---|---|
| Tra cứu | ĐK1 | 0,56 | 0,74 | 0,85 | 0,92 | 0,98 |
| Tra cứu | ĐK2 | 0,82 | 0,88 | 0,92 | 0,95 | 0,97 |
| Phức tạp | ĐK1 | 0,37 | 0,53 | 0,69 | 0,78 | 0,94 |
| Phức tạp | ĐK2 | 0,43 | 0,62 | 0,67 | 0,73 | 0,89 |
| Xung đột | ĐK1 | 0,19 | 0,29 | 0,47 | 0,54 | 0,64 |
| Xung đột | ĐK2 | 0,21 | 0,35 | 0,43 | 0,52 | 0,62 |
| Tình huống | ĐK1 | 0,12 | 0,25 | 0,42 | 0,48 | 0,66 |
| Tình huống | ĐK2 | 0,16 | 0,25 | 0,33 | 0,42 | 0,53 |

ĐK3 và ĐK4 nằm sát ĐK2 ở mọi bộ (chênh không quá 0,05 ở 3.000 token); số đầy đủ ở tệp bảng.

Ngân sách nhỏ nhất để recall trung bình đạt ngưỡng nêu trước (0,8 cho bộ tra cứu, 0,4 cho bộ khó):

| Bộ | ĐK1 | ĐK2 | ĐK3 | ĐK4 |
|---|---|---|---|---|
| Tra cứu, recall 0,8 | 1.228 | 447 | 612 | 632 |
| Phức tạp, recall 0,4 | 784 | 394 | 323 | 323 |
| Xung đột, recall 0,4 | 1.601 | 1.518 | 1.837 | 1.839 |
| Tình huống, recall 0,4 | 1.628 | 2.598 | 2.304 | 2.304 |

Nhận xét:

- Với câu tra cứu, ĐK2 đạt cùng độ phủ với khoảng một phần ba số token của ĐK1; đây là điều đề tài tuyên bố về hiệu quả token.
- Với câu khó, lợi thế đảo chiều từ khoảng 2.000 token: đoạn liền mạch 384 token của ĐK1 kéo theo các Khoản lân cận mà câu tình huống cần.
- Bản ghi ĐK3/ĐK4 dài hơn ĐK2 (56 so với 45 token) nhưng không tốn thêm nhiều ngân sách ở bộ khó, nhờ dòng quy phạm gọn.

## Đóng gói theo Điều (WP3)

Recall của ĐK2 theo biến thể đóng gói, tập dev của bộ khó:

| Bộ | Biến thể | 1.000 | 2.000 | 3.000 | 4.000 |
|---|---|---|---|---|---|
| Phức tạp | P0 | 0,62 | 0,67 | 0,73 | 0,81 |
| Phức tạp | P1 | 0,63 | 0,70 | 0,78 | 0,82 |
| Phức tạp | P2 | 0,66 | 0,71 | 0,79 | 0,83 |
| Xung đột | P0 | 0,35 | 0,43 | 0,52 | 0,58 |
| Xung đột | P1 | 0,37 | 0,46 | 0,54 | 0,60 |
| Xung đột | P2 | 0,37 | 0,48 | 0,54 | 0,61 |
| Tình huống | P0 | 0,25 | 0,33 | 0,42 | 0,47 |
| Tình huống | P1 | 0,25 | 0,38 | 0,46 | 0,49 |
| Tình huống | P2 | 0,26 | 0,41 | 0,48 | 0,53 |

Áp quy tắc chọn đã khai báo trước (recall ĐK2 ở 3.000 token, gộp 99 câu bộ khó, phải hơn P0 ít nhất 0,03):

| Biến thể | Recall ở 3.000 token | Chênh so với P0 | Khoảng tin cậy 95% (bootstrap ghép cặp 10.000 lần) | Thắng / thua |
|---|---|---|---|---|
| P0 | 0,539 | | | |
| P1 | 0,574 | +0,035 | 0,018 đến 0,054 | 14 / 0 |
| P2 | 0,588 | +0,049 | 0,029 đến 0,071 | 19 / 0 |

Chọn P2 cho ĐK2, ĐK3 và ĐK4 (không chọn lại cho ĐK3, ĐK4), ghi trong `docs/decisions.md`.
Ở bộ xung đột, ĐK2 với P2 đạt recall 0,4 ở 1.161 token thay vì 1.518; ở bộ tình huống, 1.959 thay vì 2.598, tức đã gần ĐK1 (1.628).
Lựa chọn này dựa trên nhãn nháp; nếu nhãn người sau khi khóa đổi thứ tự P0, P1, P2, quy tắc được áp lại một lần trên dev đã khóa và ghi lý do.
Độ chính xác trích dẫn theo ký tự với P2 chỉ đo được ở lượt sinh câu trả lời (H1, WP9).

## Tải kiểm chứng trên các lượt trả lời đã có

Tính lại từ `answers.jsonl` đã lưu, không gọi model:

| Lượt | Token phải đọc mỗi phát biểu | Tỉ lệ trích dẫn tới đúng một đơn vị lá |
|---|---|---|
| Tình huống, Haiku 5.5, ĐK1 | 550 | 0,01 |
| Tình huống, Haiku 5.5, ĐK2 | 250 | 1,00 |
| Tình huống, Haiku 5.5, ĐK3 | 272 | 1,00 |
| Tình huống, Haiku 5.5, ĐK4 | 261 | 1,00 |

Người kiểm một phát biểu của ĐK2-ĐK4 đọc chưa đến một nửa số token so với ĐK1 và luôn được trỏ tới một Khoản hoặc Điểm cụ thể.

## Hiệu lực trong ngữ cảnh (thăm dò cho WP4)

Không lọc hiệu lực, và lấy ngày 11/11/2026 cho mọi câu, tỉ lệ câu có ngữ cảnh ĐK2 ở 1.000 token chứa đơn vị lỗi thời (chủ yếu NĐ 12/2022, hết hiệu lực từ 10/09/2026) là 0,34 ở bộ tra cứu, 0,33 ở bộ phức tạp, 0,32 ở bộ xung đột và 0,61 ở bộ tình huống; với ĐK1 là 0,14 đến 0,23.
Con số này không đúng nghĩa cho bộ tình huống, vì vụ việc xảy ra trước khi NĐ 12/2022 hết hiệu lực; bộ hiệu lực v1 sẽ ghi ngày áp dụng cho từng câu.

## Còn thiếu

- Độ nhạy cỡ đoạn của ĐK1 (128, 256, 512 token) đang chạy; sẽ bổ sung vào tệp bảng.
- Mọi kết luận chờ nhãn người (WP1) và lượt chạy chính (WP9).
