---
title: Hướng dẫn gán nhãn
summary: Cách gán nhãn bộ câu hỏi, gold trích xuất và bảng kiểm tra quy phạm bị loại; giải thích các khái niệm và thuật ngữ liên quan.
category: Gán nhãn
order: 10
updated: 2026-11-08
---

## Tóm tắt nhanh

Có ba việc gán nhãn, mỗi người làm độc lập trên tài khoản của mình tại https://vlexora.duckdns.org.

| Việc | Ở đâu | Khối lượng | Thời gian ước tính | Phục vụ |
|---|---|---|---|---|
| Bộ câu hỏi | Nghiên cứu > Bộ câu hỏi > "Bộ câu hỏi thực nghiệm v1" | 152 câu | 4-6 giờ | RQ3: chất lượng câu trả lời |
| Gold trích xuất | Nghiên cứu > Gold > "Gold trích xuất v1 (40 Điều)" | 290 câu luật | 5-7 giờ | RQ1: chất lượng trích xuất |
| Bảng kiểm tra quy phạm bị loại | Nghiên cứu > Kiểm tra quy phạm | 104 dòng | khoảng 2 giờ | RQ2: độ chính xác của bộ kiểm chứng |

Làm theo thứ tự trên: bộ câu hỏi trước, vì đó là đầu vào của thực nghiệm chính.
Mỗi việc xong phần gán riêng thì hai người cùng đối soát và chốt nhãn cuối.

> Nguyên tắc quan trọng nhất: hai người không trao đổi về nhãn cho tới bước đối soát.
> Nếu bàn trước, độ đồng thuận (kappa) sẽ cao giả tạo và không còn dùng được trong báo cáo.

## 1. Vì sao phải gán nhãn

Đề tài so sánh bốn cách tổ chức dữ liệu cho hệ thống hỏi đáp luật (ĐK1-ĐK4) và trả lời ba câu hỏi nghiên cứu.
Máy không tự biết câu trả lời đúng hay sai, nên cần nhãn do người gán làm thước đo.

- **RQ1**: AI trích xuất quy phạm từ văn bản luật chính xác đến đâu? Thước đo là gold trích xuất.
- **RQ2**: bộ kiểm chứng tự động loại được bao nhiêu lỗi của AI, và có loại nhầm quy phạm đúng không? Thước đo là bảng kiểm tra quy phạm bị loại.
- **RQ3**: cách tổ chức dữ liệu nào cho câu trả lời đúng hơn, trích dẫn chuẩn hơn, biết từ chối khi thiếu căn cứ? Thước đo là bộ câu hỏi có nhãn.

Hai người gán độc lập để đo độ tin cậy của chính bộ nhãn (Cohen's kappa).
Đây là đồng thuận giữa hai sinh viên theo hướng dẫn, không phải xác nhận của chuyên gia pháp lý.

## 2. Các khái niệm cần biết

### Corpus và phiên bản đã khóa

**Corpus** là tập văn bản luật mà hệ thống được phép dùng làm căn cứ.
Corpus thực nghiệm gồm 5 văn bản, 94 Điều:

| Văn bản | Các Điều trong phạm vi |
|---|---|
| Bộ luật Lao động 45/2019/QH14 | 3, 13-48, 90-91, 93-99, 101-115, 117-118, 121-131, 220 |
| Nghị định 145/2020/NĐ-CP (hướng dẫn Bộ luật Lao động) | 7-8, 54-57, 59-60, 69-72, 114 |
| Nghị định 293/2025/NĐ-CP (lương tối thiểu vùng) | 3-5 |
| Thông tư 10/2020/TT-BLĐTBXH | 3 |
| Nghị định 12/2022/NĐ-CP (xử phạt vi phạm hành chính về lao động) | 10, 17 |

Văn bản lấy từ vbpl.vn (Cơ sở dữ liệu quốc gia về văn bản pháp luật) và được **khóa phiên bản** (mã `veaeaad4a6edc`).
Khóa nghĩa là nội dung không đổi nữa, nên mọi nhãn trỏ tới đúng một bản văn bản và kết quả có thể tái lập.

Khi gán nhãn, chỉ coi là "có căn cứ" khi nguyên văn nằm trong 94 Điều này.
Không dùng hiểu biết riêng về luật, kể cả khi bạn biết chắc ở Điều khác có quy định.

### Đơn vị văn bản

Văn bản luật được tách theo cấu trúc **Chương > Mục > Điều > Khoản > Điểm**.
Mỗi phần là một **đơn vị** có mã riêng, ví dụ `45-2019-qh14/chapter-iii/section-1/article-25/clause-2` là khoản 2 Điều 25 Bộ luật Lao động.

- Đơn vị cấp Điều chỉ chứa tên Điều và câu dẫn (nếu có), nội dung nằm ở các khoản.
- Điều không chia khoản thì toàn bộ nội dung nằm ngay ở đơn vị cấp Điều.
- **Câu dẫn** là phần mở đầu của Điều hoặc khoản trước một danh sách, ví dụ "2. Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước trong trường hợp sau đây:".

### Quy phạm và các trường

**Quy phạm** là một quy tắc xử sự trong câu luật: ai phải, được hoặc không được làm gì, trong điều kiện nào.
Hệ thống lưu mỗi quy phạm thành các trường, mỗi trường là một cụm từ chép nguyên văn từ câu luật:

| Trường | Ý nghĩa | Ví dụ |
|---|---|---|
| Tính quy phạm | Loại quy tắc | Nghĩa vụ, Quyền, Điều cấm, Được phép |
| Từ tình thái | Từ thể hiện loại quy tắc | "phải", "có quyền", "không được", "được" |
| Chủ thể | Ai phải hoặc được làm | "Người sử dụng lao động" |
| Hành vi | Làm gì | "thông báo" |
| Đối tượng | Hành vi tác động lên cái gì | "kết quả thử việc" |
| Bên nhận, Bên thụ hưởng | Ai nhận hoặc được hưởng | "người lao động" |
| Điều kiện | Khi nào quy tắc áp dụng | "trong trường hợp thử việc đạt yêu cầu" |
| Ngoại lệ | Trường hợp không áp dụng | "trừ trường hợp hai bên có thỏa thuận khác" |
| Thời hạn | Mốc hoặc khoảng thời gian | "ít nhất 45 ngày" |
| Định lượng | Con số, tỉ lệ, mức tiền | "ít nhất bằng 85%" |
| Kết quả | Hệ quả pháp lý | "phải bồi thường" |

Bốn loại tính quy phạm hay gặp:

- **Nghĩa vụ**: bắt buộc phải làm ("phải", "có trách nhiệm", "có nghĩa vụ").
- **Quyền**: được làm và được pháp luật bảo vệ ("có quyền").
- **Điều cấm**: không được làm ("không được", "nghiêm cấm", "cấm").
- **Được phép**: được làm nhưng không bắt buộc ("được").

### Bằng chứng nguyên văn

Mỗi trường phải là cụm từ có thật trong câu luật, chép đúng từng chữ.
Hệ thống lưu vị trí ký tự của cụm từ đó, nên người dùng bấm vào là mở đúng chỗ trong luật.
Đây là điểm khác biệt chính của đề tài so với hỏi đáp thông thường.

### Bốn điều kiện so sánh (ĐK1-ĐK4)

| Điều kiện | Hệ thống tìm căn cứ trong | Ý nghĩa |
|---|---|---|
| ĐK1 | Văn bản cắt thành đoạn đều nhau (384 token) | Cách làm thông thường, làm mốc |
| ĐK2 | Văn bản tách theo Điều, Khoản, Điểm | Xem việc tôn trọng cấu trúc luật có giúp ích không |
| ĐK3 | Quy phạm do AI trích xuất, chưa kiểm chứng | Xem biểu diễn có cấu trúc có giúp ích không |
| ĐK4 | ĐK3 sau khi bộ kiểm chứng loại bản ghi sai | Xem kiểm chứng có giúp ích không |

Model trích xuất chính cho ĐK3/ĐK4 là gpt-oss-120b.

## 3. Việc 1: gán nhãn bộ câu hỏi

### Bộ câu hỏi là gì

152 câu hỏi như người dùng thật sẽ hỏi (nhân viên pháp chế, nhân sự, người lao động).
Toàn bộ do model soạn nháp, nên app ghi nguồn "Model soạn nháp".
Mỗi câu có sẵn một **đề xuất nhãn** của model, chỉ để tham khảo; đề xuất có thể sai.

Một số câu hỏi cùng ý nhưng diễn đạt khác thuộc cùng **nhóm diễn đạt**.
Khi chia tập, cả nhóm luôn nằm chung một phía (dev hoặc held-out) để không "lộ đề".

### Các bước

1. Đăng nhập, mở **Nghiên cứu > Bộ câu hỏi**, bấm vào "Bộ câu hỏi thực nghiệm v1".
2. Lần đầu mở, app hỏi "Trước khi gán nhãn: có xem đề xuất của model không?".
   Chọn **một lần, không đổi được** sau khi đã gán câu đầu tiên.
   - **Tự gán, không xem đề xuất**: đo đồng thuận độc lập.
   - **Xem đề xuất rồi giữ hoặc sửa**: nhanh hơn; app ghi lại từng trường bạn giữ hay sửa.

   Thống nhất trước: một người tự gán, một người xem đề xuất.
3. Bấm **Bắt đầu gán nhãn**, chọn câu đầu tiên ở danh sách bên trái.
4. Với mỗi câu, điền ba trường (xem mục tiếp theo) rồi bấm **Lưu và sang câu tiếp**.
5. Thanh tiến độ cho biết đã gán bao nhiêu câu; có thể dừng giữa chừng, nhãn đã lưu không mất.

### Ba trường cần gán

**Loại câu hỏi**

| Loại | Khi nào | Ví dụ |
|---|---|---|
| Tra cứu | Một quy định trả lời được | "Thử việc kỹ sư tối đa bao lâu?" |
| Tổng hợp | Cần ghép từ hai quy định trở lên, có thể ở hai văn bản | "Trả 4,5 triệu ở vùng II có trái lương tối thiểu không, bị phạt bao nhiêu?" |
| Hiệu lực, sửa đổi | Hỏi thời điểm áp dụng, văn bản bị thay thế, quy định chuyển tiếp | "Nghị định 293/2025 áp dụng từ ngày nào?" |
| Ngoài phạm vi | Corpus không có căn cứ | "Tỉ lệ đóng bảo hiểm xã hội là bao nhiêu?" |

**Hệ thống nên**

- **Trả lời**: nguyên văn trong corpus đủ để trả lời.
- **Từ chối**: không đủ căn cứ, kể cả câu nghe như trong phạm vi nhưng thiếu con số hoặc quy định cụ thể.

Ví dụ: "Lương tối thiểu vùng I năm 2018 là bao nhiêu?" là Từ chối, vì corpus chỉ có Nghị định 293/2025.

**Đơn vị liên quan**

- Bắt buộc khi Trả lời; để trống khi Từ chối.
- Chọn **đơn vị nhỏ nhất** chứa căn cứ: điểm hoặc khoản, không chọn cả Điều nếu Điều có chia khoản.
- Câu tổng hợp chọn đủ mọi đơn vị cần thiết.
- Tìm đơn vị bằng ô **Tìm đơn vị trong corpus** (gõ từ khóa trong điều luật), bấm **Chọn**.
- Nếu đã xem đề xuất, có thể bấm **Điền theo đề xuất** rồi sửa.

Ví dụ: "Bên em tuyển kỹ sư tốt nghiệp đại học thì thử việc tối đa bao lâu?"
Tra cứu, Trả lời, đơn vị là khoản 2 Điều 25 Bộ luật Lao động ("Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên").

### Trường hợp khó

- Câu dẫn chiếu tới Điều ngoài phạm vi (ví dụ Điều 62, 119, 138, 169): phần đó không có căn cứ.
- Một số công thức trong Nghị định 145/2020 (Điều 56, 57) là hình ảnh nên không có chữ trong corpus; câu cần công thức đó thì Từ chối.
- Câu xin tư vấn lựa chọn cá nhân ("nên ký loại hợp đồng nào thì có lợi") là Ngoài phạm vi, Từ chối.
- Câu ghép hai ý: gán theo toàn bộ câu và ghi chú.
- Câu sai hẳn hoặc vô nghĩa: vẫn gán nhãn hợp lý nhất và ghi chú để loại khi đối soát; không tự sửa câu chữ.

### Đối soát và khóa

Khi cả hai đã gán xong:

1. Mở tab **Trao đổi**, bấm **Đối soát với** tên người còn lại.
   Trên server dùng chung, nhãn của hai người đã ở cùng chỗ nên không cần gửi tệp.
2. Trang đối soát hiện kappa loại câu, kappa hành vi, Dice đơn vị và tỉ lệ khớp hoàn toàn.
3. Bấm **Chốt N câu hai người đã khớp**, rồi lọc **Lệch nhau** để bàn từng câu và **Chốt nhãn cuối**.
4. Khi mọi câu đã chốt, bấm **Khóa bộ câu hỏi** (tỉ lệ held-out 0,3).
   Sau khi khóa không sửa được nữa; app chia các nhóm diễn đạt vào dev và held-out.

Không dùng tập held-out để chọn model, prompt hay tham số; nó chỉ dùng cho kết quả cuối.

## 4. Việc 2: gán nhãn gold trích xuất

> Quy ước chi tiết, từng ô và nhiều ví dụ ở tài liệu riêng: [Hướng dẫn gán nhãn gold trích xuất](/docs/huong-dan-gan-nhan-gold). Mục này chỉ tóm tắt.

### Gold set là gì

**Gold set** là bộ nhãn chuẩn do người làm, dùng để chấm máy.
Ở đây là danh sách quy phạm đúng của 290 câu luật thuộc 40 Điều lấy mẫu ngẫu nhiên (có hạt giống cố định để tái lập).
Sau khi chốt, lệnh `gold-score` so trích xuất của bộ quy tắc, ĐK3 và ĐK4 với gold để tính P/R/F1.

### Các bước

1. Mở **Nghiên cứu > Gold**, bấm "Gold trích xuất v1 (40 Điều)".
2. Chọn một câu ở danh sách bên trái; câu dẫn của khoản (nếu có) hiện phía trên để đọc cùng.
3. Nếu câu không nêu quy tắc nào (ví dụ câu định nghĩa thuần, câu dẫn chiếu), bấm **Câu này không nêu quy phạm**.
4. Nếu có, với mỗi quy phạm:
   - chọn **Tính quy phạm**;
   - bôi đen từ tình thái trong câu (ví dụ "phải") rồi bấm **Điền** ở ô Từ tình thái; để trống nếu chính câu này không có từ tình thái;
   - bôi đen từng cụm từ trong câu rồi bấm **Điền** ở ô tương ứng (Chủ thể, Hành vi, Đối tượng, Điều kiện...).
5. Câu có hai quy tắc trở lên thì bấm **Thêm quy phạm** cho mỗi quy tắc.
6. Bấm **Lưu và sang câu tiếp**. App kiểm tra mọi ô đều là nguyên văn của chính câu đó và báo lỗi nếu không.

### Quy tắc khi gán gold

- Chỉ chép chữ có trong **chính câu đó**. Chữ nằm ở câu dẫn của khoản thì không điền vào ô, dù hiểu là đúng.
  Ví dụ điểm e) "Đủ tuổi nghỉ hưu..., trừ trường hợp các bên có thỏa thuận khác" thì Chủ thể và Hành vi để trống, Điều kiện là "Đủ tuổi nghỉ hưu theo quy định tại Điều 169 của Bộ luật này", Ngoại lệ là "trừ trường hợp các bên có thỏa thuận khác".
- Chọn cụm từ ngắn nhất vẫn đủ nghĩa; không kéo cả câu vào một ô.
- Từ tình thái quyết định tính quy phạm: "phải" là Nghĩa vụ, "có quyền" là Quyền, "không được" là Điều cấm, "được" thường là Được phép.
- Không có ô nào phù hợp thì bỏ trống, không ép vào ô gần nghĩa.

### Đối soát

Ở tab **Trao đổi**, bấm **Đối soát với** người còn lại.
Trang hiện kappa có/không có quy phạm, kappa tính quy phạm; chọn **Chốt bản của** một người, hoặc **Sửa rồi chốt**.
Khi chốt hết, bấm **Tải gold cuối (JSONL)** và gửi cho người chạy thực nghiệm.

## 5. Việc 3: bảng kiểm tra quy phạm bị loại

> Hướng dẫn đầy đủ, cách quyết định và ví dụ: [Hướng dẫn kiểm tra quy phạm bị loại](/docs/huong-dan-kiem-tra-quy-pham). Mục này chỉ tóm tắt.

### Mục đích

Bộ kiểm chứng tự động loại một quy phạm khi có cụm từ không nằm nguyên văn trong câu.
Nhưng bị loại chưa chắc là sai: AI có thể lấy chữ từ câu dẫn của khoản, đúng về luật mà vẫn bị loại.
Bảng này đo xem trong số bị loại có bao nhiêu thật sự sai, và trong số được giữ có bao nhiêu sai.

### Các bước

1. Mở **Nghiên cứu > Kiểm tra quy phạm**, bấm **Mở bảng**.
2. Mỗi dòng có tên Điều và câu dẫn, nguyên văn đơn vị, câu được trích xuất và quy phạm model đưa ra.
3. Chọn một trong năm nhãn (phím 1 đến 5), ghi chú nếu cần, bấm **Lưu và sang dòng tiếp**.
4. Gán xong thì **Đối soát với** người còn lại và chốt nhãn cuối.

Bảng đã trộn ngẫu nhiên và không cho biết quy phạm do model nào tạo hay có bị loại không.

| Nhãn | Khi nào |
|---|---|
| Sai | Nói điều luật không nói, mâu thuẫn với luật, sai chủ thể, sai tính quy phạm, hoặc bỏ mất điều kiện, ngoại lệ làm đổi nghĩa |
| Đúng, diễn đạt lại | Đúng nghĩa nhưng bị viết lại, rút gọn hoặc ghép từ nhiều chỗ |
| Đúng, mượn câu dẫn | Đúng, nhưng có chữ lấy từ câu dẫn của khoản hoặc tên Điều |
| Đúng, nguyên văn | Đúng và nguyên văn trong câu |
| Không rõ | Không quyết định được; ghi lý do ở ghi chú |

Nhiều nhãn cùng đúng thì chọn nhãn đứng trên trong bảng.

## 6. Thuật ngữ pháp luật

| Thuật ngữ | Giải thích |
|---|---|
| Văn bản quy phạm pháp luật | Văn bản do cơ quan nhà nước ban hành, chứa quy tắc xử sự chung, bắt buộc |
| Bộ luật, Luật | Văn bản do Quốc hội ban hành, hiệu lực cao nhất sau Hiến pháp. Bộ luật Lao động 2019 là văn bản gốc của đề tài |
| Nghị định | Văn bản của Chính phủ, thường quy định chi tiết hoặc hướng dẫn thi hành luật |
| Thông tư | Văn bản của Bộ trưởng, hướng dẫn chi tiết hơn nữa (ví dụ Thông tư của Bộ Lao động - Thương binh và Xã hội) |
| Điều, Khoản, Điểm | Các cấp chia nhỏ của văn bản: Điều đánh số 1, 2, 3...; Khoản đánh số trong Điều; Điểm đánh chữ a, b, c trong Khoản |
| Hiệu lực | Thời điểm văn bản bắt đầu và hết được áp dụng |
| Sửa đổi, bổ sung | Văn bản sau thay một phần nội dung văn bản trước |
| Thay thế | Văn bản mới thay toàn bộ văn bản cũ, văn bản cũ hết hiệu lực |
| Bãi bỏ | Chấm dứt hiệu lực của văn bản hoặc một phần văn bản |
| Quy định chuyển tiếp | Cách áp dụng cho các trường hợp phát sinh trước khi văn bản mới có hiệu lực |
| Dẫn chiếu | Một quy định nhắc tới quy định khác, ví dụ "theo quy định tại Điều 62 của Bộ luật này" |
| Người lao động | Người làm việc cho người sử dụng lao động theo thỏa thuận, được trả lương và chịu sự quản lý |
| Người sử dụng lao động | Doanh nghiệp, cơ quan, tổ chức, hộ gia đình, cá nhân thuê mướn, sử dụng người lao động |
| Hợp đồng lao động | Thỏa thuận về việc làm có trả công, tiền lương, điều kiện lao động, quyền và nghĩa vụ mỗi bên |
| Hợp đồng xác định thời hạn, không xác định thời hạn | Có thời hạn tối đa 36 tháng, hoặc không định trước thời điểm kết thúc |
| Thử việc | Giai đoạn làm thử trước khi giao kết chính thức; có thời gian tối đa và mức lương tối thiểu theo luật |
| Tạm hoãn hợp đồng | Tạm ngừng thực hiện hợp đồng trong các trường hợp luật định (ví dụ đi nghĩa vụ quân sự) |
| Đơn phương chấm dứt hợp đồng | Một bên tự chấm dứt hợp đồng, có hoặc không phải báo trước tùy trường hợp |
| Trợ cấp thôi việc, trợ cấp mất việc làm | Khoản tiền người sử dụng lao động trả khi chấm dứt hợp đồng, khác với trợ cấp thất nghiệp (Luật Việc làm, ngoài corpus) |
| Lương tối thiểu vùng | Mức lương thấp nhất trả cho người lao động làm công việc giản đơn, chia theo 4 vùng |
| Làm thêm giờ | Làm ngoài thời giờ làm việc bình thường; có giới hạn số giờ và mức trả cao hơn |
| Thời giờ nghỉ ngơi | Nghỉ trong giờ làm, nghỉ hằng tuần, nghỉ hằng năm, nghỉ lễ tết, nghỉ việc riêng |
| Nội quy lao động | Quy định của doanh nghiệp về kỷ luật lao động, phải phù hợp pháp luật |
| Kỷ luật lao động | Việc tuân theo thời gian, công nghệ, điều hành; hình thức xử lý gồm khiển trách, kéo dài thời hạn nâng lương, cách chức, sa thải |
| Trách nhiệm vật chất | Nghĩa vụ bồi thường khi làm hư hỏng, mất tài sản của người sử dụng lao động |
| Xử phạt vi phạm hành chính | Phạt tiền và biện pháp khác khi vi phạm quy định nhưng chưa đến mức hình sự (Nghị định 12/2022) |

## 7. Thuật ngữ kỹ thuật và nghiên cứu

| Thuật ngữ | Giải thích |
|---|---|
| RAG (Retrieval-Augmented Generation) | Hệ thống tìm đoạn văn liên quan trước, rồi cho model trả lời chỉ dựa trên đoạn đó |
| Truy xuất | Bước tìm các đoạn luật liên quan nhất với câu hỏi |
| BM25 | Cách tìm theo từ khóa trùng nhau giữa câu hỏi và văn bản |
| Embedding, tìm theo ngữ nghĩa | Đổi văn bản thành vector để tìm theo nghĩa thay vì theo từ; đề tài dùng BGE-M3 chạy cục bộ |
| Hybrid | Kết hợp kết quả BM25 và tìm theo ngữ nghĩa |
| LLM, model | Mô hình ngôn ngữ lớn, ví dụ gpt-oss-120b, Gemma 4, Claude Opus |
| Trích xuất | Dùng quy tắc hoặc model để biến câu luật thành quy phạm có các trường |
| Bộ kiểm chứng (validator) | Chương trình kiểm tra quy phạm: đúng cấu trúc, đúng đơn vị, chữ nguyên văn, từ tình thái hợp lệ, không trùng lặp |
| Chèn lỗi có chủ đích | Cố ý làm hỏng quy phạm đúng để xem bộ kiểm chứng bắt được bao nhiêu |
| Recall@K | Tỉ lệ câu hỏi mà đơn vị đúng nằm trong K kết quả tìm được đầu tiên |
| Precision, Recall, F1 | Precision: trong số máy đưa ra, bao nhiêu đúng. Recall: trong số đúng, máy tìm được bao nhiêu. F1: trung bình điều hòa của hai số |
| Khớp chặt, khớp lỏng | Chặt: cụm từ giống hệt gold. Lỏng: cụm từ chứa nhau hoặc trùng ít nhất một nửa số từ |
| Cohen's kappa | Độ đồng thuận giữa hai người đã trừ phần trùng do may rủi; 1 là hoàn toàn khớp, 0 là như đoán ngẫu nhiên, từ 0,6 trở lên thường coi là khá |
| Dice | Độ trùng giữa hai tập đơn vị: 2 × số chung / tổng số của hai tập |
| Dev, held-out | Dev dùng để thử và chỉnh hệ thống; held-out giữ kín, chỉ dùng cho kết quả cuối |
| Nhóm diễn đạt | Các câu cùng ý khác cách hỏi; luôn nằm chung dev hoặc held-out |
| Đề xuất của model | Nhãn model gợi ý; chỉ để tham khảo, nhãn cuối do người quyết |
| Đối soát | Hai người so nhãn, bàn chỗ lệch và chốt nhãn cuối |
| Cổng trích dẫn | Bước bỏ phát biểu không có trích dẫn hợp lệ; không còn gì thì hệ thống từ chối |

## 8. Câu hỏi thường gặp

**Có cần gọi model khi gán nhãn không?**
Không. Đề xuất đã lưu sẵn; gán nhãn không tốn lượt gọi nào.

**Lỡ chọn sai chế độ xem đề xuất thì sao?**
Nếu chưa gán câu nào thì đổi được; đã gán rồi thì không. Báo người chạy thực nghiệm để ghi lại.

**Không chắc nhãn thì làm gì?**
Chọn nhãn hợp lý nhất và ghi chú; khi đối soát sẽ bàn lại.

**Gán xong một phần, mai làm tiếp được không?**
Được. Nhãn lưu ngay mỗi khi bấm Lưu.

**Gặp lỗi trên trang web?**
Chụp màn hình kèm thời điểm và gửi người phụ trách; nhãn đã lưu được sao lưu mỗi đêm.
