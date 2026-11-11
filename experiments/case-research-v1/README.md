# Bộ tình huống tranh chấp lao động thực tế v1

Thư mục này chứa 46 tình huống tranh chấp lao động thực tế đã được ẩn danh, dùng làm nguyên liệu xây dựng kịch bản đánh giá cho Lexora.
Mỗi tình huống có ít nhất hai vấn đề pháp lý để câu hỏi cần đến chuyên môn pháp chế hoặc nhân sự.
Ngày nghiên cứu: 2026-11-09.
Mọi tình huống ở trạng thái cần rà soát, chưa phải dữ kiện pháp lý đã được xác minh.

## Tệp

- `cases.json`: danh sách 46 tình huống (UTF-8), các trường `case_id`, `source_kind`, `source_url`, `source_ref`, `decided_year`, `facts`, `issues`, `court_outcome`, `legal_bases_cited`, `topics`, `notes`.
- `README.md`: tệp này.

## Nguồn đã dùng

Chỉ dùng ba loại nguồn công khai đã được người dùng chấp thuận, đọc từng trang một, không tải hàng loạt.

| Loại nguồn | `source_kind` | Trang | Số tình huống |
| --- | --- | --- | --- |
| Bản án, quyết định đã công bố | `ban_an` | congbobanan.toaan.gov.vn | 24 |
| Án lệ | `an_le` | anle.toaan.gov.vn | 3 |
| Báo chí đưa tin tranh chấp lao động | `bao_chi` | vietnamnet.vn (12), tuoitre.vn gồm bài của Tuổi Trẻ, Người Lao Động và Pháp Luật TP.HCM (5), thanhnien.vn (2) | 19 |
| Tổng | | | 46 |

Nhóm `ban_an` gồm 23 bản án sơ thẩm hoặc phúc thẩm và 1 quyết định giám đốc thẩm (c20).
Nhóm `an_le` gồm Án lệ 70/2023/AL, 20/2018/AL và 69/2023/AL; trên trang án lệ chỉ có hai án lệ thuộc lĩnh vực Lao động đang có hiệu lực (70/2023/AL và 20/2018/AL), còn 69/2023/AL thuộc lĩnh vực Dân sự nhưng phát sinh từ quan hệ lao động.
Năm quyết định hoặc năm đưa tin: 2017 (1), 2018 (2), 2020 (2), 2021 (2), 2022 (3), 2023 (9), 2024 (9), 2025 (4), 2026 (13), không xác định (1).

## Cách thu thập

Công cụ đọc web thông thường báo lỗi chứng chỉ TLS ("unable to verify the first certificate") với cả hai trang của Tòa án, nên các trang này được tải từng trang bằng `curl` của Windows dùng kho chứng chỉ hệ thống.
Không có trang nào yêu cầu captcha hay chặn truy cập tự động, và không có bước nào vượt qua cơ chế bảo vệ.
Toàn văn bản án được lấy từ tệp PDF gắn với trang chi tiết, trích chữ bằng `pypdf` trong `.venv`, rồi đọc phần nội dung vụ án, nhận định và quyết định.
Sáu bản án là bản scan không có lớp chữ nên bị bỏ qua (mã trang 1374697, 2010632, 1854040, 1575819, 1736583, 2050487).
Một số bản án đã mở nhưng không đưa vào vì áp dụng pháp luật quá cũ hoặc chỉ có vấn đề tố tụng (mã trang 1454903, 1077854) hoặc không phải vụ lao động (1174981).
Bài báo được đọc qua công cụ đọc web; một bài trên tuoitre.vn (đường dẫn post486182) chỉ trả về trang chuyên mục nên không được đưa vào.

## Phân bố theo chủ đề

Một tình huống có thể thuộc nhiều chủ đề.

| Chủ đề | `ban_an` | `an_le` | `bao_chi` | Tổng |
| --- | --- | --- | --- | --- |
| `don_phuong_cham_dut` | 17 | 2 | 12 | 31 |
| `bhxh` | 9 | 0 | 13 | 22 |
| `tien_luong` | 8 | 0 | 12 | 20 |
| `hop_dong_lao_dong` | 9 | 3 | 5 | 17 |
| `bao_truoc` | 6 | 1 | 4 | 11 |
| `tro_cap_thoi_viec` | 4 | 0 | 3 | 7 |
| `cho_thoi_viec_ly_do_kinh_te` | 3 | 0 | 3 | 6 |
| `bao_hiem_that_nghiep` | 3 | 0 | 3 | 6 |
| `trach_nhiem_vat_chat` | 4 | 1 | 1 | 6 |
| `ky_luat_lao_dong` | 3 | 0 | 3 | 6 |
| `thu_viec` | 3 | 1 | 1 | 5 |
| `dieu_chuyen_cong_viec` | 3 | 0 | 2 | 5 |
| `sa_thai` | 3 | 0 | 2 | 5 |
| `tai_nan_lao_dong` | 2 | 0 | 2 | 4 |
| `cong_doan` | 2 | 1 | 1 | 4 |
| `thoi_hieu` | 2 | 0 | 2 | 4 |
| `thuong` | 1 | 0 | 3 | 4 |
| `tro_cap_mat_viec` | 2 | 0 | 1 | 3 |
| `lam_them_gio` | 3 | 0 | 0 | 3 |
| `tam_dinh_chi_cong_viec` | 2 | 0 | 1 | 3 |
| `an_toan_ve_sinh_lao_dong` | 1 | 0 | 2 | 3 |
| `khong_canh_tranh` | 1 | 1 | 0 | 2 |
| `chi_phi_dao_tao` | 2 | 0 | 0 | 2 |
| `lao_dong_nu` | 1 | 0 | 1 | 2 |
| `lao_dong_nuoi_con_nho` | 1 | 0 | 1 | 2 |
| `hop_dong_xac_dinh_thoi_han_lien_tiep` | 1 | 0 | 0 | 1 |
| `cham_dut_hop_dong_nghia_vu` | 1 | 0 | 0 | 1 |
| `hop_dong_vo_hieu` | 1 | 0 | 0 | 1 |
| `lao_dong_chua_thanh_nien` | 1 | 0 | 0 | 1 |
| `cai_thau` | 0 | 0 | 1 | 1 |
| `khau_tru_luong` | 0 | 0 | 1 | 1 |
| `lao_dong_nuoc_ngoai` | 0 | 0 | 1 | 1 |
| `cham_dut_do_giai_the` | 0 | 0 | 1 | 1 |
| `thai_san` | 0 | 0 | 1 | 1 |

Các chủ đề còn mỏng: thai sản, tuổi nghỉ hưu (chưa có tình huống nào), bệnh nghề nghiệp, lương tối thiểu và khấu trừ lương.

## Quy tắc bảo vệ thông tin cá nhân

Không ghi tên người, tên doanh nghiệp, địa chỉ cụ thể, số căn cước, mã số bảo hiểm xã hội hay bất kỳ định danh nào của đương sự, kể cả khi văn bản gốc có ghi.
Mỗi tình huống được viết lại thành mô tả ẩn danh theo ngành nghề, địa bàn cấp tỉnh và đặc điểm liên quan đến vấn đề pháp lý.
Chỉ giữ lại đường dẫn nguồn, số và ngày bản án, số án lệ, tên tòa án và tiêu đề bài báo, vì đây là định danh của văn bản, không phải của con người.
Chỉ đưa vào các tình huống đã thực sự mở và đọc; không suy đoán hay bịa số bản án, đường dẫn hoặc tình tiết.

## Lưu ý khi dùng

`legal_bases_cited` chỉ chứa căn cứ mà chính nguồn nêu; khi bài báo không nêu điều luật, trường này để trống hoặc ghi rõ là không nêu điều cụ thể.
Một số vấn đề trong `issues` có nhắc điều luật để gợi ý cho người ra đề; trường `notes` ghi rõ khi đó không phải căn cứ do nguồn trích dẫn.
Có 20 tình huống mà sự việc phát sinh trước ngày 01/01/2021 nên áp dụng Bộ luật Lao động 2012 hoặc cũ hơn; trường `notes` ghi điều tương ứng trong Bộ luật Lao động 2019 khi vấn đề pháp lý không thay đổi.
Các tình huống `bao_chi` dựa trên lời thuật của báo, chưa đối chiếu bản án gốc, và một số vụ chưa có kết quả cuối cùng.
Một vài bản án tự dẫn sai điểm, khoản hoặc điều (ví dụ c07, c14); trường `notes` đã ghi lại để không dùng nhầm làm đáp án.
Một số tình huống được đặt cạnh nhau có chủ đích vì cho kết quả trái ngược: c09 và c28 (khai không trung thực khi tuyển dụng), c13 và c36 (thỏa thuận chấm dứt qua tin nhắn, email), c03, c08 và c41 (cho thôi việc vì lý do kinh tế), c06 và c27 (thỏa thuận không cạnh tranh).
