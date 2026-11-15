# Đồng thuận nhãn của Kha với nhãn AI, bộ câu hỏi thực nghiệm v1 (15/11/2026)

Đây là đồng thuận **người với model**, không phải người với người.
Đề cương yêu cầu kappa giữa hai người gán độc lập; số liệu này chỉ là kiểm tra chất lượng và là tham khảo bổ sung.

## Dữ liệu

- Store: bản sao lưu 03:30 ngày 15/11/2026 của store chung trên VM (`lexora-20261115.sqlite`, SHA-256 `067ec83b12f4e132d72802407e83ea9278682522dcc576fe36141f2622f7653f`), chép về `data/kb/vm-lexora-20261115.sqlite`.
- Bộ câu hỏi `qe1ae05433e9f` (152 câu, corpus `veaeaad4a6edc`, 94 Điều).
- Người: tài khoản `kha`, 152/152 nhãn, chế độ "Không xem đề xuất"; cả 152 nhãn có provenance `proposals_shown: false` và mọi trường là `own`.
- Model: đề xuất lưu sẵn của Opus 5.5 (phiên agent 08/11/2026), một đề xuất cho mỗi câu.
  Chính model này soạn câu hỏi cùng lúc với đề xuất, nên đề xuất gần với ý định khi soạn câu; đồng thuận vì thế dễ cao hơn so với hai người gán độc lập.
- 45 nhãn Kha gán nhầm ở tài khoản `admin` đã bị xóa ngày 14/11/2026 (có bản sao lưu `before-delete-admin-labels-20261114-1326.sqlite` trên VM) và không có trong phép so sánh.

Chạy lại:

```powershell
.venv\Scripts\python experiments/label-agreement-2026-11-15/compare.py data/kb/vm-lexora-20261115.sqlite qe1ae05433e9f kha experiments/label-agreement-2026-11-15/kha-vs-model.json
```

## Kết quả

| Chỉ số | 152 câu | Bỏ 6 câu dính lỗi form |
|---|---|---|
| Kappa loại câu | 0,950 (khớp 97,4%) | 0,948 |
| Kappa trả lời / từ chối | 0,922 (khớp 98,0%) | 0,921 |
| Dice đơn vị trung bình | 0,953 | 0,976 |
| Khớp hoàn toàn tập đơn vị | 92,8% | 96,6% |
| Khớp cùng Điều (câu cả hai cùng "trả lời") | 100% (128 câu) | 100% (122 câu) |
| Khớp hoàn toàn cả ba trường | 141/152 (92,8%) | 141/146 (96,6%) |

Theo thang thường dùng, kappa trên 0,8 là đồng thuận gần như hoàn toàn.
Kha và model không lệch nhau ở Điều nào; mọi chỗ lệch về đơn vị đều nằm trong cùng một Điều.

## 11 câu lệch

| Câu | Lệch | Nguyên nhân | Đề nghị |
|---|---|---|---|
| 47, 56, 75, 82, 85, 126 | Kha chọn Điểm, model chọn Khoản cha | **Lỗi form**: ô tìm đơn vị chỉ hiện đơn vị lá, nên Khoản có câu dẫn chứa quy định chính không chọn được; Kha ghi chú đủ cả 6 câu | Gán lại sau khi bản sửa lên VM: chọn Khoản cha (và giữ Điểm nếu Điểm đó cũng là căn cứ) |
| 104, 105 | Kha: Ngoài phạm vi, Từ chối; model: Hiệu lực, Trả lời | Khoản 1 Điều 220 BLLĐ (hiệu lực 01/01/2021, BLLĐ 2012 hết hiệu lực) có trong 94 Điều và đứng đầu kết quả tìm tự điền của câu 104 | Sửa thành Hiệu lực, Trả lời, đơn vị khoản 1 Điều 220 |
| 130 | Kha: Ngoài phạm vi, Từ chối; model: Hiệu lực, Trả lời | Khoản 5 Điều 5 NĐ 293/2025 quy định đúng trường hợp đổi địa bàn này | Sửa thành Hiệu lực, Trả lời, đơn vị khoản 5 Điều 5 |
| 5 | Kha chọn điểm **d** khoản 1 Điều 21, model chọn điểm **đ** | Khoản 2 Điều 24 ghi "các điểm a, b, c, đ, g và h", nên điểm d là nhầm với đ | Đổi điểm d thành điểm đ |
| 100 | Kha: Tra cứu, chỉ khoản 2 Điều 113; model: Tổng hợp, thêm khoản 3 | Câu hỏi cả "có phải trả tiền phép không" (khoản 3) lẫn "bao nhiêu ngày" (khoản 2) | Thêm khoản 3 Điều 113, đổi thành Tổng hợp |

Không có câu nào trong 11 câu trên mà model rõ ràng sai.
Năm câu không dính lỗi form (5, 100, 104, 105, 130) là lỗi gán của người, Kha cần tự xem và quyết định; Lexora không sửa nhãn thay người gán.

## Ghi chú của Kha

35 câu có ghi chú; ngoài 6 câu báo lỗi, các ghi chú ngắn gồm "S" (gợi ý sai: kết quả tìm ban đầu theo câu hỏi không chứa đơn vị đúng), "Xót" (kết quả tìm thiếu đơn vị cần) và "Bất tiện".
"Gợi ý" ở đây là danh sách kết quả tìm tự điền theo câu hỏi, không phải đề xuất của model (Kha không xem đề xuất).

## Kết luận

Nhãn của Kha đủ tốt để dùng sau khi sửa 11 câu trên.
Đây chưa phải số liệu đồng thuận để báo cáo theo đề cương: cần người gán thứ hai (ví dụ tài khoản `phapche`) tự gán ở chế độ không xem đề xuất, rồi đối soát và khóa bộ trên trang so sánh của app.
