# Chương 2. Cơ sở lý thuyết và nghiên cứu liên quan

> Bản nháp ngày 09/11/2026.
> Chỉ trích dẫn các công trình nhóm chắc chắn tồn tại; chỗ đánh dấu **[cần bổ sung trích dẫn]** cần tìm và kiểm tra nguồn trước khi nộp.

Chương này trình bày các nền tảng lý thuyết mà hệ thống dựa vào: kiến trúc RAG, truy xuất từ khóa và truy xuất ngữ nghĩa, kết hợp xếp hạng, trích xuất thông tin bằng mô hình ngôn ngữ lớn, cấu trúc của quy phạm pháp luật, kho tri thức và đồ thị tri thức, cùng các chỉ số đánh giá.
Phần cuối điểm qua các nghiên cứu liên quan và vị trí của đề tài.

## 2.1. Mô hình ngôn ngữ lớn và hiện tượng ảo giác

Mô hình ngôn ngữ lớn (LLM) sinh văn bản bằng cách dự đoán token tiếp theo dựa trên tri thức học được từ dữ liệu huấn luyện.
Khi được hỏi về một lĩnh vực chuyên môn, mô hình có thể sinh câu trả lời trôi chảy nhưng sai sự thật hoặc không có căn cứ; hiện tượng này thường được gọi là **ảo giác** (hallucination) (Ji et al., 2023).
Trong lĩnh vực pháp luật, ảo giác đặc biệt nguy hiểm vì người dùng khó phân biệt một điều khoản có thật với một điều khoản được bịa ra; ngay cả các công cụ nghiên cứu pháp lý thương mại có dùng truy xuất vẫn được ghi nhận là có tỉ lệ ảo giác đáng kể (Magesh et al., 2024).
Ngoài ra, tri thức của mô hình bị đóng băng tại thời điểm huấn luyện, trong khi văn bản pháp luật được sửa đổi, bổ sung và thay thế liên tục.

## 2.2. Retrieval-Augmented Generation

**Retrieval-Augmented Generation (RAG)** kết hợp một bộ truy xuất với một mô hình sinh: với mỗi câu hỏi, bộ truy xuất tìm các đoạn văn bản liên quan trong một kho bên ngoài, rồi mô hình sinh câu trả lời dựa trên các đoạn đó (Lewis et al., 2020).
RAG có ba lợi ích chính cho bài toán pháp luật:

- Câu trả lời dựa trên văn bản cụ thể thay vì chỉ dựa trên tri thức trong tham số của mô hình.
- Kho văn bản cập nhật được mà không cần huấn luyện lại mô hình.
- Câu trả lời có thể kèm trích dẫn tới đoạn nguồn để người dùng kiểm tra.

Một hệ thống RAG điển hình gồm các bước: chia tài liệu thành các đoạn (chunking), lập chỉ mục, truy xuất các đoạn liên quan nhất, xếp các đoạn vào ngữ cảnh trong giới hạn token, và sinh câu trả lời (Gao et al., 2023).
Chất lượng của toàn hệ thống phụ thuộc vào từng bước; đặc biệt, **cách chia và biểu diễn tài liệu** quyết định những gì bộ truy xuất có thể tìm thấy và những gì mô hình được đọc.
Với văn bản luật, chia theo độ dài cố định có thể cắt ngang một Điều hoặc tách một khoản khỏi câu dẫn chứa điều kiện áp dụng; đây là động cơ cho các điều kiện ĐK2-ĐK4 của đề tài.

RAG không tự bảo đảm câu trả lời đúng: mô hình vẫn có thể diễn giải sai đoạn nguồn, bỏ sót điều kiện, hoặc trích dẫn một đoạn không chứa căn cứ cho phát biểu.
Vì vậy hệ thống của đề tài thêm một **cổng trích dẫn** kiểm tra mọi trích dẫn thuộc tập đoạn đã cung cấp, và đánh giá riêng mức độ bám nguồn của từng phát biểu.

## 2.3. Truy xuất từ khóa: BM25

BM25 là hàm xếp hạng theo mô hình xác suất về mức độ liên quan, được dùng rộng rãi làm mốc so sánh cho truy xuất văn bản (Robertson và Zaragoza, 2009).
Với câu hỏi $q$ gồm các từ $t$ và tài liệu $d$, điểm BM25 là:

$$
\text{score}(q, d) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, d) \cdot (k_1 + 1)}{f(t, d) + k_1 \cdot \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}
$$

$$
\text{IDF}(t) = \ln\left(1 + \frac{N - n(t) + 0{,}5}{n(t) + 0{,}5}\right)
$$

trong đó:

- $f(t, d)$ là số lần từ $t$ xuất hiện trong tài liệu $d$;
- $|d|$ là độ dài tài liệu, $\text{avgdl}$ là độ dài trung bình của các tài liệu trong kho;
- $N$ là số tài liệu, $n(t)$ là số tài liệu chứa $t$;
- $k_1$ điều chỉnh mức bão hòa theo tần suất từ, $b$ điều chỉnh mức chuẩn hóa theo độ dài tài liệu.

Đề tài dùng $k_1 = 1{,}2$ và $b = 0{,}75$, là các giá trị thường dùng.
Hệ số $b$ có hệ quả quan trọng khi so sánh các cách biểu diễn: tài liệu ngắn được ưu tiên hơn tài liệu dài khi cùng chứa một từ, nên kích thước bản ghi ảnh hưởng tới kết quả xếp hạng.

Tiếng Việt viết theo âm tiết, mỗi âm tiết cách nhau một khoảng trắng, và một từ có thể gồm nhiều âm tiết ("hợp đồng", "người lao động").
Đề tài tách token theo âm tiết (`lexora-syllable-v1`) thay vì dùng bộ tách từ, để giữ luồng xử lý đơn giản và tái lập được; hạn chế của cách này là mất thông tin về ranh giới từ ghép.
BM25 khớp theo mặt chữ, nên không tìm được đoạn diễn đạt khác câu hỏi: câu hỏi "tối đa bao lâu" không khớp với câu luật viết "không quá 60 ngày".

## 2.4. Truy xuất ngữ nghĩa và BGE-M3

**Truy xuất dày đặc** (dense retrieval) biểu diễn câu hỏi và tài liệu thành các vectơ trong cùng một không gian, rồi xếp hạng tài liệu theo độ tương đồng (thường là cosine) giữa các vectơ (Karpukhin et al., 2020).
Vì vectơ được học để phản ánh nghĩa, truy xuất dày đặc có thể tìm được đoạn diễn đạt khác câu hỏi, bù cho điểm yếu của BM25.
Ngược lại, nó có thể bỏ qua các chi tiết mặt chữ quan trọng trong luật như số hiệu, con số hay một từ phủ định.

**BGE-M3** là mô hình embedding đa ngôn ngữ hỗ trợ tiếng Việt, xử lý được đầu vào dài tới 8.192 token và hỗ trợ cả biểu diễn dày đặc, thưa và đa vectơ (Chen et al., 2024).
Đề tài dùng biểu diễn dày đặc của BGE-M3, chạy cục bộ trên CPU với phiên bản trọng số cố định, để không gửi dữ liệu ra ngoài và để kết quả tái lập được.

## 2.5. Kết hợp xếp hạng: Reciprocal Rank Fusion

Khi có nhiều bộ truy xuất, có thể kết hợp các danh sách xếp hạng bằng **Reciprocal Rank Fusion (RRF)** (Cormack et al., 2009):

$$
\text{RRF}(d) = \sum_{r \in R} \frac{1}{c + \text{rank}_r(d)}
$$

trong đó $R$ là tập các danh sách xếp hạng, $\text{rank}_r(d)$ là thứ hạng của tài liệu $d$ trong danh sách $r$, và $c$ là hằng số làm giảm ảnh hưởng của các thứ hạng đầu (thường $c = 60$).
RRF chỉ dùng thứ hạng, không dùng điểm số, nên không cần chuẩn hóa điểm giữa BM25 và độ tương đồng cosine, và không có trọng số cần tinh chỉnh.
Đề tài dùng RRF với $c = 60$ trên 30 ứng viên đầu của mỗi kênh, gọi là truy xuất **kết hợp** (hybrid).

## 2.6. Trích xuất thông tin bằng mô hình ngôn ngữ lớn

**Trích xuất thông tin** (Information Extraction) là bài toán biến văn bản tự do thành dữ liệu có cấu trúc: thực thể, quan hệ giữa các thực thể và thuộc tính của chúng.
Các phương pháp truyền thống dựa trên quy tắc hoặc mô hình học có giám sát cần nhiều dữ liệu gán nhãn cho từng miền **[cần bổ sung trích dẫn]**.
LLM cho phép trích xuất theo chỉ dẫn mà không cần huấn luyện riêng, bằng cách mô tả lược đồ đầu ra trong prompt **[cần bổ sung trích dẫn]**.

**Đầu ra có cấu trúc** (structured output) buộc mô hình trả về dữ liệu theo một lược đồ JSON định trước, giúp kiểm tra tự động được kiểu và trường dữ liệu.
Tuy nhiên, lược đồ chỉ bảo đảm hình thức, không bảo đảm nội dung: mô hình vẫn có thể điền giá trị không có trong văn bản, diễn đạt lại thay vì chép nguyên văn, hoặc gán sai loại quan hệ.
Để kiểm soát điều này, đề tài yêu cầu mọi giá trị là một đoạn **chép nguyên văn, liền mạch** từ chính câu luật, và chỉ giữ giá trị định vị được chính xác trong câu.
Ràng buộc này biến một phần bài toán kiểm chứng ngữ nghĩa thành bài toán kiểm tra chuỗi ký tự mà máy làm được một cách chắc chắn.

Phương pháp **dựa trên quy tắc** vẫn có giá trị làm baseline: với văn bản luật, nhiều quy phạm có mẫu câu cố định quanh các từ tình thái như "phải", "không được", "có quyền", nên một bộ quy tắc đơn giản đã trích được một phần đáng kể với độ chính xác cao.

## 2.7. Cấu trúc của quy phạm pháp luật

Theo lý luận nhà nước và pháp luật, quy phạm pháp luật là quy tắc xử sự chung do nhà nước ban hành, thường được phân tích thành ba bộ phận: **giả định** (hoàn cảnh, điều kiện áp dụng), **quy định** (cách xử sự: được làm, phải làm, không được làm) và **chế tài** (hậu quả bất lợi khi vi phạm) **[cần bổ sung trích dẫn: giáo trình Lý luận nhà nước và pháp luật]**.
Một quy phạm không nhất thiết có đủ ba bộ phận trong cùng một câu, và một điều khoản có thể chứa nhiều quy phạm.

Đề tài vận hành hóa cấu trúc này thành các ô của một bản ghi quy phạm:

| Thành phần lý luận | Ô trong lược đồ của đề tài |
|---|---|
| Chủ thể của quy phạm | Chủ thể (bên mang quyền hoặc nghĩa vụ) |
| Quy định: cách xử sự | Hành vi, Đối tượng; Tính quy phạm (Nghĩa vụ, Điều cấm, Quyền, Được phép) |
| Giả định | Điều kiện, Ngoại lệ, Thời hạn |
| Chế tài, hệ quả | Kết quả |
| Nội dung định lượng | Định lượng (mức, số ngày, tỉ lệ) |
| Bên liên quan | Bên nhận, Bên thụ hưởng |

**Tính quy phạm** (normative modality) được nhận diện qua **từ tình thái** trong câu: "phải", "có nghĩa vụ" (nghĩa vụ); "không được", "nghiêm cấm" (điều cấm); "có quyền" (quyền); "được" (được phép).
Ý tưởng phân loại quy phạm theo tình thái nghĩa vụ, cấm, cho phép có gốc từ logic nghĩa vụ (deontic logic) **[cần bổ sung trích dẫn]**.

Văn bản luật Việt Nam có một đặc điểm gây khó cho trích xuất theo câu: nhiều khoản và điểm là các mục liệt kê không có chủ thể hay từ tình thái, vì các thông tin đó nằm ở **câu dẫn** của Điều hoặc khoản cha.
Ví dụ, khoản 2 Điều 25 Bộ luật Lao động chỉ viết "Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên"; phần "thời gian thử việc" nằm ở câu dẫn của Điều.

## 2.8. Kho tri thức và đồ thị tri thức

**Kho tri thức** (Knowledge Base) lưu tri thức dưới dạng có cấu trúc để truy vấn và suy luận được; **đồ thị tri thức** (Knowledge Graph) biểu diễn tri thức thành các nút (thực thể) và cạnh có kiểu (quan hệ) (Hogan et al., 2021).
Trong miền pháp luật, đồ thị tri thức thường mô hình hóa cấu trúc văn bản (văn bản, Điều, Khoản), quan hệ dẫn chiếu, sửa đổi, thay thế giữa các văn bản, và các khái niệm pháp lý **[cần bổ sung trích dẫn]**.

Đề tài dùng một kho tri thức lấy quy phạm làm trung tâm:

- Giá trị của các ô chủ thể, đối tượng, bên nhận tương ứng với **thực thể**.
- Quy phạm là một **quan hệ có kiểu** nối chủ thể với hành vi và đối tượng; kiểu quan hệ là tính quy phạm.
- Điều kiện, ngoại lệ, thời hạn, định lượng, kết quả là **thuộc tính** của quan hệ.
- Quan hệ cấu trúc (đơn vị thuộc Điều, Điều thuộc văn bản) và dẫn chiếu giữa các Điều được lưu riêng.

Khác với nhiều đồ thị tri thức thông thường, mỗi thông tin trong kho của đề tài gắn với **bằng chứng nguyên văn** tới vị trí ký tự, và kho được tổ chức thành các **phiên bản bất biến** do người duyệt công bố.
Đề tài không dùng cơ sở dữ liệu đồ thị chuyên dụng; đồ thị được lưu trong SQLite và JSON, đủ cho quy mô thực nghiệm.

## 2.9. Kiểm chứng tri thức

Tri thức do máy trích xuất cần được kiểm chứng trước khi dùng.
Các loại kiểm tra thường gặp gồm: kiểm tra lược đồ (đúng trường, đúng kiểu), kiểm tra toàn vẹn tham chiếu (đối tượng được nhắc tới có tồn tại), kiểm tra bằng chứng (thông tin có trong nguồn), kiểm tra trùng lặp và kiểm tra nhất quán (không mâu thuẫn với tri thức khác) **[cần bổ sung trích dẫn]**.

Kiểm tra bằng chứng nguyên văn có ưu điểm là **chắc chắn và rẻ**: nếu một giá trị không xuất hiện trong câu nguồn thì chắc chắn nó không được chép nguyên văn.
Hạn chế của nó cũng rõ: một quy phạm có mọi chữ đều nguyên văn vẫn có thể sai nghĩa, ví dụ khi bỏ mất từ phủ định, bỏ điều kiện hoặc bỏ ngoại lệ.
Để đo hiệu quả của bộ kiểm chứng một cách khách quan, có thể **chèn lỗi có chủ đích** vào các bản ghi sạch rồi đo tỉ lệ lỗi bị phát hiện theo từng loại; kỹ thuật này tương tự kiểm thử đột biến (mutation testing) trong kỹ thuật phần mềm **[cần bổ sung trích dẫn]**.

## 2.10. Các chỉ số đánh giá

### 2.10.1. Đánh giá truy xuất

**Recall@K** là tỉ lệ câu hỏi (hoặc tỉ lệ đơn vị đáp án) xuất hiện trong K kết quả đầu tiên.
Đề tài tính Recall@K theo **mã đơn vị gốc**: mọi bản ghi của mọi điều kiện đều ánh xạ về các đơn vị (Điều, Khoản, Điểm) mà nó được lấy ra, nên bốn điều kiện được chấm theo cùng một chuẩn.
Recall@K có một thiên lệch cần lưu ý: bản ghi càng lớn thì càng phủ nhiều đơn vị, nên dễ "trúng" hơn mà không có nghĩa là có ích hơn cho mô hình sinh.
Vì vậy kết quả truy xuất cần được báo cáo kèm **số token ngữ cảnh** tương ứng.

### 2.10.2. Đánh giá trích xuất

Với gold set do người gán nhãn, chất lượng trích xuất được đo bằng **Precision** (tỉ lệ giá trị trích xuất đúng trên tổng số giá trị trích xuất), **Recall** (tỉ lệ giá trị gold được trích xuất) và **F1** (trung bình điều hòa của hai chỉ số):

$$
P = \frac{TP}{TP + FP}, \quad R = \frac{TP}{TP + FN}, \quad F_1 = \frac{2PR}{P + R}
$$

Với giá trị là một đoạn văn bản, có thể so khớp **chặt** (bằng nhau sau chuẩn hóa) hoặc **lỏng** (lồng nhau hoặc trùng phần lớn token), để phân biệt lỗi sai hoàn toàn với lỗi lệch ranh giới.
Đề tài đo ở hai mức: từng ô (tương ứng thực thể) và cả quy phạm (tương ứng quan hệ).

### 2.10.3. Độ đồng thuận giữa người gán nhãn

Khi hai người gán nhãn độc lập, mức đồng thuận vượt trên mức ngẫu nhiên được đo bằng hệ số **Cohen's kappa** (Cohen, 1960):

$$
\kappa = \frac{p_o - p_e}{1 - p_e}
$$

trong đó $p_o$ là tỉ lệ đồng ý quan sát được và $p_e$ là tỉ lệ đồng ý kỳ vọng do ngẫu nhiên.
Thang diễn giải thường dùng coi 0,61-0,80 là đồng thuận khá cao và trên 0,80 là gần như hoàn toàn (Landis và Koch, 1977).
Với nhãn là một tập đơn vị (ví dụ tập Điều, Khoản chứa đáp án), đề tài dùng thêm hệ số **Dice** giữa hai tập và tỉ lệ khớp hoàn toàn.
Kappa phản ánh độ nhất quán giữa hai người theo cùng hướng dẫn, không thay thế xác nhận của chuyên gia pháp lý.

### 2.10.4. Đánh giá câu trả lời

Câu trả lời của hệ thống RAG thường được đánh giá theo nhiều chiều (Es et al., 2023):

- **Độ đúng** (answer correctness): câu trả lời có đúng với quy định không.
- **Mức độ bám nguồn** (grounding, faithfulness): mỗi phát biểu có được đoạn trích dẫn hỗ trợ không.
- **Độ chính xác trích dẫn**: đoạn được trích có thực sự chứa căn cứ không, và có thuộc tập đơn vị gold không.
- **Từ chối đúng**: khi không đủ căn cứ hoặc câu hỏi ngoài phạm vi, hệ thống có từ chối không; và ngược lại, hệ thống có từ chối nhầm câu hỏi trả lời được không.

Việc chấm do người thực hiện theo rubric là chuẩn chính; LLM có thể được dùng làm giám khảo bổ sung (Zheng et al., 2023), với điều kiện đo độ đồng thuận giữa giám khảo LLM và người chấm, và giám khảo khác với mô hình sinh để tránh tự chấm cao.

### 2.10.5. Kiểm định thống kê

Khi so sánh hai điều kiện trên **cùng** một bộ câu hỏi, các phép đo là cặp, nên cần dùng kiểm định cho dữ liệu cặp:

- **Kiểm định McNemar** cho chỉ số nhị phân theo từng câu hỏi (đúng hoặc sai, trúng hoặc trượt), chỉ dựa trên các câu mà hai điều kiện cho kết quả khác nhau (McNemar, 1947).
- **Khoảng tin cậy bootstrap ghép cặp** cho chênh lệch trung bình của các chỉ số liên tục hoặc thứ bậc, bằng cách lấy mẫu lại các câu hỏi có hoàn lại (Efron và Tibshirani, 1993).

Với khoảng 150 câu hỏi chia thành tập dev và held-out, cỡ mẫu nhỏ làm khoảng tin cậy rộng; vì vậy kết quả cần được báo cáo kèm khoảng tin cậy thay vì chỉ một con số.

## 2.11. Nghiên cứu liên quan

### 2.11.1. Xử lý ngôn ngữ pháp lý

Xử lý ngôn ngữ tự nhiên cho pháp luật (Legal NLP) đã có các bộ dữ liệu chuẩn cho tiếng Anh như LexGLUE (Chalkidis et al., 2022).
Với tiếng Việt, các cuộc thi về truy xuất và hỏi đáp pháp lý như ALQAC (Automated Legal Question Answering Competition) và Zalo AI Challenge - Legal Text Retrieval đã thúc đẩy các hệ thống truy xuất điều luật cho câu hỏi tiếng Việt **[cần bổ sung trích dẫn: bài mô tả ALQAC và Zalo AI Challenge, các hệ thống đạt giải]**.
Các bộ dữ liệu này chủ yếu đánh giá bước truy xuất điều luật, chưa đánh giá cách tổ chức tri thức hay độ bám nguồn của câu trả lời sinh ra.

### 2.11.2. Trích xuất quy phạm từ văn bản luật

Đã có nhiều nghiên cứu trích xuất quy tắc, nghĩa vụ và quyền từ văn bản quy phạm, từ phương pháp dựa trên mẫu câu tới học máy và gần đây là LLM **[cần bổ sung trích dẫn]**.
Phần lớn các nghiên cứu này dùng văn bản tiếng Anh và đánh giá trích xuất như một bài toán độc lập, chưa nối kết quả trích xuất với chất lượng của một hệ thống hỏi đáp phía sau.

### 2.11.3. RAG cho pháp luật

Các hệ thống RAG cho pháp luật thường lập chỉ mục văn bản theo đoạn hoặc theo điều khoản rồi dùng LLM để trả lời **[cần bổ sung trích dẫn]**.
Đánh giá độc lập cho thấy ngay cả công cụ thương mại có truy xuất vẫn tạo câu trả lời sai hoặc trích dẫn không hỗ trợ phát biểu (Magesh et al., 2024).
Một số hướng kết hợp đồ thị tri thức với RAG (GraphRAG) để cải thiện câu hỏi cần tổng hợp nhiều nguồn **[cần bổ sung trích dẫn]**.

### 2.11.4. Vị trí của đề tài

So với các hướng trên, đề tài có ba điểm khác:

1. Tri thức được trích xuất thành quy phạm có **bằng chứng nguyên văn tới từng ô**, nên kiểm chứng được tự động một phần và truy vết được tới vị trí ký tự.
2. Ảnh hưởng của cách tổ chức tri thức được đo bằng **thiết kế đối chứng bốn bậc**, mỗi bậc thay đổi một yếu tố, trên cùng corpus, bộ câu hỏi, bộ truy xuất và mô hình sinh.
3. Đánh giá **xuyên suốt** từ trích xuất (RQ1), kiểm chứng (RQ2) tới truy xuất và câu trả lời (RQ3), trên pháp luật lao động tiếng Việt.

## Tóm tắt chương

RAG giúp mô hình ngôn ngữ trả lời dựa trên văn bản, nhưng chất lượng phụ thuộc vào cách biểu diễn tài liệu và không tự bảo đảm trích dẫn đúng.
BM25 và truy xuất ngữ nghĩa bổ trợ nhau, RRF kết hợp chúng mà không cần tinh chỉnh trọng số.
Quy phạm pháp luật có cấu trúc giả định, quy định, chế tài, được vận hành hóa thành các ô có bằng chứng nguyên văn, cho phép kiểm chứng tự động một phần.
Các chỉ số P/R/F1, Cohen's kappa, Recall@K, độ bám nguồn, độ chính xác trích dẫn và tỉ lệ từ chối đúng, cùng kiểm định cặp, là cơ sở cho thiết kế thực nghiệm ở Chương 4.

## Tài liệu tham khảo (chương 2)

- Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D. M., Aletras, N. (2022). LexGLUE: A Benchmark Dataset for Legal Language Understanding in English. *ACL 2022*.
- Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., Liu, Z. (2024). BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. *arXiv:2402.03216*.
- Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement*, 20(1), 37-46.
- Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. *SIGIR 2009*.
- Efron, B., Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Es, S., James, J., Espinosa-Anke, L., Schockaert, S. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation. *arXiv:2309.15217*.
- Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, H. (2023). Retrieval-Augmented Generation for Large Language Models: A Survey. *arXiv:2312.10997*.
- Hogan, A., Blomqvist, E., Cochez, M., et al. (2021). Knowledge Graphs. *ACM Computing Surveys*, 54(4).
- Ji, Z., Lee, N., Frieske, R., et al. (2023). Survey of Hallucination in Natural Language Generation. *ACM Computing Surveys*, 55(12).
- Karpukhin, V., Oğuz, B., Min, S., et al. (2020). Dense Passage Retrieval for Open-Domain Question Answering. *EMNLP 2020*.
- Landis, J. R., Koch, G. G. (1977). The Measurement of Observer Agreement for Categorical Data. *Biometrics*, 33(1), 159-174.
- Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 2020*.
- Magesh, V., Surani, F., Dahl, M., Suzgun, M., Manning, C. D., Ho, D. E. (2024). Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools. *arXiv:2405.20362*.
- McNemar, Q. (1947). Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages. *Psychometrika*, 12(2), 153-157.
- Robertson, S., Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333-389.
- Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023 Datasets and Benchmarks*.

Ghi chú: thông tin thư mục (tập, số, trang, danh sách tác giả đầy đủ) cần đối chiếu lại với bản gốc trước khi nộp.
