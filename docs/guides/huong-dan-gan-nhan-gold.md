---
title: Hướng dẫn gán nhãn gold trích xuất
summary: Quy ước chi tiết để gán quy phạm cho 290 câu luật của gold v1: từng ô, tính quy phạm, các trường hợp khó và ví dụ từ chính corpus.
category: Gán nhãn
order: 20
updated: 2026-11-16
---

## Gold dùng để làm gì

Gold trích xuất là đáp án chuẩn do người gán, dùng để chấm phần trích xuất quy phạm (RQ1).
Sau khi gán và chốt, lệnh `gold-score` so ba nguồn với gold trên đúng 290 câu này:

- bộ quy tắc (`norm-rules-v2`);
- ĐK3: quy phạm do model gpt-oss-120b trích xuất, chưa kiểm chứng;
- ĐK4: ĐK3 sau khi bộ kiểm chứng loại bản ghi sai.

Vì gold là thước đo, mọi quy ước dưới đây cần được hai người làm giống nhau.
Gặp câu không có quy ước, chọn cách hợp lý nhất, ghi chú lại và đem ra bàn ở bước đối soát.
Khái niệm chung (corpus, đơn vị, quy phạm, thuật ngữ) xem ở [Hướng dẫn gán nhãn](/docs/huong-dan-gan-nhan).

## Bộ gold v1

| | |
|---|---|
| Tên trong app | Gold trích xuất v1 (40 Điều) |
| Phạm vi | 40 Điều lấy ngẫu nhiên có hạt giống cố định từ 94 Điều của corpus, chia theo tỉ lệ số Điều của từng văn bản |
| Số câu cần gán | 290 |
| Ai gán gì | Kha gán đủ 40 Điều; Vũ gán độc lập mẫu đồng thuận 12 Điều (101 câu) |
| Thời gian ước tính | Khoảng 1-2 phút một câu: 5-7 giờ cho cả bộ, 2-3 giờ cho mẫu |
| Ở đâu | https://vlexora.duckdns.org > Nghiên cứu > Gold |

Mỗi dòng cần gán là **một câu** của một đơn vị lá (điểm, khoản không chia điểm, hoặc Điều không chia khoản).
Câu dẫn của khoản hay Điều chứa danh sách hiện phía trên câu để đọc cùng, nhưng không phải là dòng cần gán.

## Màn hình gán nhãn

1. Mở bộ gold, thẻ **Gán nhãn**.
2. Bên trái là danh sách câu với trạng thái: Chưa gán, Không có quy phạm, hoặc số quy phạm đã gán.
3. Bên phải là câu đang chọn, câu dẫn (nếu có) và vùng nhập quy phạm.
4. Thanh trên cho biết bạn đã gán bao nhiêu câu.

Cách điền một ô: bôi đen cụm từ ngay trong câu, rồi bấm **Điền** cạnh ô cần điền.
Không gõ tay: app chỉ nhận chữ chép nguyên văn từ chính câu đó và báo lỗi khi lưu nếu không khớp.

## Quy trình cho mỗi câu

1. **Đọc câu cùng câu dẫn**, xác định câu có nêu quy tắc xử sự nào không.
2. **Không có quy tắc** (định nghĩa, tên Điều, câu giải thích, câu chỉ dẫn chiếu): bấm **Câu này không nêu quy phạm**, xong.
3. **Có quy tắc**: với mỗi quy tắc,
   - chọn **Tính quy phạm**;
   - nếu chính câu có từ tình thái, bôi đen rồi **Điền** vào ô Từ tình thái; nếu không có, để trống;
   - điền các ô có chữ tương ứng trong câu, bỏ trống ô không có.
4. Câu có hơn một quy tắc thì bấm **Thêm quy phạm** cho từng quy tắc (tối đa 8).
5. Bấm **Lưu và sang câu tiếp**.

## Tính quy phạm

App cho chọn năm loại.
Quy ước chính: **tính quy phạm đi theo từ tình thái**, giống bộ từ điển mà bộ kiểm chứng dùng.

| Loại | Từ tình thái thường gặp | Ghi chú |
|---|---|---|
| Nghĩa vụ | "phải", "có trách nhiệm", "có nghĩa vụ", "bắt buộc", "buộc", "chịu trách nhiệm" | Bắt buộc làm |
| Điều cấm | "không được", "nghiêm cấm", "cấm", "bị cấm" | Bắt buộc không làm; cả "không được hưởng" cũng xếp vào đây |
| Quyền | "có quyền", "được quyền", "được" | Được làm hoặc được nhận và được pháp luật bảo vệ |
| Được phép | "được", "có thể" | Được làm nhưng không bắt buộc, thường là một lựa chọn |
| Chưa rõ loại | (không có) | Câu có quy tắc nhưng cả câu và câu dẫn đều không cho biết loại |

Ô Từ tình thái chỉ chứa đúng từ tình thái: với "được hưởng", "được trả" thì điền "được", phần còn lại thuộc Hành vi.

Phân biệt "được":

- Nhận một lợi ích (tiền, chế độ, ngày nghỉ): **Quyền**. Ví dụ "Người lao động làm thêm giờ được trả lương...".
- Được làm một việc, có thể làm hoặc không: **Được phép**. Ví dụ "Người sử dụng lao động được sử dụng người lao động làm thêm giờ khi...".

Điểm hoặc khoản trong danh sách không có từ tình thái thì **lấy tính quy phạm theo câu dẫn**, còn ô Từ tình thái để trống.
Ví dụ câu dẫn "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:" thì các điểm bên dưới là Quyền.

## Các ô và quy ước điền

Mỗi ô chứa **một đoạn liền mạch** chép từ câu.
Nếu một ô có hai đoạn tách rời, chọn đoạn chính và ghi chú.

| Ô | Điền gì | Quy ước |
|---|---|---|
| Chủ thể | Ai phải, được hoặc không được làm | Chỉ cụm danh từ ("người sử dụng lao động"), không kèm từ tình thái |
| Hành vi | Làm gì | Động từ chính, kèm cách thức đứng liền ngay sau ("thông báo bằng văn bản"); không kèm "phải", "không được"; không kèm đối tượng |
| Đối tượng | Cái mà hành vi tác động lên | Cụm danh từ sau động từ ("hợp đồng lao động", "kết quả thử việc") |
| Bên nhận | Ai nhận việc, nhận thông báo, nhận tiền | Thường sau "cho", "với" ("cho người lao động" thì điền "người lao động") |
| Bên thụ hưởng | Ai được hưởng lợi khi khác Bên nhận | Ít gặp; không chắc thì dùng Bên nhận |
| Điều kiện | Khi nào, trong trường hợp nào thì áp dụng | Giữ từ dẫn: "khi", "nếu", "trong trường hợp", "đối với"; cụm cách thức tách xa động từ ("không cần báo trước") cũng ghi ở đây |
| Ngoại lệ | Trường hợp không áp dụng | Giữ từ dẫn "trừ", "trừ trường hợp" |
| Thời hạn | Mốc hoặc khoảng thời gian để làm | "ít nhất 45 ngày", "trong thời hạn 14 ngày làm việc", "không quá 60 ngày" (thời gian thử việc) |
| Định lượng | Số lượng, mức, tỉ lệ, tiền, số giờ | "ít nhất bằng 85%", "không quá 40 giờ trong 01 tháng", "từ 5.000.000 đồng đến 10.000.000 đồng" |
| Kết quả | Hệ quả pháp lý khi quy tắc áp dụng | "phạt tiền ...", "phải bồi thường ...", "hết hiệu lực" |

Thêm vài quy ước:

- Chọn cụm **ngắn nhất vẫn đủ nghĩa**; không kéo cả câu vào một ô.
- Không đưa dấu câu đầu cuối, số thứ tự ("2.", "a)") vào ô.
- Câu có từ phủ định đổi nghĩa ("không phải", "không cần") thì giữ phủ định trong ô chứa nó, đừng làm mất.
- Một quy tắc áp cho nhiều chủ thể nối bằng "và" ("người lao động và người sử dụng lao động") thì điền cả cụm vào Chủ thể, một quy phạm.
- Một chủ thể có hai hành vi khác nhau thì tách thành hai quy phạm.

## Câu không nêu quy phạm

Bấm **Câu này không nêu quy phạm** khi câu chỉ:

- là tên Điều ("Điều 25. Thời gian thử việc");
- định nghĩa khái niệm ("Người lao động là người làm việc cho người sử dụng lao động theo thỏa thuận, được trả lương..."): chữ "được" ở đây là một phần định nghĩa, không phải quyền;
- mô tả, giải thích, không có ai phải hay được làm gì;
- chỉ dẫn chiếu ("thực hiện theo quy định tại Điều 62 của Bộ luật này") mà không tự nêu quy tắc.

## Các trường hợp hay gặp trong corpus

**Giao quy định chi tiết** ("Chính phủ quy định chi tiết Điều này.")
Nghĩa vụ, Từ tình thái trống, Chủ thể "Chính phủ", Hành vi "quy định chi tiết", Đối tượng "Điều này".

**Điều khoản xử phạt** (Nghị định 12/2022)
Câu dẫn có danh sách điểm, ví dụ "1. Phạt tiền từ 500.000 đồng đến 1.000.000 đồng đối với người sử dụng lao động có một trong các hành vi sau đây:", chỉ hiện để đọc.
Mỗi điểm bên dưới là một hành vi bị phạt: Điều cấm, Từ tình thái trống, Hành vi là nội dung điểm.
Nếu hành vi bị phạt chính là việc không làm (ví dụ "Không trả đủ tiền lương"), giữ cả chữ "Không" trong Hành vi.
Khoản tự nêu cả mức phạt và hành vi trong một câu (ví dụ Điều 17 khoản 2: "Phạt tiền đối với người sử dụng lao động có một trong các hành vi: Trả lương không đúng hạn...") thì Chủ thể "người sử dụng lao động", Kết quả "Phạt tiền", mỗi hành vi một quy phạm; mức tiền (nếu có trong câu) vào Định lượng.

**Hiệu lực, thay thế văn bản** (Nghị định 293/2025 Điều 5 khoản 1: "Nghị định này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026.")
Đây là quy tắc về hiệu lực: Chưa rõ loại, Chủ thể "Nghị định này", Kết quả "có hiệu lực thi hành", Thời hạn "từ ngày 01 tháng 01 năm 2026".
Câu "Nghị định số 74/2024/NĐ-CP ... hết hiệu lực kể từ ngày Nghị định này có hiệu lực thi hành" làm tương tự: Chủ thể là tên Nghị định cũ, Kết quả "hết hiệu lực", Thời hạn "kể từ ngày Nghị định này có hiệu lực thi hành".

**Khoản liệt kê nhiều điều kiện** (các điểm a, b, c dưới một câu dẫn)
Mỗi điểm là một dòng riêng, thường chỉ có Điều kiện, Thời hạn hoặc Định lượng; Chủ thể và Hành vi để trống vì nằm ở câu dẫn.

## Ví dụ từ chính corpus

**Ví dụ 1. Câu đầy đủ**
Điều 107 khoản 4: "Khi tổ chức làm thêm giờ theo quy định tại khoản 3 Điều này, người sử dụng lao động phải thông báo bằng văn bản cho cơ quan chuyên môn về lao động thuộc Ủy ban nhân dân cấp tỉnh."

| Ô | Giá trị |
|---|---|
| Tính quy phạm | Nghĩa vụ |
| Từ tình thái | phải |
| Chủ thể | người sử dụng lao động |
| Hành vi | thông báo bằng văn bản |
| Bên nhận | cơ quan chuyên môn về lao động thuộc Ủy ban nhân dân cấp tỉnh |
| Điều kiện | Khi tổ chức làm thêm giờ theo quy định tại khoản 3 Điều này |

**Ví dụ 2. Điểm trong danh sách**
Câu dẫn (Điều 35 khoản 1): "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước cho người sử dụng lao động như sau:"
Câu cần gán (điểm a): "Ít nhất 45 ngày nếu làm việc theo hợp đồng lao động không xác định thời hạn;"

| Ô | Giá trị |
|---|---|
| Tính quy phạm | Nghĩa vụ (theo "phải báo trước" ở câu dẫn) |
| Từ tình thái | để trống |
| Thời hạn | Ít nhất 45 ngày |
| Điều kiện | nếu làm việc theo hợp đồng lao động không xác định thời hạn |

**Ví dụ 3. "được" là Quyền**
Câu dẫn (Điều 98 khoản 1): "Người lao động làm thêm giờ được trả lương tính theo đơn giá tiền lương hoặc tiền lương thực trả theo công việc đang làm như sau:"
Câu cần gán (điểm a): "Vào ngày thường, ít nhất bằng 150%;"
Quyền, Từ tình thái trống, Điều kiện "Vào ngày thường", Định lượng "ít nhất bằng 150%".

**Ví dụ 4. "không được" và ngoại lệ**
Điều 30 khoản 2: "Trong thời gian tạm hoãn thực hiện hợp đồng lao động, người lao động không được hưởng lương và quyền, lợi ích đã giao kết trong hợp đồng lao động, trừ trường hợp hai bên có thỏa thuận hoặc pháp luật có quy định khác."

| Ô | Giá trị |
|---|---|
| Tính quy phạm | Điều cấm |
| Từ tình thái | không được |
| Chủ thể | người lao động |
| Hành vi | hưởng |
| Đối tượng | lương và quyền, lợi ích đã giao kết trong hợp đồng lao động |
| Điều kiện | Trong thời gian tạm hoãn thực hiện hợp đồng lao động |
| Ngoại lệ | trừ trường hợp hai bên có thỏa thuận hoặc pháp luật có quy định khác |

**Ví dụ 5. Định nghĩa**
Điều 3 khoản 1: "Người lao động là người làm việc cho người sử dụng lao động theo thỏa thuận, được trả lương và chịu sự quản lý, điều hành, giám sát của người sử dụng lao động."
Câu này không nêu quy phạm.

**Ví dụ 6. Không có chữ ở chính câu**
Điểm e) dưới câu dẫn "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:": "Đủ tuổi nghỉ hưu theo quy định tại Điều 169 của Bộ luật này, trừ trường hợp các bên có thỏa thuận khác;"
Quyền (theo câu dẫn), Từ tình thái trống, Chủ thể và Hành vi trống, Điều kiện "Đủ tuổi nghỉ hưu theo quy định tại Điều 169 của Bộ luật này", Ngoại lệ "trừ trường hợp các bên có thỏa thuận khác".
Không điền "Người lao động" hay "đơn phương chấm dứt" vì các chữ đó không nằm trong câu này.

## Cách chấm điểm (để biết điều gì quan trọng)

Quy tắc chấm được cố định trước khi chạy thực nghiệm.

- **Mức từng ô**: so giá trị của cùng một ô trên cùng một câu.
  - Khớp chặt: giống hệt sau khi bỏ khác biệt chữ hoa, khoảng trắng và dấu câu ở hai đầu.
  - Khớp lỏng: một bên chứa bên kia, hoặc trùng ít nhất một nửa số từ.
- **Mức quy phạm**: một quy phạm của máy khớp với gold khi cùng tính quy phạm, Hành vi khớp và Chủ thể khớp (hoặc cùng trống).

Vì vậy ba thứ quan trọng nhất là **Tính quy phạm, Chủ thể và Hành vi**; ranh giới cụm từ lệch một chút vẫn được tính ở mức khớp lỏng.

## Mẫu đồng thuận và người gán thứ hai

Theo quyết định ngày 15/11/2026, gold v1 không được hai người gán toàn bộ.
Người gán thứ nhất (Kha) gán đủ 40 Điều.
Người gán thứ hai (Vũ) gán độc lập **mẫu đồng thuận**: khoảng 30% số Điều, chọn một lần bằng hạt giống cố định.
Đồng thuận (kappa, F1) được đo trên phần hai người cùng gán; các câu còn lại dùng nhãn của người thứ nhất và được đánh dấu là một người gán.
Gold không dùng đề xuất của model, vì gold dùng để chấm chính model trích xuất.

Cách Lexora chọn mẫu (`document-largest-remainder-v1`):

- Số Điều của mẫu bằng 30% số Điều của bộ, làm tròn (40 Điều thì 12 Điều).
- Số ghế được chia cho từng văn bản theo tỉ lệ số Điều của văn bản đó, theo phương pháp phần dư lớn nhất: mỗi văn bản nhận phần nguyên của hạn ngạch, ghế còn lại đi tới các văn bản có phần dư lớn nhất, phần dư bằng nhau thì xếp theo mã băm có hạt giống.
- Vì vậy văn bản chỉ có một Điều không được làm tròn lên một cách mặc nhiên; với gold v1 (31/6/1/1/1 Điều) mẫu là 9 Điều của Bộ luật Lao động, 2 Điều của Nghị định 145/2020 và 1 Điều của Thông tư 10/2020.
- Trong mỗi văn bản, các Điều được lấy theo thứ tự mã băm có hạt giống của mã Điều.
- Hạt giống mặc định là `lexora-gold-agreement-v1`, nên mọi máy tính ra cùng một danh sách.

Mẫu được chọn **trước khi người thứ hai gán câu đầu tiên**, để không ai chọn mẫu sau khi đã thấy nhãn.
App từ chối chọn mẫu khi bộ gold đã có nhãn của hai người, và mẫu đã chọn thì không đổi được.

### Chọn mẫu (một lần cho cả bộ)

1. Mở bộ gold, thẻ **Trao đổi**, mục **Mẫu đồng thuận**.
2. Bấm **Chọn mẫu đồng thuận**, đọc hộp xác nhận (số Điều, tỉ lệ, hạt giống), rồi bấm **Chọn mẫu**.
3. App ghi lại người chọn và thời điểm; bấm **Xem 12 Điều trong mẫu** để xem danh sách và số câu của từng Điều.

### Người gán thứ hai làm gì

1. Mở bộ gold bằng tài khoản của mình, thẻ **Gán nhãn**.
2. Ở danh sách câu, chọn **Mẫu đồng thuận**; người chưa gán câu nào ngoài mẫu sẽ thấy chế độ này được chọn sẵn.
3. Thanh tiến độ và dòng "Bạn đã gán x/101 câu trong mẫu" chỉ đếm câu trong mẫu; **Lưu và sang câu tiếp** cũng chỉ đi qua câu trong mẫu.
4. Gán từng câu theo đúng quy ước ở các mục trên, không xem nhãn của người kia và không xem kết quả của máy.
5. Ở chế độ **Tất cả**, câu thuộc mẫu có chấm xanh cạnh số thứ tự; khung câu đang gán ghi "Thuộc mẫu đồng thuận".

## Đối soát và chốt

1. Mở thẻ **Trao đổi**, bấm **Đối soát với** tên người còn lại.
2. Khung **Mức đồng thuận** cho biết mẫu có bao nhiêu Điều và câu, mỗi người đã gán bao nhiêu câu trong mẫu, cùng **Kappa có/không có quy phạm**, **Kappa tính quy phạm** và F1 trên các câu cả hai đã gán.
3. Bộ lọc **Cần đối soát** liệt kê câu hai người gán khác nhau; với từng câu chọn **Chốt bản của** một người, hoặc **Sửa rồi chốt**.
4. Câu thuộc mẫu chỉ chốt được khi đã có nhãn của cả hai người.
5. Câu bất đồng do thiếu quy ước: thống nhất quy ước mới, ghi vào ghi chú, áp dụng cho các câu tương tự.
6. Bấm **Chốt hàng loạt** và xác nhận: app chốt một lần các câu hai người gán giống nhau và các câu ngoài mẫu chỉ có nhãn của một người.
7. Khung **Chốt nhãn cuối** liệt kê điều còn chặn việc xuất gold (ví dụ câu trong mẫu chưa đủ nhãn của hai người, câu ngoài mẫu chưa ai gán); khi không còn gì chặn, bấm **Tải gold cuối (JSONL)** và gửi cho người chạy thực nghiệm.

App ghi nguồn của mỗi nhãn cuối:

| Nguồn | Nghĩa |
|---|---|
| `agreed:<a>+<b>` | Hai người gán giống nhau, chốt hàng loạt |
| `single:<a>` | Câu ngoài mẫu, chỉ có nhãn của một người, chốt hàng loạt |
| `adjudicated:<người chốt>` | Người đối soát chọn hoặc sửa nhãn; bộ cũ ghi tên người chốt không có tiền tố |

Nếu có người sửa nhãn của một câu đã chốt hàng loạt, câu đó tự bỏ chốt để chốt lại; nhãn do người đối soát chốt thì giữ nguyên.
Mỗi dòng của gold cuối có thêm trường `annotation` với `mode` là `double` (hai người gán) hoặc `single` (một người gán), danh sách người gán, nguồn của nhãn cuối và `in_sample`.
`gold-score` khi đó báo P/R/F1 trên toàn bộ gold và thêm khối `double_annotated` trên riêng các câu hai người gán, để bảng kết quả của luận văn có cả hai số.

Ghi lại kappa trước khi chốt: đó là số liệu độ tin cậy của gold trong báo cáo.

## Mẹo làm nhanh và đúng

- Làm theo từng Điều liền nhau để giữ mạch câu dẫn.
- Đọc câu dẫn trước, quyết định tính quy phạm cho cả danh sách điểm một lần.
- Mỗi buổi khoảng 1-1,5 giờ rồi nghỉ; gán lúc mệt dễ lệch quy ước.
- Không mở kết quả trích xuất của máy hay trang Kết quả trong lúc gán gold.
