# Phương án cải thiện ĐK2-ĐK4, 22/11/2026

Trạng thái: đã chốt hướng ngày 22/11 (mục 7, câu 1-3); chưa cài code, chưa gọi model.
Tài liệu này đánh giá những gì đã làm cho ĐK2, ĐK3, ĐK4 và đề xuất thay đổi thiết kế; nó không bám cứng đề cương, nhưng ghi rõ chỗ lệch.
Mọi số liệu là chạy thử trên tập dev với nhãn nháp do model soạn (corpus v2 cho truy xuất ĐK2, corpus v1 và v3 cho kho quy phạm); chúng chỉ dùng để chọn hướng, không dùng để kết luận.
Không có lượt gọi model hay tải mạng nào trong phiên phân tích này.
Phân tích offline nằm ở `experiments/runs/analysis-2026-11-22-dk2/` và `experiments/runs/analysis-2026-11-22-dk34/` (thư mục lượt chạy không vào Git).

Ràng buộc người dùng đặt ngày 22/11:

- Mốc dừng thêm biến thể lùi khoảng một tuần, từ 25/11 sang khoảng 02/12; lượt chính dời theo.
- Ngân sách gọi model cho phần cải thiện tới khoảng 30 USD, mỗi lượt vẫn duyệt trước.
- Việc đổi ĐK4 thành kho do người duyệt sẽ quyết sau khi xem số (mục 5.4).
- Nhãn người gần như chưa tăng so với 15-16/11.

## 1. Tóm tắt

Thang bốn bậc hiện tại chỉ có một bậc tạo khác biệt thật: ĐK2 so với ĐK1 về độ chính xác trích dẫn.
ĐK3 gần như trùng ĐK2 và ĐK4 gần như trùng ĐK3, không phải do nhiễu mà do cách thiết kế: dòng quy phạm không mang thông tin mới, model sinh không dùng nó, và bộ kiểm chứng chủ yếu loại nhầm.
Hiệu ứng lớn nhất đo được trong toàn bộ dự án (lọc hiệu lực theo đơn vị) hiện đang được cấp đều cho ĐK2, ĐK3, ĐK4, nên không bậc nào trong ba bậc này được tính công.

Phương án đề xuất theo một nguyên tắc: mỗi bậc phải thêm một thứ có cơ chế làm đổi ngữ cảnh hoặc câu trả lời, và cơ chế đó đo được bằng chỉ số tất định.

- ĐK2: đóng gói dạng cây và tên văn bản rút gọn (P3) để lấy lại ngân sách token đang tốn cho phần lặp; thu hẹp phần lớn khoảng cách độ phủ với ĐK1-128.
- ĐK3: kho tri thức thêm thông tin không có sẵn trong nguyên văn: chủ thể và chế tài kế thừa từ câu dẫn, khóa tìm kiếm theo trường quy phạm, quan hệ dẫn chiếu và cạnh sửa đổi; dùng ở bước truy xuất, không chỉ in thêm một dòng.
- ĐK4: kiểm chứng đúng như đề cương mô tả: bằng chứng (sửa lỗi loại nhầm câu dẫn), tham chiếu tồn tại, và quan hệ thời gian, trạng thái hiệu lực; bản ghi vi phạm bị loại hoặc đánh dấu không dùng.

Rủi ro lớn nhất không nằm ở thiết kế mà ở nhãn người: không có nhãn người thì mọi cải thiện ở đây vẫn không báo cáo được (mục 6).

## 2. Đánh giá những gì đã làm

### 2.1. ĐK2

Điểm mạnh đã vững trên ba bộ và hai model: độ chính xác trích dẫn theo ký tự gấp 2,5-3 lần ĐK1-384 (+0,15 đến +0,21, thắng/thua 36/6, 39/3, 22/1), tải kiểm chứng 250 so với 550 token mỗi phát biểu, 100% trích dẫn trỏ tới đúng một đơn vị lá.

Điểm yếu: độ phủ ở bộ khó thua ĐK1 khi ĐK1 dùng cỡ đoạn mạnh nhất.
Gộp 99 câu bộ khó ở 3.000 token, ĐK2-P2 đạt 0,588, ĐK1-128 đạt 0,652 (chênh +0,064 [+0,020; +0,109]).

Nguyên nhân đã đo (`analysis-2026-11-22-dk2/density.py`):

| Bộ | ĐK2-P2: bản ghi / đơn vị / token nguyên văn ở 3.000 token | ĐK1-128: đoạn / đơn vị / token nguyên văn |
|---|---|---|
| Tình huống | 25,8 / 25,8 / 1.534 | 19,8 / 68,4 / 2.528 |
| Xung đột | 25,8 / 25,8 / 1.819 | 20,0 / 63,6 / 2.558 |
| Phức tạp | 25,7 / 25,7 / 1.721 | 19,8 / 66,7 / 2.534 |

Khoảng 40% ngân sách của ĐK2-P2 không phải nguyên văn: câu dẫn của Khoản in lại ở mọi Điểm (khoảng 600-780 token mỗi câu hỏi) và tiêu đề khối với tên văn bản đầy đủ (khoảng 450-490 token).

Phân loại 59 đơn vị đáp án chỉ ĐK1-128 tìm thấy ở 3.000 token (`misses.json`):

| Nhóm | Số đơn vị |
|---|---|
| Khoản, Điểm anh em trong Điều đã có trong ngữ cảnh, bị bỏ do giới hạn 3 Điều và 400 token của P2 | 31 |
| Có hạng trong top 50 nhưng hết ngân sách trước khi tới | 29 |
| Đơn vị ngắn dưới 25 từ | 13 |
| Nối được qua dẫn chiếu | 8 |

Các nhóm chồng lên nhau.
Ngoài ra có 131 đơn vị cả hai cùng trượt; 71 trong số đó nằm ngoài cả 160 hạng đầu của ĐK2 (50 ở bộ tình huống), tức là lệch từ ngữ giữa lời kể vụ việc và lời văn luật, ví dụ "thỏa thuận miệng" so với "bằng lời nói" ở khoản 2 Điều 14.
Nhóm này không sửa được bằng đóng gói; đây là chỗ một kho tri thức có thể giúp (mục 4.2).

### 2.2. ĐK3

Đo trên kho v1 (gpt-oss-120b) và v3 (Sonnet 5.5), `analysis-2026-11-22-dk34/summary.json`:

- Dòng quy phạm gần như không có chữ mới: 0,11% (v1) và 0,49% (v3) số từ của các ô nằm ngoài nguyên văn đơn vị; ở ĐK4 là 0%, vì bộ kiểm chứng buộc mọi ô phải nguyên văn.
- Thông tin mới thật sự chỉ có nhãn tính quy phạm khi câu không có từ tình thái (44% quy phạm ĐK4 v3) và cách tách vai.
- Chủ thể để trống ở 61% quy phạm v3, vì chủ thể ngầm định nằm ở câu dẫn của đơn vị cha.
- Model sinh không dùng dòng quy phạm: cụm ba từ chỉ có trong dòng quy phạm xuất hiện ở 2-5 trên 150-320 phát biểu, và khi đọc tay đều là cụm vắt qua ranh giới hai ô; 0/125 giá trị cài lỗi bị lặp lại; prompt `answer-v4.md` không nhắc tới dòng quy phạm.
- Dòng quy phạm làm bản ghi dài hơn (56 so với 45 token) nên ĐK3 thường hơi kém ĐK2 ở cùng ngân sách.
- Độ phủ quy phạm trên đơn vị đáp án: 0,66 (tra cứu v1) và 0,68 (ba bộ khó v3) có ít nhất một quy phạm ở ĐK3; đây là trần của mọi thiết kế chỉ dựa vào quy phạm như ĐK3-q.

Kết luận: với thiết kế "nguyên văn cộng dòng quy phạm", ĐK3 không thể khác ĐK2, trừ phần mở rộng theo dẫn chiếu.
Kết quả âm của H0a là hệ quả thiết kế, không phải phát hiện về giá trị của kho tri thức.

### 2.3. ĐK4

- `kb-validator-v3` chỉ kiểm hình thức: lược đồ, đơn vị và câu tồn tại, mọi ô nguyên văn trong câu, từ tình thái nguyên văn, trùng lặp; không kiểm chủ thể, không kiểm nghĩa, không kiểm thời gian và trạng thái.
- Tỉ lệ bị loại: 7,5% (v1), 5,0% (v2), 4,4% (v3).
- Ở v3, 136/181 quy phạm bị loại vì ô "không nguyên văn" thật ra nằm nguyên văn ở câu dẫn của đơn vị cha (ví dụ "Phạt tiền" của khoản xử phạt); lỗi thật chỉ 45.
- Trong đơn vị đáp án bộ khó, 26/288 đơn vị mất hết quy phạm ở ĐK4; số câu có mọi đơn vị đáp án được phủ giảm từ 28 xuống 14 trên 90.
- RQ1 xem trước trên gold tạm (176/290 câu của Kha, mức lenient): F1 quy phạm ĐK3 0,35, ĐK4 0,37; kiểm chứng tăng precision bằng recall, gần như trung tính.
- Thí nghiệm cài lỗi: bộ kiểm chứng chặn 122/125 lỗi khỏi kho, nhưng lỗi vốn không lan sang câu trả lời ở ĐK3, nên ĐK4 không có gì để cứu ở tầng câu trả lời.

Kết luận: giá trị của ĐK4 hiện chỉ thấy ở tầng kho (RQ2), và một phần lớn "giá trị" đó là loại nhầm.

### 2.4. Hiệu lực

Bộ hiệu lực v1 (30 câu nháp, `validity-dryrun-2026-11-16/summary.json`, BM25):

| Điều kiện | Tỉ lệ câu có đơn vị lỗi thời trong ngữ cảnh, 3.000 token | Recall, 3.000 token |
|---|---|---|
| ĐK1-128, không lọc | 0,81 | 0,64 |
| ĐK1-hl, lọc mức văn bản | 0,52 | 0,71 |
| ĐK2, không lọc | 0,71 | 0,59 |
| ĐK2, lọc mức đơn vị | 0,00 | 0,68 |

Đây là hiệu ứng lớn nhất trong dự án.
Nhưng cấu hình `validity/` hiện cấp cùng bộ lọc mức đơn vị cho ĐK2, ĐK3 và ĐK4, nên nó chỉ góp vào so sánh ĐK2 với ĐK1.

### 2.5. ĐK3-q, ĐK4-q

Code đã nối đủ (`retrieval/norm_query.py`, `record: norm_lines`, preflight, test), nhưng chưa có `query_slots.jsonl` (cần gọi model), `actor-aliases.json` còn ở trạng thái nháp, và gold chưa xuất bản cuối.
Chạy thử `enum-gate` trên gold tạm (7 câu mức Điều) cho độ phủ trích xuất ĐK3 0,50, ĐK4 0,46, dưới ngưỡng 60% đã khai báo; số này rất nhỏ và chưa chính thức.
13 đơn vị không có quy phạm là các điểm khung phạt của Điều 17 NĐ 12/2022, nơi người gán coi là quy phạm định lượng còn model không trích.

## 3. ĐK2: đề xuất

### 3.1. P3: đóng gói dạng cây và tên văn bản rút gọn (ưu tiên 1)

Thiết kế: giữ nguyên xếp hạng và phần thêm anh em của P2; trong một khối Điều, câu dẫn của mỗi Khoản chỉ in một lần, các Điểm in thụt dưới nó; tiêu đề khối dùng tên rút gọn tới số hiệu (ví dụ "NĐ 145/2020/NĐ-CP, Điều 70") thay tên đầy đủ.
Mỗi Điểm vẫn giữ mã đoạn riêng, nên trích dẫn vẫn tới Điểm.

Đo bằng mô phỏng chi phí trên thứ hạng đã lưu (`variants.py`), so với P2, 99 câu bộ khó:

| Biến thể | 2.000 token | 3.000 token |
|---|---|---|
| P3 (cây + tên rút gọn) | +0,018 [+0,006; +0,034], 7/0 | +0,032 [+0,015; +0,052], 12/0 |
| P3 + `rrf_candidates` 100 | +0,051 [+0,022; +0,084], 20/4 | +0,045 [+0,014; +0,077], 23/5 |

Với P3 cộng `rrf_candidates` 100, khoảng cách tới ĐK1-128 còn +0,019 [-0,020; +0,058] ở 3.000 token, nằm trong biên không kém 0,05 của H2.
P3 không làm câu nào thua, vì nó chỉ dùng lại phần ngân sách đang lãng phí.

Việc cần làm: cài bố cục cây và chi phí theo Khoản trong `indexing/packing.py` (dùng chung cho truy xuất và sinh câu trả lời), test thứ tự khối, mã đoạn, ngân sách, không lặp đơn vị; đo lại bằng chuỗi thật thay vì mô phỏng.
Chi phí: offline.

Rủi ro: tên rút gọn làm model nhầm văn bản (thấp, số hiệu vẫn còn); ngữ cảnh nhiều đơn vị hơn có thể làm model trích dẫn rộng hơn và giảm độ chính xác theo ký tự, chỉ đo được ở lượt sinh.

### 3.2. `rrf_candidates` 100 (ưu tiên 2)

Riêng biến thể này chỉ +0,011 [-0,016; +0,042] ở 3.000 token.
Đây là thiết lập dùng chung, nên phải áp cho mọi điều kiện, kể cả ĐK1, và chọn theo chỉ số của từng điều kiện, không theo chênh lệch.

### 3.3. Không nhận

- Chấm điểm phân cấp theo Điều bằng BM25: -0,045 [-0,085; -0,006] ở trọng số 1, thiên về Điều dài.
- In cả Điều cho mọi khối: không tăng recall, khối phình to, hại tải kiểm chứng.
- Mở rộng dẫn chiếu sang văn bản khác cho ĐK2: chỉ 8/59 lỗi nối được qua dẫn chiếu; việc này thuộc về ĐK3.

### 3.4. Hiệu lực ở ĐK2

Đề xuất ĐK2 chỉ dùng siêu dữ liệu văn bản (lọc mức văn bản, giống ĐK1-hl), vì đề cương định nghĩa ĐK2 là "chia theo cấu trúc kèm metadata nguồn".
Trạng thái từng Khoản, Điểm tính từ cạnh sửa đổi là tri thức trích từ văn bản sửa đổi, nên thuộc về kho tri thức (mục 4, 5).
Đây là lựa chọn A/B ở mục 7, câu 1.

## 4. ĐK3: kho tri thức thêm thông tin không có trong nguyên văn

### 4.1. Kế thừa câu dẫn (ưu tiên 1, offline)

Trước khi đánh chỉ mục và kiểm chứng, Điểm và Khoản con nhận chủ thể, hành vi và chế tài từ câu dẫn của đơn vị cha khi ô của chúng trống, kèm offset nguyên văn của câu dẫn (bằng chứng vẫn trỏ về văn bản gốc).
Đây là nguyên nhân đã biết từ 08/11 của cả chủ thể trống (61%) lẫn phần lớn số bị loại nhầm.
Đo được ngay: tỉ lệ quy phạm có chủ thể, độ phủ đơn vị đáp án, recall của ĐK3-q, F1 trên gold tạm.
Phiên bản mới: `claims-inherit-v1`, khai báo là biến thể mới trước khi đo trên nhãn người.

### 4.2. Khóa tìm kiếm từ kho tri thức (ưu tiên 2)

Mục tiêu: đánh vào nhóm 71 đơn vị nằm ngoài 160 hạng, lỗi lệch từ ngữ mà không cách đóng gói nào sửa được.
Mỗi đơn vị có quy phạm được thêm vào chỉ mục (không đưa vào phần model đọc) các khóa:

1. Tất định, không tốn tiền: tên chủ thể chuẩn hóa theo bảng bí danh (sau 4.1), nhãn tính quy phạm bằng lời thường ("nghĩa vụ", "bị cấm", "được quyền", "bị phạt"), chế tài kế thừa.
2. Do model soạn: hai đến ba câu hỏi ngắn mà quy phạm đó trả lời, viết theo cách người hỏi kể sự việc, sinh từ các ô của quy phạm và nguyên văn (cách làm của doc2query và "contextual retrieval"; cần đối chiếu bản gốc trước khi trích dẫn trong chương 2).

Khóa chỉ dùng để tìm; câu trả lời vẫn chỉ dựa vào nguyên văn và trích dẫn vẫn kiểm bằng offset.
Khóa của quy phạm bị bộ kiểm chứng loại cũng bị loại ở ĐK4.

Thứ tự làm và cổng:

1. Khóa tất định trên dev, offline: đo recall theo ngân sách của ĐK3 so với ĐK2 trên bộ khó.
2. Lượt thử khóa do model soạn trên các Điều chạm tới tập dev của bộ khó, ước tính 1-2 USD; cổng: recall của ĐK3 ở 3.000 token hơn ĐK3 chỉ có khóa tất định ít nhất 0,03 (ngưỡng phải chốt trước khi chạy).
3. Qua cổng thì chạy toàn corpus v3 (3.862 đơn vị lá có quy phạm) và corpus v1 cho bộ tra cứu.
   Ước tính dựa trên lượt trích kho v3 (863 lô, 16,97 USD, đầu ra lớn hơn nhiều): khoảng 5-12 USD với Sonnet 5.5, thấp hơn với Haiku 5.5; con số thật lấy từ lượt thử.

Mối đe dọa: khác biệt ĐK3 so với ĐK2 khi đó đến từ "làm giàu chỉ mục", mà về nguyên tắc cũng làm được trên ĐK2.
Cách xử lý: khóa được sinh từ các ô của quy phạm, nên đây là đóng góp của biểu diễn có cấu trúc; báo cáo thêm ĐK3 chỉ có khóa tất định để tách phần do model soạn.

### 4.3. Thu gọn dòng quy phạm trong phần model đọc

Vì dòng quy phạm không mang chữ mới, chỉ in phần thông tin mới thật sự: nhãn tính quy phạm, chủ thể kế thừa, và ghi chú trạng thái hiệu lực.
Phần ngân sách tiết kiệm được dùng cho nguyên văn, như P3 làm với ĐK2.

### 4.4. Đồ thị: dẫn chiếu và cạnh sửa đổi, chưa kiểm chứng

Giữ mở rộng dẫn chiếu hai chiều hiện có.
Theo lựa chọn B ở mục 7, thêm cạnh sửa đổi (`amendment-rules-v2`) như quan hệ của kho: khi một đơn vị được chọn, đơn vị sửa nó hoặc bị nó sửa được kéo vào cùng ghi chú quan hệ, nhưng chưa có bước kiểm trạng thái, nên đơn vị cũ vẫn có thể nằm trong ngữ cảnh.

### 4.5. ĐK3-q cho câu liệt kê, có định tuyến

Giữ ĐK3-q và ĐK4-q làm nơi kho quy phạm được đọc trực tiếp; chỉ câu được phân tích là liệt kê mới đi đường này.
Chạy lại `enum-gate` sau 4.1, vì trần độ phủ 0,50-0,68 có thể không qua ngưỡng 60%; nếu vẫn không qua, báo cáo ở tầng truy xuất như kế hoạch 11/11.
Chi phí: khoảng 40 lượt `query-slots` cộng phần sinh câu trả lời.

## 5. ĐK4: kiểm chứng theo đúng đề cương

Đề cương mục 4.4 và Bảng 2: kiểm chứng gồm lược đồ, tham chiếu, trùng lặp, quan hệ thời gian, trạng thái, mâu thuẫn và đối chiếu bằng chứng; bản ghi vi phạm bị loại hoặc đánh dấu không dùng.
Bộ kiểm chứng hiện tại chỉ làm phần lược đồ, bằng chứng và trùng lặp.

### 5.1. `kb-validator-v4`: bằng chứng chấp nhận câu dẫn

Ô không có trong câu nhưng có nguyên văn ở câu dẫn của đơn vị cha được chấp nhận, kèm offset của câu dẫn.
Theo số ở mục 2.3, việc này bỏ được khoảng 75% số bị loại ở v3, chỉ giữ lại lỗi thật.
Đo offline: lượng bị loại theo lý do, P/R trên gold tạm, và trên bảng kiểm tra 104 dòng khi có nhãn.

### 5.2. Kiểm tham chiếu và quan hệ thời gian

- Cạnh dẫn chiếu và cạnh sửa đổi phải giải được tới đơn vị có trong corpus; cạnh không giải được bị đánh dấu không dùng thay vì suy đoán.
- Trạng thái mỗi đơn vị tại ngày của câu hỏi (`unit-status-v2`): đơn vị hết hiệu lực, bị bãi bỏ hoặc chưa có hiệu lực bị loại; đơn vị đã bị sửa được thay bằng đơn vị sửa kèm ghi chú.
- Quy phạm của đơn vị lỗi thời bị đánh dấu không dùng.

Theo lựa chọn B, đây là chỗ ĐK4 khác ĐK3 rõ nhất: trên bộ hiệu lực, ĐK3 (có cạnh sửa đổi nhưng chưa kiểm) dự kiến vẫn có đơn vị lỗi thời trong ngữ cảnh, còn ĐK4 về 0 như ĐK2 lọc mức đơn vị ở bảng 2.4.
Đây là dự đoán từ cơ chế, chưa đo trên thiết kế mới.

### 5.3. Đo lan truyền lỗi ở nơi lỗi có thể lan

Thí nghiệm cài lỗi chỉ có nghĩa khi model sinh đọc quy phạm thay vì nguyên văn: đo ở ĐK3-q so với ĐK4-q (H5), không đo ở ĐK3/ĐK4 dạng nguyên văn.
Với khóa tìm kiếm ở 4.2, thêm phép thử thứ hai: khóa sinh từ quy phạm cài lỗi kéo đơn vị sai vào ngữ cảnh (lỗi lan qua truy xuất), ĐK4 chặn được bao nhiêu.

### 5.4. Có nên đổi ĐK4 thành kho do người duyệt không

Khuyến nghị: không thay ĐK4; báo cáo "ĐK4 cộng người duyệt" như biến thể mở rộng, đúng như đề cương mục 4.7 đã viết.
Lý do:

- Duyệt toàn bộ 4.933 quy phạm v3 không khả thi trước khoảng 02/12, và nhãn người đang là nút thắt.
- Gold 40 Điều đã là một kho do người duyệt; dùng nó làm "kho trần" cho phép đo trần lợi ích của kiểm chứng mà không tốn thêm công người.
- Cảnh báo: không được dùng kho trần này trên bộ liệt kê, vì bộ liệt kê suy ra từ chính gold, kết quả sẽ hoàn hảo một cách vòng tròn; chỉ dùng trên bộ tra cứu v1 (corpus v1 chứa 40 Điều của gold, cần kiểm lại khi làm).

## 6. Đánh giá và thống kê

- Với 25-99 câu và nhiễu sinh cộng nhiễu chấm khoảng ±0,07, chênh lệch độ đúng cỡ 0,05 giữa ĐK3 và ĐK4 không phát hiện được.
  Vì vậy chỉ số chính của các giả thuyết về ĐK3, ĐK4 phải là chỉ số tất định: recall theo ngân sách, tỉ lệ trích dẫn đơn vị lỗi thời, F1 tập đơn vị của câu liệt kê, tỉ lệ lặp lỗi cài.
  Độ đúng theo giám khảo là phân tích bổ sung.
- Mọi thay đổi ở đây được chọn sau khi xem dữ liệu dev có nhãn model, nên phải ghi vào `docs/decisions.md` như biến thể khai báo trước, kèm chỉ số và ngưỡng chọn, trước khi đo trên nhãn người; held-out vẫn chạy đúng một lần.
- Giả thuyết đề xuất sửa (thay mục 4 của kế hoạch 11/11 sau khi nhóm đồng ý):

| Mã | Giả thuyết | So sánh | Chỉ số chính |
|---|---|---|---|
| H1 | Giữ nguyên | ĐK2 so với ĐK1 | Độ chính xác trích dẫn theo ký tự |
| H2 | ĐK2 với P3 không kém ĐK1-128 về độ phủ | ĐK2 so với ĐK1 | Recall ở 3.000 token, biên 0,05, bộ khó |
| H3 | Kiểm chứng trạng thái giảm trích dẫn lỗi thời | ĐK4 so với ĐK3 (lựa chọn B), ĐK2 so với ĐK1-hl | Tỉ lệ câu trả lời trích dẫn đơn vị lỗi thời, bộ hiệu lực |
| H4 | Giữ nguyên, sau kế thừa câu dẫn | ĐK3-q so với ĐK2 | F1 tập đơn vị, bộ liệt kê |
| H5 | Giữ nguyên | ĐK4-q so với ĐK3-q | Tỉ lệ lặp lỗi cài |
| H6 (mới) | Khóa từ kho tri thức tăng độ phủ ở câu khó | ĐK3 so với ĐK2 | Recall ở 3.000 token, bộ khó |
| H0a, H0b | Giữ từ đề cương, báo cáo bổ sung | ĐK3 so với ĐK2, ĐK4 so với ĐK3 | Độ đúng theo giám khảo |

Về nhãn: nếu đến khoảng 28/11 bộ khó vẫn chưa có nhãn của hai người, nên dùng phương án lùi đã khai báo (bộ tra cứu mẫu 80 câu, gold 30 Điều) và thu nhỏ bộ khó về các câu đã có nhãn, thay vì thêm biến thể.
Các cải thiện ở tài liệu này không thay được nhãn người.

## 7. Câu hỏi cần nhóm quyết

Người dùng đã trả lời câu 1-3 ngày 22/11 (ghi ở `docs/decisions.md`): câu 1 chọn B; câu 2 chạy khóa do Claude Sonnet 5.5 soạn, có lượt thử và cổng; câu 3 khai báo cả P3 và `rrf_candidates` 100.
Câu 4 còn mở.

1. Hiệu lực mức đơn vị thuộc bậc nào?
   - A: giữ như hiện tại, cấp cho ĐK2-ĐK4; H3 chỉ là ĐK2 so với ĐK1; ĐK4 không được tính công phần hiệu lực.
   - B (khuyến nghị): ĐK2 chỉ lọc mức văn bản; cạnh sửa đổi là tri thức của ĐK3; kiểm trạng thái là kiểm chứng của ĐK4. Khớp đề cương mục 4.4 hơn, cho ĐK4 một cơ chế đo được, nhưng đổi cách phát biểu H3 đã khai báo ngày 11/11.
2. Có chạy khóa tìm kiếm do model soạn (4.2, mục 2 và 3) không, và bằng model nào (Sonnet 5.5 hay Haiku 5.5)?
3. Có khai báo P3 và `rrf_candidates` 100 là biến thể của WP3 và áp quy tắc chọn trước mốc mới không?
4. Có đồng ý đổi bộ giả thuyết như bảng ở mục 6 không, và báo giảng viên thế nào?

## 8. Lịch đến mốc dừng biến thể khoảng 02/12

| Ngày | Việc | Chi phí |
|---|---|---|
| 23-24/11 | Ghi quyết định mục 7; cài P3 trong `packing.py`, kế thừa câu dẫn, `kb-validator-v4`, khóa tất định, lựa chọn hiệu lực A hoặc B; test | Offline |
| 25/11 | Đo lại trên dev bằng chuỗi thật: recall theo ngân sách ĐK1-ĐK4, bộ hiệu lực, `enum-gate`, gold tạm | Offline |
| 25-26/11 | Lượt thử khóa do model soạn; quyết theo cổng ở 4.2 | 1-2 USD, cần duyệt |
| 26-28/11 | Khóa do model soạn toàn corpus nếu qua cổng; `query-slots` bộ liệt kê; thử lại 9Router | 5-15 USD, cần duyệt |
| 28-30/11 | Chạy lại truy xuất mọi điều kiện; `preflight`; áp quy tắc chọn đã khai báo trên nhãn người đã có | Offline |
| khoảng 02/12 | Dừng thêm biến thể; lượt chính sau đó | |

Phần còn lại của lịch (chấm, thống kê, viết) dời khoảng một tuần so với `progress-2026-11-16.md`; mốc nộp 20/12 không đổi nên phần dự phòng 19-20/12 bị dùng.

## 9. Ghi chú về tài liệu tham khảo

Các kỹ thuật nêu ở 4.2 (doc2query, contextual retrieval) và đóng gói từ đơn vị nhỏ lên đơn vị lớn ("small-to-big", parent document) là kiến thức chung của nhóm phân tích; chưa tra bản gốc trong phiên này.
Danh sách đọc ở WP8 của kế hoạch 11/11 vẫn là nguồn chính cho chương 2; mọi trích dẫn phải đối chiếu bản gốc trước khi dùng.
