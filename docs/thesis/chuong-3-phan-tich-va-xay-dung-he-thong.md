# Chương 3. Phân tích và xây dựng hệ thống

> Bản nháp ngày 09/11/2026, viết từ mã nguồn và nhật ký quyết định của dự án.
> Các chỗ đánh dấu **[cập nhật]** chờ số liệu RQ1, RQ3 hoặc quyết định của giảng viên.

Chương này trình bày cách nhóm xây dựng Lexora: thu thập và chuẩn hóa dữ liệu luật, thiết kế lược đồ tri thức, trích xuất và kiểm chứng tri thức, tổ chức kho tri thức theo bốn điều kiện đối chứng, và hệ thống truy xuất, sinh câu trả lời.
Mọi thành phần được thiết kế để kết quả tái lập được: dữ liệu khóa phiên bản, cấu hình ghi lại theo từng lượt chạy, đầu ra của model được lưu nguyên văn.

## 3.1. Thu thập và chuẩn bị dữ liệu

### 3.1.1. Nguồn dữ liệu

Văn bản được lấy từ Cơ sở dữ liệu quốc gia về văn bản pháp luật (vbpl.vn) qua cổng dữ liệu công khai mà trang web dùng.
Mỗi văn bản được lưu thành một **bản chụp** bất biến gồm nội dung gốc, siêu dữ liệu chính thức (số hiệu, cơ quan ban hành, ngày ban hành, trạng thái hiệu lực), thời điểm truy cập và mã băm SHA-256 của nội dung.
Việc lấy văn bản chỉ thực hiện theo từng văn bản được chỉ định rõ, có khoảng nghỉ giữa các lần gọi; trang tìm kiếm của vbpl.vn không bị tự động hóa.

Để tìm văn bản nhanh, nhóm dựng một danh mục ngoại tuyến (`catalog-v1`) từ hai bộ dữ liệu mở có mã văn bản trùng với mã của vbpl.vn; danh mục chỉ dùng để tìm, trạng thái hiệu lực vẫn lấy từ bản chụp.

### 3.1.2. Phạm vi thực nghiệm

| Văn bản | Các Điều trong phạm vi | Chủ đề |
|---|---|---|
| Bộ luật Lao động 45/2019/QH14 | 3, 13-48, 90-91, 93-99, 101-115, 117-118, 121-131, 220 | Định nghĩa, hợp đồng, thử việc, chấm dứt hợp đồng, tiền lương, thời giờ làm việc và nghỉ ngơi, kỷ luật, hiệu lực |
| Nghị định 145/2020/NĐ-CP | 7-8, 54-57, 59-60, 69-72, 114 | Hướng dẫn hợp đồng, tiền lương làm thêm giờ, kỷ luật, hiệu lực |
| Nghị định 293/2025/NĐ-CP | 3-5 | Lương tối thiểu vùng |
| Thông tư 10/2020/TT-BLĐTBXH | 3 | Hướng dẫn nội dung hợp đồng lao động |
| Nghị định 12/2022/NĐ-CP | 10, 17 | Xử phạt vi phạm về thử việc và tiền lương |

Tổng cộng 5 văn bản, 94 Điều, 617 đơn vị (287 khoản, 213 điểm).
Đề cương dự kiến 8-12 văn bản với 60-100 điều khoản; số Điều đạt, số văn bản được thu hẹp để vừa sức gán nhãn của hai thành viên (ghi trong nhật ký quyết định).

### 3.1.3. Chuẩn hóa văn bản

Mọi vị trí bằng chứng đều neo vào **văn bản đã chuẩn hóa**, nên quy tắc chuẩn hóa được cố định và đặt tên (`nfc-newlines-v1`): chuẩn hóa Unicode NFC và thống nhất ký tự xuống dòng.
Bất kỳ thay đổi nào ở bước này đều làm sai lệch vị trí cũ và phải tạo phiên bản mới.

### 3.1.4. Tách cấu trúc văn bản

Bộ tách cấu trúc (`lexora-parser-v2`) chia văn bản thành Chương, Mục, Điều, Khoản, Điểm; mỗi phần là một **đơn vị** có mã ổn định, ví dụ `45-2019-qh14/chapter-iii/section-1/article-25/clause-2`.
Đơn vị cấp Điều chỉ giữ tên Điều và câu dẫn; nội dung nằm ở khoản và điểm.
Phiên bản 2 xử lý thêm ba trường hợp gặp trong pilot:

- **Trích dẫn sửa đổi**: đoạn văn bản nằm trong ngoặc kép của một điều khoản sửa đổi không bị tách thành đơn vị con.
- **Biến thể tiêu đề**: tiêu đề Điều gõ sai dấu (ví dụ "Điêu") vẫn được nhận.
- **Phụ lục và phần cuối văn bản**: được tách riêng, không dính vào Điều cuối cùng.

Mỗi văn bản kèm báo cáo cảnh báo của bộ tách (ví dụ trích dẫn sửa đổi), hiển thị cho người duyệt trong ứng dụng.

Một hạn chế đã biết: một số công thức trong Nghị định 145/2020 (Điều 56, 57) là hình ảnh nên không có trong văn bản.

### 3.1.5. Khóa phiên bản corpus

Corpus thực nghiệm được khóa thành phiên bản số 1 (mã `veaeaad4a6edc`) cùng mã băm của toàn bộ gói dữ liệu.
Mọi bộ câu hỏi, gold và lượt chạy đều gắn với đúng phiên bản này, nên mã đơn vị luôn trỏ tới cùng một nội dung.

## 3.2. Lược đồ tri thức

### 3.2.1. Hợp đồng dữ liệu

Dữ liệu trao đổi giữa các bước theo hợp đồng `1.0.0-pilot` gồm bốn loại bản ghi JSONL:

| Bản ghi | Nội dung chính |
|---|---|
| Văn bản | Mã văn bản, phiên bản, nguồn, ngày truy cập, mã băm, ngày hiệu lực, trạng thái pháp lý |
| Đơn vị | Mã đơn vị, loại (Chương, Mục, Điều, Khoản, Điểm), đơn vị cha, vị trí ký tự trong văn bản, nội dung |
| Bằng chứng | Đoạn trích nguyên văn, vị trí bắt đầu và kết thúc, mã băm văn bản chuẩn hóa |
| Quy phạm | Tính quy phạm, từ tình thái, các ô, bằng chứng của từng ô, trạng thái duyệt |

Bộ kiểm tra hợp đồng xác nhận: đúng lược đồ, tham chiếu tồn tại, và đoạn trích bằng đúng nội dung tại vị trí đã ghi.

### 3.2.2. Quy phạm

Đơn vị tri thức trung tâm là **quy phạm**: một quy tắc xử sự nêu trong một câu luật.

| Thành phần | Ý nghĩa |
|---|---|
| Tính quy phạm | Nghĩa vụ, Điều cấm, Quyền, Được phép, hoặc Chưa rõ |
| Từ tình thái | Từ trong câu thể hiện loại quy phạm ("phải", "không được", "có quyền", "được") |
| Chủ thể | Bên mang nghĩa vụ hoặc quyền |
| Hành vi, Đối tượng | Việc phải, được hoặc không được làm, và cái mà hành vi tác động lên |
| Bên nhận, Bên thụ hưởng | Bên nhận việc, nhận tiền hoặc được hưởng lợi |
| Điều kiện, Ngoại lệ | Khi nào áp dụng, trường hợp không áp dụng |
| Thời hạn, Định lượng | Mốc thời gian; số lượng, mức, tỉ lệ |
| Kết quả | Hệ quả pháp lý |

Mỗi ô là một đoạn chép nguyên văn từ chính câu, kèm vị trí ký tự; nhờ vậy mỗi thông tin đều truy được về văn bản gốc và máy kiểm tra được chữ nào không có thật.
Danh sách từ tình thái hợp lệ cho từng loại được cố định trong mã nguồn và dùng chung cho bước kiểm chứng.

### 3.2.3. Ánh xạ sang thực thể và quan hệ

Đề cương đặt RQ1 theo thực thể và quan hệ (entity/relation).
Quy phạm biểu diễn đúng nội dung đó ở dạng có bằng chứng:

| Khái niệm đề cương | Trong Lexora |
|---|---|
| Thực thể | Giá trị của các ô Chủ thể, Đối tượng, Bên nhận, Bên thụ hưởng |
| Quan hệ có kiểu | Quy phạm: Chủ thể nối với Hành vi và Đối tượng bằng kiểu Nghĩa vụ, Quyền, Điều cấm hoặc Được phép |
| Thuộc tính của quan hệ | Điều kiện, Ngoại lệ, Thời hạn, Định lượng, Kết quả |
| Quan hệ cấu trúc | Đơn vị thuộc Điều, Điều thuộc văn bản; dẫn chiếu giữa các Điều (`explicit-article-ref-v1`) |
| Thông tin thời gian, trạng thái | Thuộc tính của văn bản: ngày hiệu lực, trạng thái pháp lý |

Vì vậy RQ1 được đo ở hai mức: từng ô (tương ứng thực thể) và cả quy phạm (tương ứng quan hệ).

### 3.2.4. Trạng thái duyệt

Mọi quy phạm do máy tạo đều ở trạng thái **chờ duyệt** cho tới khi người duyệt quyết định; chúng không được trình bày như sự thật pháp lý đã xác minh.

## 3.3. Lựa chọn công nghệ

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Lõi xử lý | Python, chỉ thư viện chuẩn | Dễ tái lập, ít phụ thuộc |
| Lưu trữ | SQLite và tệp JSONL | Chạy trên máy cá nhân; giai đoạn này chưa cần cơ sở dữ liệu máy chủ |
| Model trích xuất chính | gpt-oss-120b (mã nguồn mở) qua 9Router | Đề cương ưu tiên model mở; phủ đủ câu, không lỗi gọi trong lượt chạy |
| Model lặp lại, đối chứng | gemma4:31b; Claude Opus 5.5 | Kiểm tra kết quả có lặp lại trên model khác; so với model mạnh có phí |
| Truy xuất từ khóa | BM25 (k1 = 1,2; b = 0,75), tách theo âm tiết tiếng Việt | Mốc chuẩn, không cần huấn luyện |
| Truy xuất ngữ nghĩa | BGE-M3 (revision `5617a9f`) chạy cục bộ trên CPU | Mở, hỗ trợ tiếng Việt, không gửi dữ liệu ra ngoài |
| Kết hợp | Reciprocal Rank Fusion (c = 60, 30 ứng viên mỗi kênh) | Đơn giản, không cần tinh chỉnh trọng số |
| Sinh câu trả lời | **[cập nhật]** gpt-oss-120b qua 9Router hoặc Claude Opus 5.5, một model cố định cho cả bốn điều kiện | Chờ chốt |
| Ứng dụng web | FastAPI, Pydantic; SvelteKit, TypeScript | Giao diện cho người dùng thật, phục vụ dạng ứng dụng tĩnh |

Không dùng LangChain, LlamaIndex hay cơ sở dữ liệu đồ thị để giữ toàn bộ luồng xử lý minh bạch và kiểm soát được.

## 3.4. Trích xuất tri thức

### 3.4.1. Baseline theo quy tắc

Bộ quy tắc `norm-rules-v2` nhận diện từ tình thái và mẫu câu thường gặp để điền các ô; câu có từ tình thái nhưng không khớp mẫu được đánh dấu để người duyệt xem.
Đây là baseline cho RQ1.

### 3.4.2. Trích xuất bằng model

Prompt `norm-llm-v1` gửi cho model các câu của một Điều kèm câu dẫn làm ngữ cảnh, mỗi câu có mã S1, S2...
Model trả về danh sách quy phạm cho từng câu, với yêu cầu: mọi giá trị phải chép nguyên văn, liền mạch từ chính câu; không có thì để trống; văn bản trong yêu cầu là dữ liệu, không phải chỉ dẫn.

| Thiết lập | Giá trị |
|---|---|
| Đơn vị gọi | Một Điều mỗi lượt (tối đa khoảng 6.000 ký tự), 95 lượt cho toàn phạm vi, 577 câu |
| Nhiệt độ | 0 |
| Giới hạn đầu ra | 16.000 token (một số model suy luận dùng nhiều token trước khi trả lời) |
| Đầu ra | Claude Code: JSON theo lược đồ; 9Router: JSON trong câu trả lời, lưu nguyên văn để đối chiếu |
| Tối đa | 6 quy phạm mỗi câu |

Mỗi lượt chạy ghi lại model, prompt, mã băm lược đồ, câu trả lời thô, token và thời gian; lượt chạy bị ngắt được tiếp tục mà không gọi lại các lô đã xong.

### 3.4.3. So sánh và chọn model

Nhóm chạy cùng thiết lập với 7 model.

| Model | Câu có trả lời | ĐK3 | ĐK4 | Bị loại | Lượt gọi lỗi |
|---|---|---|---|---|---|
| gpt-oss-120b | 100% | 416 | 385 | 7,5% | 0% |
| gemma4:31b | 93,6% | 446 | 304 | 31,8% | 2,1% |
| nemotron-3-ultra | 86,5% | 380 | 325 | 14,5% | 33,3% |
| nemotron-3-super | 88,6% | 331 | 308 | 6,9% | 7,8% |
| beam | 62,2% | 265 | 247 | 6,8% | 39,7% |
| Claude Opus 5.5 | 100% | 450 | 450 | 0% | 0% |

gpt-oss-120b được chọn làm model chính vì phủ đủ câu, không lỗi gọi, và phần lớn quy phạm bị loại của nó là lỗi thật.
Nhóm không chọn model theo độ chênh giữa ĐK3 và ĐK4, vì như vậy là thiên lệch theo kết quả mong muốn; lựa chọn sẽ được kiểm lại bằng F1 trên gold **[cập nhật]**.

## 3.5. Kiểm chứng tri thức

### 3.5.1. Bộ kiểm chứng tự động

Bộ kiểm chứng `kb-validator-v3` kiểm từng quy phạm theo năm nhóm; mỗi kiểm tra cho kết quả đạt, không đạt, không áp dụng hoặc chưa xác minh được.

| Mã | Kiểm tra | Loại khi |
|---|---|---|
| V1 | Lược đồ | Thiếu trường, sai kiểu, tính quy phạm không hợp lệ, giá trị quá dài |
| V2 | Toàn vẹn | Đơn vị không tồn tại, sai phiên bản, câu nằm ngoài đơn vị |
| V3 | Bằng chứng nguyên văn | Có ô không tìm thấy nguyên văn trong câu |
| V4 | Từ tình thái | Từ tình thái không có trong câu, hoặc thuộc loại khác (ví dụ "phải" mà ghi Quyền) |
| V7 | Trùng lặp | Quy phạm giống hệt một quy phạm khác của cùng câu |

Quy phạm không có từ tình thái (thường là các điểm trong danh sách) được ghi là **chưa xác minh** thay vì bị loại.
Phiên bản 3 là kết quả điều chỉnh sau khi xem đầu ra của pilot, trước mọi phép đo: v1 loại 13/14 quy phạm ở lượt thử vì quá chặt, v2 vẫn loại 132/450.
Việc điều chỉnh này được ghi trong nhật ký quyết định và nêu trong phần giới hạn.

Bộ kiểm chứng chưa kiểm hiệu lực theo thời gian và mâu thuẫn giữa các văn bản; đây là giới hạn so với mô tả của đề cương.

### 3.5.2. Đo hiệu quả kiểm chứng

Hai cách đo bổ trợ nhau:

- **Chèn lỗi có chủ đích** (`error-injection-v1`): lấy quy phạm sạch của ĐK4, cố ý làm hỏng theo 12 loại lỗi (30 lỗi mỗi loại, hạt giống cố định) và đo tỉ lệ bị loại. Các loại lỗi chia thành lỗi kỹ thuật (sai đơn vị, sai phiên bản, sửa trích dẫn, đổi số, chủ thể bịa, từ tình thái bịa hoặc đảo, hành vi lấy từ câu khác) và lỗi ngữ nghĩa khi chữ vẫn nguyên văn (bỏ phủ định, bỏ điều kiện, bỏ ngoại lệ).
- **Kiểm tra tay quy phạm bị loại** (`rejection-audit-v1`): 104 quy phạm (80 bị loại, 24 được giữ) từ bốn model, che nguồn, hai người gán nhãn Sai, Đúng diễn đạt lại, Đúng mượn câu dẫn, Đúng nguyên văn hoặc Không rõ.

Kết quả sơ bộ: bộ kiểm chứng bắt 97-100% lỗi kỹ thuật và gần như không bắt lỗi ngữ nghĩa, đúng như thiết kế.
Phân tích tự động cho thấy 82% số quy phạm bị loại của gemma4 chỉ do lấy chữ từ câu dẫn của khoản; độ chính xác thật của bộ kiểm chứng chờ kết quả gán nhãn **[cập nhật]**.

## 3.6. Xây dựng kho tri thức

### 3.6.1. Kho cho thực nghiệm

ĐK3 là toàn bộ quy phạm của một lượt trích xuất; ĐK4 là phần của ĐK3 qua được bộ kiểm chứng.
Cả hai được dựng lại một cách tất định từ câu trả lời thô đã lưu, nên đổi phiên bản bộ kiểm chứng không cần gọi lại model.

### 3.6.2. Kho cho người dùng thật

Trong ứng dụng, người duyệt nhập văn bản, cho máy tách quy phạm (bằng quy tắc hoặc model), rồi duyệt từng quy phạm: chấp nhận, từ chối, hoặc sửa một ô bằng cách bôi đen đúng cụm từ trong nguyên văn.
Mỗi câu không có quy phạm phải được người duyệt ghi nhận hoặc bổ sung quy phạm trước khi công bố.
Mỗi lần công bố tạo một **phiên bản** bất biến của kho, ghi người duyệt và lý do; người tra cứu chỉ thấy các kho đã công bố, và hỏi đáp chỉ dùng bằng chứng của quy phạm đã được duyệt.

## 3.7. Truy xuất và sinh câu trả lời

### 3.7.1. Bốn cách biểu diễn

| Điều kiện | Bản ghi để tìm | Số bản ghi |
|---|---|---|
| ĐK1 | Đoạn 384 token, gối nhau 64 token, cắt từ văn bản liền | 83 |
| ĐK2 | Mỗi điểm, khoản (hoặc Điều không chia khoản) kèm tên văn bản, đường dẫn cấu trúc, tên Điều và câu dẫn; đơn vị dài được chia theo câu | 460 |
| ĐK3 | Mỗi quy phạm của lượt trích xuất, diễn đạt thành các dòng "Tính quy phạm: ...", "Chủ thể: ..." | 416 |
| ĐK4 | Như ĐK3, chỉ gồm quy phạm qua bộ kiểm chứng | 385 |

Mọi bản ghi đều ánh xạ về mã đơn vị gốc, nên Recall@K và độ chính xác trích dẫn được tính theo cùng một chuẩn cho cả bốn điều kiện.

### 3.7.2. Truy xuất

Cùng cấu hình cho cả bốn điều kiện: phương pháp (BM25, BGE-M3 hoặc kết hợp), tham số BM25, mô hình embedding, quy tắc kết hợp và số kết quả (top-5).
Phương pháp được chọn trên tập dev rồi khóa trước khi chạy tập held-out **[cập nhật]**.

### 3.7.3. Sinh câu trả lời

Các bản ghi tìm được được đánh mã E01, E02... và xếp vào ngữ cảnh trong giới hạn 3.000 token (luôn giữ bản ghi đầu tiên).
Prompt `answer-v1` yêu cầu model: chỉ dùng các đoạn căn cứ; mỗi phát biểu ghi mã đoạn hỗ trợ; giữ đủ điều kiện, ngoại lệ, phủ định; không khẳng định hiệu lực nếu đoạn không nói; trả lời bằng một trong bốn trạng thái (đủ căn cứ, một phần, không đủ căn cứ, ngoài phạm vi).

**Cổng trích dẫn** chạy sau model: bỏ mọi phát biểu không có mã đoạn hợp lệ; nếu không còn phát biểu nào, câu trả lời được hạ thành "không đủ căn cứ".
Với model qua 9Router, lược đồ JSON được đưa vào prompt, câu trả lời được đọc thành JSON và lưu nguyên văn; câu trả lời không đọc được tính là lượt lỗi.

### 3.7.4. Bảo đảm so sánh công bằng

Trước khi báo cáo RQ3, công cụ `preflight` kiểm tra: bốn điều kiện dùng cùng gói dữ liệu, cùng bộ câu hỏi, cùng cấu hình truy xuất và embedding; mỗi điều kiện một lượt; không bản ghi nào lẫn giữa các điều kiện; ĐK3 và ĐK4 lấy từ cùng một lượt trích xuất và ĐK4 là tập con; các lượt sinh câu trả lời dùng cùng model, prompt, số kết quả và giới hạn token; tập held-out chỉ chạy khi cấu hình đã khóa.

## 3.8. Ứng dụng web

### 3.8.1. Kiến trúc

Lõi xử lý viết bằng Python thư viện chuẩn; lớp web dùng FastAPI và phục vụ giao diện SvelteKit đã build sẵn; dữ liệu nằm trong một tệp SQLite cho mỗi không gian làm việc.
Bản dùng chung cho nhóm chạy tại https://vlexora.duckdns.org sau một reverse proxy HTTPS, sao lưu mỗi đêm.

### 3.8.2. Vai trò và an toàn

| Vai trò | Quyền |
|---|---|
| Người tra cứu | Hỏi đáp trên các kho đã công bố |
| Người duyệt | Nhập văn bản, duyệt và công bố kho; khu Nghiên cứu (corpus, bộ câu hỏi, gold, kiểm tra quy phạm) |
| Quản trị | Quản lý tài khoản và mọi việc của người duyệt |
| Giám sát | Xem lượt gọi model, mức sử dụng, kết quả thực nghiệm; đặt hạn mức và công tắc tính năng dùng model |

Mật khẩu băm bằng scrypt; khóa tạm sau 5 lần đăng nhập sai; phiên đăng nhập dùng cookie HttpOnly; mọi yêu cầu ghi cần token và kiểm tra nguồn gốc.
Nhật ký gọi model chỉ lưu số liệu (token, thời gian, kết quả), không lưu câu hỏi hay câu trả lời của người dùng.

### 3.8.3. Hỗ trợ nghiên cứu trong ứng dụng

Các công cụ gán nhãn (bộ câu hỏi, gold, kiểm tra quy phạm) cho phép hai người gán độc lập trên tài khoản riêng, tính Cohen's kappa và đối soát ngay trên trang; người gán không thấy thông tin có thể làm thiên lệch nhãn (model nào tạo quy phạm, quy phạm có bị loại không).
Trang Kết quả và trang Giám sát đọc trực tiếp số liệu các lượt chạy và xuất được báo cáo.

## Tóm tắt chương

Lexora tổ chức luật lao động thành kho quy phạm có cấu trúc, mỗi thông tin có bằng chứng nguyên văn tới vị trí ký tự, được kiểm chứng tự động và duyệt bởi người trước khi dùng.
Bốn điều kiện ĐK1-ĐK4 được xây dựng từ cùng một corpus khóa phiên bản, chỉ khác nhau ở cách biểu diễn, và dùng chung truy xuất, sinh câu trả lời và cách chấm.
Chương 4 trình bày cách xây dựng bộ đánh giá và kết quả thực nghiệm.
