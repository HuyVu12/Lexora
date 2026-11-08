---
title: Hướng dẫn kiểm tra quy phạm bị loại
summary: Cách gán nhãn bảng 104 quy phạm do model trích xuất trên web: năm nhãn, cách quyết định, ví dụ, đối soát và cách đọc kết quả.
category: Gán nhãn
order: 30
updated: 2026-11-08
---

## Việc này để làm gì

Bộ kiểm chứng tự động loại một quy phạm khi có cụm từ không nằm nguyên văn trong chính câu luật.
Nhưng bị loại chưa chắc là sai.
Phân tích tự động cho thấy phần lớn quy phạm bị loại của gemma4 chỉ lấy chữ từ câu dẫn của khoản: đúng về luật mà vẫn bị loại.

Bảng kiểm tra trả lời hai câu hỏi cho RQ2:

1. Trong số quy phạm **bị loại**, bao nhiêu thật sự sai? Đó là độ chính xác của bộ kiểm chứng.
2. Trong số quy phạm **được giữ**, bao nhiêu vẫn sai? Đó là lỗi lọt qua ĐK4.

Khái niệm chung (quy phạm, các ô, câu dẫn, thuật ngữ) xem ở [Hướng dẫn gán nhãn](/docs/huong-dan-gan-nhan).

## Bảng gồm những gì

| | |
|---|---|
| Ở đâu | https://vlexora.duckdns.org > Nghiên cứu > Kiểm tra quy phạm |
| Số dòng | 104: 80 quy phạm bị loại và 24 quy phạm được giữ, trộn ngẫu nhiên |
| Nguồn | Quy phạm do bốn model trích xuất (gemma4, gpt-oss-120b, nemotron-3-ultra, nemotron-3-super), lấy mẫu có hạt giống cố định |
| Thời gian ước tính | Khoảng 2 giờ mỗi người |

Bảng **che** thông tin model nào tạo quy phạm và quy phạm có bị loại không.
Người gán chỉ thấy luật và quy phạm, để không bị ảnh hưởng bởi quyết định của máy.
Đừng mở trang Kết quả kiểm tra hay trang Kết quả thực nghiệm trong lúc gán.

## Màn hình gán nhãn

Bên trái là danh sách 104 dòng; dòng đã gán có nhãn nhỏ bên cạnh.
Bên phải là dòng đang chọn, gồm bốn phần:

| Phần | Nội dung |
|---|---|
| Tên Điều và câu dẫn | Tên Điều, câu dẫn của khoản và điểm cha; đọc để hiểu câu nằm trong danh sách nào |
| Nguyên văn đơn vị | Toàn bộ chữ của đơn vị chứa câu |
| Câu được trích xuất | Câu mà model đã đọc, tô màu nếu đơn vị có nhiều câu |
| Quy phạm model đưa ra | Tính quy phạm, từ tình thái và các ô model điền |

## Các bước

1. Mở **Nghiên cứu > Kiểm tra quy phạm**, bấm **Mở bảng**.
2. App tự chọn dòng đầu tiên chưa gán.
3. Đọc câu dẫn, nguyên văn và quy phạm của model; đối chiếu từng ô với luật.
4. Chọn một trong năm nhãn (bấm vào ô, hoặc phím **1** đến **5**).
5. Ghi chú nếu cần, nhất là khi chọn **Không rõ** hoặc khi phân vân.
6. Bấm **Lưu và sang dòng tiếp** (hoặc **Ctrl+Enter**). App nhảy tới dòng chưa gán kế tiếp.

Nhãn lưu ngay mỗi lần bấm Lưu; có thể dừng giữa chừng và làm tiếp hôm sau.
Muốn sửa dòng đã gán, chọn lại dòng đó ở danh sách, đổi nhãn và lưu.

## Năm nhãn

Đánh giá **quy phạm có đúng với luật không**, đọc cả câu dẫn.
Không đánh giá model có chép đúng chữ hay không, trừ khi điều đó làm đổi nghĩa.

| Phím | Nhãn | Khi nào |
|---|---|---|
| 1 | Sai | Nói điều luật không nói; mâu thuẫn với luật; sai chủ thể; sai tính quy phạm (ví dụ nghĩa vụ thành quyền); bỏ mất điều kiện, ngoại lệ hoặc phủ định làm đổi nghĩa |
| 2 | Đúng, diễn đạt lại | Đúng nghĩa nhưng cụm từ bị viết lại, rút gọn hoặc ghép từ nhiều chỗ, không còn nguyên văn |
| 3 | Đúng, mượn câu dẫn | Đúng, nhưng có chữ lấy từ câu dẫn của khoản hoặc tên Điều thay vì từ chính câu |
| 4 | Đúng, nguyên văn | Đúng và mọi chữ nằm nguyên văn trong câu |
| 5 | Không rõ | Không quyết định được; ghi lý do |

**Nhiều nhãn cùng đúng thì chọn nhãn đứng trên trong bảng.**
Ví dụ quy phạm vừa mượn câu dẫn vừa bỏ mất ngoại lệ làm đổi nghĩa thì chọn Sai.

## Cách quyết định

Hỏi lần lượt:

1. **Tính quy phạm đúng chưa?** "phải" mà model ghi Quyền, hay "có quyền" mà ghi Nghĩa vụ, là Sai.
2. **Chủ thể đúng chưa?** Ghi nhầm người sử dụng lao động thành người lao động là Sai.
3. **Có thêm điều luật không nói không?** Thêm con số, điều kiện hay chủ thể không có trong câu và câu dẫn là Sai.
4. **Có bỏ mất ý làm đổi nghĩa không?** Bỏ "không", bỏ "trừ trường hợp...", bỏ điều kiện giới hạn phạm vi là Sai. Bỏ một ý phụ không đổi nghĩa thì không tính là Sai.
5. Nếu đúng nghĩa: các chữ lấy từ đâu?
   - từ câu dẫn hoặc tên Điều: **Đúng, mượn câu dẫn**;
   - bị viết lại, rút gọn: **Đúng, diễn đạt lại**;
   - nguyên văn trong câu: **Đúng, nguyên văn**.

Ô model để trống không phải lỗi, trừ khi thiếu nó thì quy phạm thành sai nghĩa.

## Ví dụ

**Ví dụ 1. Đúng, mượn câu dẫn**
Câu dẫn: "2. Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:"
Câu: "e) Đủ tuổi nghỉ hưu theo quy định tại Điều 169 của Bộ luật này, trừ trường hợp các bên có thỏa thuận khác;"
Model ghi: Quyền, Chủ thể "Người lao động", Hành vi "đơn phương chấm dứt", Đối tượng "hợp đồng lao động", Điều kiện "Đủ tuổi nghỉ hưu...", Ngoại lệ "trường hợp các bên có thỏa thuận khác".
Nghĩa đúng; Chủ thể và Hành vi lấy từ câu dẫn. Nhãn: **Đúng, mượn câu dẫn**.

**Ví dụ 2. Sai vì sai tính quy phạm**
Câu: "Người sử dụng lao động phải thông báo kết quả thử việc cho người lao động."
Model ghi: Quyền, từ tình thái "phải".
"phải" là nghĩa vụ, không phải quyền. Nhãn: **Sai**.

**Ví dụ 3. Sai vì bỏ ngoại lệ làm đổi nghĩa**
Câu: "Trong thời gian tạm hoãn thực hiện hợp đồng lao động, người lao động không được hưởng lương..., trừ trường hợp hai bên có thỏa thuận hoặc pháp luật có quy định khác."
Model ghi đúng Điều cấm, chủ thể, hành vi, nhưng thêm Điều kiện "nếu người lao động nghỉ quá 30 ngày" (câu không nói).
Thêm điều kiện luật không nói. Nhãn: **Sai**.

**Ví dụ 4. Đúng, diễn đạt lại**
Câu: "Người lao động làm thêm giờ được trả lương... vào ngày nghỉ hằng tuần, ít nhất bằng 200%".
Model ghi Định lượng "200% lương" (câu viết "ít nhất bằng 200%").
Nghĩa gần đúng nhưng viết lại; nếu bỏ "ít nhất" làm mất ý mức sàn thì cân nhắc Sai. Ở đây chọn **Đúng, diễn đạt lại** và ghi chú "bỏ chữ ít nhất".

**Ví dụ 5. Không rõ**
Câu có dẫn chiếu tới Điều không có trong bảng và không đủ thông tin để biết quy phạm đúng hay sai.
Nhãn: **Không rõ**, ghi chú "cần đọc Điều 62".

## Đối soát

1. Khi cả hai đã gán xong, ở trang bảng bấm **Đối soát với** tên người còn lại.
2. Ghi lại **Kappa năm nhãn** và **Kappa sai / không sai** trước khi chốt; đó là độ tin cậy của bảng trong báo cáo.
3. Bấm **Chốt N dòng hai người đã khớp**.
4. Lọc **Lệch nhau**, bàn từng dòng, chọn **Nhãn cuối**, ghi chú lý do nếu cần, bấm **Chốt**.
5. Lặp tới khi bộ lọc **Chưa chốt** không còn dòng nào.

Trên server dùng chung, nhãn hai người đã ở cùng chỗ nên không phải gửi tệp.
Cần tệp để lưu trữ thì bấm **Tải nhãn của tôi (CSV)**; định dạng giống bảng Excel cũ, dùng được với lệnh `kb-audit-score`.

## Đọc kết quả (quản trị và tài khoản giám sát)

Sau khi chốt, tài khoản admin hoặc dev mở **Kết quả kiểm tra** trên trang bảng.
Trang này mở khóa bảng: hiện từng model, quyết định của bộ kiểm chứng (bị loại hay được giữ), số dòng mỗi nhãn và **tỉ lệ sai**.

- Tỉ lệ sai = số dòng Sai / số dòng đã quyết định (không tính Không rõ).
- Nhóm **bị loại**: tỉ lệ sai càng cao, bộ kiểm chứng loại càng đúng. Tỉ lệ thấp và nhiều "Đúng, mượn câu dẫn" nghĩa là bộ kiểm chứng đang loại cả quy phạm đúng.
- Nhóm **được giữ**: tỉ lệ sai là phần lỗi vẫn lọt vào ĐK4, thường là lỗi ngữ nghĩa mà trích dẫn vẫn nguyên văn.
- Có thể tính trên nhãn cuối hoặc trên nhãn của từng người để so.

Người gán nhãn (vai trò người duyệt) không mở được trang này.

## Câu hỏi thường gặp

**Thấy quy phạm thiếu nhiều ô thì có phải Sai không?**
Không, nếu phần đã điền đúng và không làm đổi nghĩa. Bảng đánh giá cái model nói ra có đúng không, không chấm độ đầy đủ.

**Model ghi đúng nhưng chọn sai từ tình thái (chữ khác trong câu) thì sao?**
Nếu tính quy phạm vẫn đúng thì không tính là Sai; ghi chú lại.

**Hai quy phạm gần giống nhau ở hai dòng khác nhau?**
Gán từng dòng độc lập; có thể đó là cùng câu luật do hai model khác nhau trích xuất.
