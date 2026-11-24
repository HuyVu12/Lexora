# Hướng dẫn duyệt nhãn 24/11/2026

## Vũ: trang duyệt có gợi ý

1. Mở `experiments/review-pack-2026-11-24/review.html` bằng Chrome hoặc Edge (không cần mạng).
2. Ô "Người duyệt" nhập `huyvu`; tiến độ tự lưu trong trình duyệt theo tên này, đóng trang mở lại vẫn còn.
3. Làm lần lượt năm tab; mỗi mục đọc phần nguyên văn được tô vàng, đọc gợi ý của model, rồi chọn.
4. Phím tắt: `Enter` đồng ý với gợi ý và sang mục sau, `1`-`9` chọn phương án khác, `j`/`k` mục sau/trước; tab gold có `n` (không có quy phạm) và `+` (thêm quy phạm).
5. Xong mỗi tab bấm "Xuất tệp kết quả", lưu tệp vào thư mục `experiments/review-pack-2026-11-24/results/`, rồi báo để chuyển và nhập lên máy chủ.

| Tab | Số mục | Cần chú ý |
|---|---|---|
| Gold quy phạm | 101 câu | 47 câu tin cậy thấp (lọc "Độ tin cậy thấp"); mỗi ô phải là cụm chép nguyên văn từ câu, ô sai sẽ đỏ; câu chỉ hướng dẫn cách ghi hay định nghĩa thì có thể là không có quy phạm |
| Hiệu lực | 84 dòng | Model gợi ý "đúng" cả 84 dòng: đừng bấm hàng loạt; xem kỹ hl-a05, hl-b01, hl-d05 (có thể thiếu đơn vị) |
| Liên kết | 35 câu | l26-l29 dựa trên quy định đã hết hiệu lực từ 07/08/2025 (NĐ 219/2025); l04, l09, l12, l16, l25, l34 có thể thiếu đơn vị; l05, l23 có thể không cần B; l14 tin cậy thấp |
| Sửa đổi | 100 cạnh | 95 gợi ý đúng; xem kỹ dòng 3, 53, 79, 80, 90 |
| Kiểm tra loại bỏ | 104 quy phạm | 26 mục tin cậy thấp; nhãn: sai, diễn đạt, đúng nhờ ngữ cảnh, đúng, không rõ |

Ước tính: 4-6 giờ cho cả năm tab nếu chủ yếu đồng ý gợi ý.
Trên máy chủ (https://vlexora.duckdns.org), Vũ còn duyệt đề xuất của ba bộ khó (90 câu) và bộ tra cứu; hai bộ mới (hiệu lực, cần liên kết) đã được duyệt ở trang này nên không cần gán lại trên máy chủ.

## Kha: gán độc lập, không xem gợi ý

Trên máy chủ, chế độ không xem đề xuất:

| Việc | Còn lại | Ghi chú |
|---|---|---|
| Bộ tra cứu v1 | sửa 11 câu lệch | danh sách ở `experiments/label-agreement-2026-11-15/README.md` |
| Bộ tình huống | 2/35 | |
| Bộ xung đột | 20/25 | |
| Bộ phức tạp | 30/30 | |
| Bộ hiệu lực v1 (mới) | 30/30 | câu không ghi ngày hiểu là hỏi tại 11/11/2026 |
| Bộ cần liên kết v1 (mới) | 35/35 | gán mọi đơn vị cần cho câu trả lời đủ, kể cả đơn vị được dẫn chiếu tới |
| Kiểm tra quy phạm bị loại | 104/104 | |

Cạnh sửa đổi (100 dòng): mở tệp `review-blind.html` (gửi riêng cho Kha), tab "Sửa đổi", nhập tên `kha`, xuất tệp kết quả và gửi lại.
Trang này không có gợi ý; các tab khác của nó Kha không cần làm vì đã làm trên máy chủ.

## Sau khi duyệt

`scripts/review_pack/convert.py` chuyển tệp xuất: gold thành tệp nhãn `lexora-gold-labels-v1` của huyvu, nhập lên máy chủ; quy phạm bị loại thành nhãn của huyvu trong bộ kiểm tra; ba bảng kiểm thành CSV đúng định dạng gốc.
Mọi việc nhập lên máy chủ đều sao lưu store trước.
Gợi ý là của model, không phải kết luận pháp lý; người duyệt là người quyết định.
