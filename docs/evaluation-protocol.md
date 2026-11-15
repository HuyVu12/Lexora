# Giao thức thực nghiệm

## Khóa dữ liệu trước tinh chỉnh
Mục tiêu 150 câu: dự thảo 60 tra cứu, 45 tổng hợp, 25 hiệu lực/sửa đổi, 20 ngoài phạm vi/thiếu căn cứ. Chốt phân bố sau pilot và lưu lý do. Chia phân tầng khoảng 105 dev/45 held-out; gom các câu diễn đạt lại và cùng tình huống vào cùng split để giảm rò rỉ. Khóa danh sách ID và hash trước tối ưu pipeline. Held-out không dùng chọn model/prompt/top-k; nếu đã xem để sửa hệ thống thì công bố vi phạm và tạo tập kiểm tra mới khi có thể.

## Gold extraction
40–60 điều khoản; hai người gán nhãn độc lập trước khi đối soát. Chốt tập đơn vị gán nhãn và nhãn phân loại để tính Cohen’s kappa; không áp dụng trực tiếp kappa lên các span tự do không căn chỉnh. Báo cáo span/relation F1 riêng. Lưu hai bản annotation gốc, bản adjudicated và lý do bất đồng. Đây không phải xác nhận chuyên gia pháp lý.

## ĐK1–ĐK4
Dùng chung corpus nguồn, câu hỏi, generator và revision, embedding, top-k, ngân sách token context, decoding, seed (nếu backend hỗ trợ) và rubric. Mỗi điều kiện có index riêng. ĐK4 phải xuất phát từ cùng snapshot extraction của ĐK3. Ánh xạ mọi chunk/claim về unit ID để so Recall@K công bằng. Nếu cần tối ưu riêng từng điều kiện, chỉ dùng dev và báo cáo thành thí nghiệm phụ.

## Chỉ số và cách tính
- Entity/relation precision, recall, F1: chốt exact-match/normalized-match trước chạy; báo cáo cả số lượng và quy tắc matching.
- Validation: phát hiện lỗi theo loại, false reject, lỗi còn sót trên mẫu gold và bộ lỗi chèn có nhãn. Báo cáo mẫu số; không lấy chính validator làm ground truth.
- Recall@K: số unit liên quan truy xuất được / số unit liên quan chuẩn, trung bình trên câu có relevant units; báo cáo K đã khóa.
- Citation accuracy: số citation đúng căn cứ / tổng citation; thêm tỷ lệ câu trả lời không có citation.
- Grounding: tỷ lệ phát biểu được evidence hỗ trợ, theo rubric người chấm.
- Correctness: rubric 0 sai, 1 đúng một phần, 2 đúng và đủ căn cứ; khóa mẫu chấm phân tầng cho mọi điều kiện.
- Từ chối đúng: số câu cần từ chối được từ chối / số câu cần từ chối; báo cáo thêm từ chối nhầm trên câu trả lời được.
- Độ trễ, token, thời gian GPU và chi phí: ghi từng run; không thay thế chỉ số chất lượng.

Không đặt ngưỡng chất lượng giả định thành kết quả. Báo cáo số mẫu, missing/error, chênh lệch theo từng câu và khoảng bất định nếu đủ mẫu. Kết quả âm vẫn là kết quả nghiên cứu. LLM judge chỉ bổ sung cho đánh giá người.

## Bổ sung từ kế hoạch 11/11 và các quyết định 15/11/2026

Phần này ghi các điểm đã chốt sau bản giao thức đầu; chi tiết và lý do nằm ở `planning/research-plan-2026-11-11.md` và `decisions.md`.

### Bộ dữ liệu và corpus

- Bộ tra cứu v1 (152 câu) chạy trên corpus v1 (94 Điều) với kho quy phạm của gpt-oss-120b.
- Bộ khó (tình huống, xung đột, phức tạp) và bộ hiệu lực chạy trên corpus v3 với kho quy phạm của Sonnet 5.5.
- Hai nhóm được báo cáo riêng; không so số ĐK3/ĐK4 giữa hai nhóm, vì khác cả corpus lẫn model trích xuất.
- Bộ hiệu lực v1: mỗi câu có ngày áp dụng (`as_of`), tập đơn vị đáp án tại ngày đó và tập đơn vị lỗi thời (`stale_unit_ids`), suy ra từ metadata văn bản và cạnh sửa đổi `amendment-rules-v1`.
- Bộ liệt kê v1 suy ra từ gold trích xuất đã đối soát; precision chỉ tính trên đơn vị có nhãn.

### Người gán nhãn

- Bộ câu hỏi: Kha gán độc lập, không xem đề xuất; Vũ gán dưới tài khoản của mình ở chế độ có xem đề xuất của model.
- Tệp đã khóa ghi chế độ của từng người; báo cáo phải nêu rằng đồng thuận khi một bên duyệt đề xuất thường cao hơn gán độc lập.
- Nhãn do model gán (đề xuất, rà soát) không bao giờ được ghi hay báo cáo như nhãn người.
- Gold trích xuất: Kha gán đủ 40 Điều; Vũ tự gán độc lập một mẫu phân tầng khoảng 30% (12 Điều) chọn bằng hạt giống cố định trước khi có nhãn của người thứ hai.
- Đồng thuận của gold đo trên phần hai người cùng gán; phần còn lại là nhãn một người gán và được đánh dấu như vậy.
- RQ1 báo cáo điểm trên toàn bộ gold và trên riêng phần hai người gán.
- Gold không dùng đề xuất model, vì gold dùng để chấm chính model trích xuất.

### Quy ước nhãn của bộ khó

- Câu không ghi ngày được hiểu là hỏi tại ngày khóa corpus v3 (11/11/2026): đáp án là đơn vị còn hiệu lực tại ngày đó, đơn vị hết hiệu lực hoặc đã bị sửa đổi là lỗi thời.
- Câu tình huống có ngày xảy ra việc thì theo quy định tại ngày đó.
- Quy định được nhắc lại ở hai văn bản thì chọn cả hai đơn vị.
- Bộ tình huống chỉ giữ đơn vị mà bản án dựa vào; 9 câu tin cậy thấp bị loại khỏi bộ khóa (còn 35 câu).
- Cách chấm recall coi đơn vị cha được phủ khi tìm thấy bất kỳ đơn vị con nào của nó; nhãn model rà soát vì thế bỏ đơn vị cha khi đã có đơn vị con trong cùng danh sách.

### Chỉ số bổ sung

- Recall theo ngân sách token (250 đến 6.000) dùng đúng hàm đóng gói của lượt sinh câu trả lời; kèm ngân sách nhỏ nhất để đạt ngưỡng recall nêu trước (0,8 cho bộ tra cứu, 0,4 cho bộ khó).
- Độ chính xác trích dẫn theo ký tự: phần ký tự của các bản ghi được trích dẫn nằm trong đơn vị đáp án.
- Tải kiểm chứng: số token của bản ghi được trích dẫn chia cho số phát biểu, và tỉ lệ trích dẫn trỏ tới đúng một đơn vị lá.
- Hiệu lực: tỉ lệ câu trả lời trích dẫn đơn vị lỗi thời (chỉ số chính của H3), tỉ lệ ngữ cảnh chứa đơn vị lỗi thời, recall đơn vị đúng phiên bản.
- Liệt kê: P, R, F1 của tập đơn vị được trích dẫn so với gold (chỉ số chính của H4), tỉ lệ câu trả lời lặp lại giá trị cài lỗi (chỉ số chính của H5).
- Precision của trích dẫn luôn báo cáo kèm recall và số phát biểu.

### Kiểm định và mức nhiễu

- Bốn so sánh chính (ĐK1-ĐK2, ĐK2-ĐK3, ĐK3-ĐK4, ĐK1-ĐK4) dùng bootstrap ghép cặp theo câu hỏi, 10.000 lần, hạt giống cố định, hiệu chỉnh Holm; mọi so sánh khác ghi là thăm dò.
- Mỗi câu của bộ khó được sinh hai lần; chênh lệch giữa hai lần sinh của cùng điều kiện là mức nhiễu sinh.
- Giám khảo chấm lại 50 câu trả lời lần hai để có mức nhiễu giám khảo.
- Mọi chênh lệch giữa các điều kiện được trình bày cạnh hai mức nhiễu này.
- Câu thiếu ở một trong hai lượt của một cặp so sánh được đếm và báo cáo, không bị bỏ âm thầm.

### Chọn cấu hình

- Mọi lựa chọn (cỡ đoạn ĐK1, biến thể đóng gói, prompt, ngân sách) chọn trên dev theo chỉ số của một điều kiện đã nêu trước, không theo độ chênh giữa các điều kiện, rồi khóa.
- ĐK1 chính dùng đoạn 128 token, gối 21; ĐK2-ĐK4 dùng đóng gói P2 (`pack-article-v1`), được áp lại một lần nếu nhãn người sau khi khóa đổi thứ tự P0, P1, P2.
- Dừng thêm biến thể từ 25/11/2026; held-out chạy đúng một lần.
