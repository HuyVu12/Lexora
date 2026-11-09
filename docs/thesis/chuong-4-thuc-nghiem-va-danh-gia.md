# Chương 4. Thực nghiệm và đánh giá

> Khung chương, bản nháp ngày 09/11/2026.
> Mọi ô kết quả ghi **(chờ kết quả)** chỉ được điền từ các lượt chạy thật trên bộ câu hỏi và gold set đã khóa.
> Các chỗ đánh dấu **[mục còn mở]** chưa được chốt; xem mục 4.9.

Chương này trình bày thiết kế thực nghiệm, cách xây dựng bộ dữ liệu đánh giá và độ tin cậy của nhãn, các chỉ số cho từng câu hỏi nghiên cứu, kết quả, phân tích lỗi và các mối đe dọa tới tính hợp lệ của kết luận.

## 4.1. Thiết kế thực nghiệm

### 4.1.1. Nguyên tắc chung

- Một corpus duy nhất: "Phạm vi thực nghiệm v1", phiên bản 1 (`veaeaad4a6edc`), 5 văn bản, 94 Điều, 617 đơn vị.
- Bộ câu hỏi và gold set được khóa **trước** khi chạy thật; tập held-out chỉ chạy một lần, sau khi mọi cấu hình đã khóa.
- Mọi thay đổi phương pháp sau khi khóa đều được ghi lý do trong nhật ký quyết định.
- Mỗi lượt chạy ghi manifest (cấu hình, mã băm dữ liệu đầu vào, model, prompt) và lưu nguyên văn đầu ra của model để tái lập.

### 4.1.2. Bốn điều kiện đối chứng

| Điều kiện | Bản ghi để truy xuất | Yếu tố thay đổi so với bậc trước |
|---|---|---|
| ĐK1 | Đoạn 384 token, gối nhau 64 token, cắt từ văn bản liền | Baseline |
| ĐK2 | Đơn vị lá (điểm, khoản, hoặc Điều không chia khoản) kèm tên văn bản, đường dẫn cấu trúc, tên Điều và câu dẫn | Tôn trọng cấu trúc văn bản |
| ĐK3 | Bản ghi của ĐK2 cộng thêm các quy phạm do LLM trích xuất từ đơn vị đó (chưa kiểm chứng); truy xuất có mở rộng theo đồ thị dẫn chiếu | Biểu diễn tri thức có cấu trúc |
| ĐK4 | Như ĐK3, chỉ gắn các quy phạm qua được bộ kiểm chứng | Kiểm chứng tri thức |

ĐK3 và ĐK4 lấy từ **cùng một lượt trích xuất** (`kb-scope-v1-gpt-oss-120b`); ĐK4 là tập con của ĐK3.
Bản ghi ĐK3/ĐK4 giữ nguyên văn, đường dẫn và câu dẫn của ĐK2; đơn vị không có quy phạm giữ bản ghi như ĐK2.
Nhờ vậy khác biệt ĐK2-ĐK3 chỉ đến từ phần tri thức có cấu trúc (các quy phạm và đồ thị), không đến từ việc mất nội dung.

Đồ thị dẫn chiếu (`reference-expansion-v2`) gồm các dẫn chiếu tường minh đã giải được ("theo quy định tại khoản 1 Điều 36"), theo hai chiều: đơn vị được dẫn chiếu, và đơn vị dẫn chiếu tới đơn vị đang xét (ví dụ Điều 8 Nghị định 145/2020 hướng dẫn Điều 46 Bộ luật Lao động).
Sau khi xếp hạng, mỗi bản ghi tìm được kéo theo tối đa hai láng giềng trên đồ thị, với điều kiện láng giềng đó cũng khớp câu hỏi (nằm trong danh sách ứng viên của bộ truy xuất); tổng số bản ghi vẫn là K nên không điều kiện nào được thêm ngữ cảnh.
Điều kiện "láng giềng phải khớp câu hỏi" được thêm sau khi chạy thử cho thấy các Điều được dẫn chiếu rất nhiều (như Điều về hiệu lực thi hành) bị kéo vào ở hầu hết câu hỏi và đẩy mất bản ghi đúng.

Các biến thể phụ được chạy và báo cáo cùng, để tách tác động của từng thành phần:

| Biến thể | Khác điều kiện chính ở |
|---|---|
| ĐK3/ĐK4 chỉ quy phạm | Mỗi bản ghi chỉ là một quy phạm đã tuần tự hóa, không có nguyên văn (thiết kế đầu tiên, 07/11) |
| ĐK3/ĐK4 không đồ thị | Bản ghi như điều kiện chính, không mở rộng theo đồ thị |
| ĐK3 đồ thị một chiều | Chỉ theo chiều đơn vị được dẫn chiếu |
| ĐK3/ĐK4 đồ thị không kiểm câu hỏi | Láng giềng được kéo vào kể cả khi không khớp câu hỏi |
Mọi bản ghi của mọi điều kiện đều ánh xạ về mã đơn vị gốc, nên các chỉ số truy xuất và trích dẫn được tính theo cùng một chuẩn.

### 4.1.3. Thiết lập dùng chung

| Thành phần | Giá trị |
|---|---|
| Phương pháp truy xuất | Chọn một trong BM25, BGE-M3, kết hợp (RRF) trên tập dev, rồi khóa **[cập nhật]** |
| BM25 | k1 = 1,2; b = 0,75; token theo âm tiết (`lexora-syllable-v1`) |
| Embedding | BAAI/bge-m3, revision `5617a9f`, chạy cục bộ |
| Kết hợp | RRF, c = 60, 30 ứng viên mỗi kênh |
| Số kết quả | top-5 |
| Model sinh câu trả lời | Một model cố định cho cả bốn điều kiện **[mục còn mở]** |
| Prompt | `answer-v1` |
| Ngân sách ngữ cảnh | 3.000 token (đếm theo âm tiết cho tới khi thay bằng tokenizer của model) |
| Giám khảo LLM bổ sung | Khác model sinh **[cập nhật]** |

### 4.1.4. Kiểm soát công bằng

Trước khi báo cáo RQ3, công cụ `preflight` phải cho kết quả đạt với các kiểm tra sau:

| Kiểm tra | Ý nghĩa |
|---|---|
| Mỗi điều kiện một lượt, đủ bốn điều kiện | Không chọn lượt tốt nhất trong nhiều lượt |
| Cùng đơn vị, cùng văn bản, cùng bộ câu hỏi | So sánh trên cùng dữ liệu (so mã băm) |
| Cùng cấu hình truy xuất và mô hình embedding | Khác biệt chỉ đến từ cách biểu diễn |
| ĐK3 và ĐK4 cùng kiểu bản ghi và cùng cấu hình đồ thị | Khác biệt ĐK3-ĐK4 chỉ do kiểm chứng |
| Cách ly chỉ mục | Không bản ghi nào lẫn giữa các điều kiện hoặc trỏ ra ngoài corpus; bản ghi khớp mã băm trong manifest |
| ĐK3 và ĐK4 cùng một lượt trích xuất, ĐK4 là tập con | Khác biệt ĐK3-ĐK4 chỉ do kiểm chứng |
| Cùng cấu hình sinh câu trả lời | Cùng nhà cung cấp, model, prompt hệ thống, top-k, ngân sách token, tập câu hỏi |
| Held-out chỉ chạy khi cấu hình đã khóa | Không tinh chỉnh trên held-out |

## 4.2. Bộ dữ liệu đánh giá

### 4.2.1. Bộ câu hỏi v1

| Đặc điểm | Giá trị |
|---|---|
| Số câu | 152 |
| Loại câu | 99 tra cứu, 25 tổng hợp nhiều đơn vị, 9 hiệu lực, 19 ngoài phạm vi |
| Kỳ vọng | 131 trả lời được, 21 phải từ chối |
| Nhóm diễn đạt lại | 20 câu diễn đạt lại một câu khác |
| Nguồn câu | Model soạn nháp theo 5 nhóm Điều, ghi nguồn `model`; hai người duyệt |
| Chia tập | Khoảng 30% held-out, chia theo **nhóm diễn đạt lại** (các câu cùng nhóm luôn nằm cùng tập), phân tầng theo loại câu, hạt giống `lexora-split-v1` |

Mỗi câu được gán nhãn: loại câu, kỳ vọng trả lời hay từ chối, tập đơn vị chứa căn cứ, ghi chú.
Đề xuất nhãn của model được lưu sẵn; người gán nhãn chọn một chế độ (xem đề xuất hoặc không) một lần và giữ nguyên, và hệ thống ghi lại trường nào được giữ, trường nào được sửa so với đề xuất.

Số liệu sau khi khóa: (chờ kết quả).

### 4.2.2. Bộ câu hỏi phức tạp v1

Bộ câu hỏi v1 chủ yếu là câu tra cứu: 101 trên 152 câu có đúng một đơn vị đáp án và chỉ 2 câu cần hai văn bản.
Vì vậy nó ít có khả năng cho thấy giá trị của đồ thị dẫn chiếu và của cấu trúc quy phạm, vốn nằm ở các câu cần nhiều quy định.
Bộ phức tạp v1 bổ sung loại câu này và được báo cáo riêng.

| Đặc điểm | Giá trị |
|---|---|
| Số câu | 30, đều loại tổng hợp, 6 câu diễn đạt lại |
| Nhóm | 10 câu liên văn bản (Bộ luật và Nghị định hoặc Thông tư hướng dẫn), 10 câu nhiều Điều trong một văn bản, 10 câu tình huống nhiều vấn đề |
| Đơn vị đáp án mỗi câu | 2 đến 4 |
| Nguồn câu | Model soạn nháp, hai người gán nhãn như bộ v1 (`question-set-complex-v1-guideline.md`) |
| Chỉ số thêm | Tỉ lệ câu tìm đủ mọi đơn vị đáp án trong K kết quả đầu |

Số liệu sau khi khóa: (chờ kết quả).

### 4.2.3. Gold set trích xuất v1

| Đặc điểm | Giá trị |
|---|---|
| Phạm vi | 40 Điều lấy mẫu có hạt giống (`lexora-gold-v1`) từ corpus đã khóa |
| Số câu | 290 |
| Nhãn | Các quy phạm của từng câu: tính quy phạm, từ tình thái, các ô; mỗi giá trị phải là đoạn nguyên văn của câu |
| Người gán nhãn | Hai thành viên, độc lập, rồi đối soát |

Model không tham gia gán nhãn gold, vì gold do model gán sẽ tạo vòng tròn khi dùng để chấm chính model.

### 4.2.4. Bảng kiểm tra quy phạm bị loại

104 quy phạm (80 bị loại, 24 được giữ) từ bốn model, che tên model và kết quả kiểm chứng, gán nhãn Sai, Đúng diễn đạt lại, Đúng mượn câu dẫn, Đúng nguyên văn hoặc Không rõ.
Bảng này đo độ chính xác thật của bộ kiểm chứng: trong số quy phạm bị loại, bao nhiêu thực sự sai.

### 4.2.5. Độ tin cậy của nhãn

| Bộ nhãn | Chỉ số đồng thuận | Kết quả |
|---|---|---|
| Bộ câu hỏi: loại câu, trả lời hay từ chối | Cohen's kappa | (chờ kết quả) |
| Bộ câu hỏi: tập đơn vị căn cứ | Dice trung bình; tỉ lệ khớp hoàn toàn | (chờ kết quả) |
| Gold set: từng ô | Kappa hoặc F1 giữa hai người | (chờ kết quả) |
| Gold set: quy phạm | F1 giữa hai người | (chờ kết quả) |
| Bảng kiểm tra quy phạm bị loại | Cohen's kappa | (chờ kết quả) |
| Chấm câu trả lời: người và giám khảo LLM | Cohen's kappa | (chờ kết quả) |

## 4.3. RQ1: Chất lượng trích xuất

### 4.3.1. Thiết lập

So sánh baseline theo quy tắc (`norm-rules-v2`) với LLM (ĐK3 và ĐK4 của lượt trích xuất chính) trên đúng các câu của gold set.
Quy tắc so khớp được cố định trước mọi lượt chạy:

- **Mức ô** (tương ứng thực thể): chặt là bằng nhau sau chuẩn hóa chữ hoa, khoảng trắng và dấu câu ở biên; lỏng là lồng nhau hoặc Jaccard token từ 0,5.
- **Mức quy phạm** (tương ứng quan hệ): khớp khi cùng tính quy phạm, hành vi khớp và chủ thể khớp; ghép tham lam theo độ tương đồng, mỗi quy phạm dùng một lần.

### 4.3.2. Kết quả

| Phương pháp | P ô (chặt) | R ô (chặt) | F1 ô (chặt) | F1 ô (lỏng) | F1 quy phạm |
|---|---|---|---|---|---|
| Quy tắc `norm-rules-v2` | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| LLM, ĐK3 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| LLM, ĐK4 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

| Nhóm ô | F1 quy tắc | F1 ĐK3 | F1 ĐK4 |
|---|---|---|---|
| Chủ thể, hành vi, đối tượng | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| Điều kiện, ngoại lệ, thời hạn, định lượng | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| Tính quy phạm | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

### 4.3.3. Kiểm lại lựa chọn model

Model trích xuất chính được chọn trước khi có gold, theo độ phủ câu và tỉ lệ lỗi gọi; lựa chọn này được kiểm lại bằng F1 trên gold cho các model đã chạy đủ.

| Model | F1 ô (chặt) | F1 quy phạm |
|---|---|---|
| gpt-oss-120b (chính) | (chờ kết quả) | (chờ kết quả) |
| gemma4:31b (lặp lại) | (chờ kết quả) | (chờ kết quả) |
| Claude Opus 5.5 (đối chứng) | (chờ kết quả) | (chờ kết quả) |

## 4.4. RQ2: Hiệu quả kiểm chứng

### 4.4.1. Thiết lập

- **Chèn lỗi có chủ đích** (`error-injection-v1`): 12 loại lỗi, 30 lỗi mỗi loại, hạt giống cố định, chèn vào quy phạm sạch của ĐK4; mỗi bản ghi được kiểm riêng.
- **Lỗi còn sót so với gold**: quy phạm của ĐK4 không khớp gold là lỗi bộ kiểm chứng không bắt được.
- **Độ chính xác của việc loại**: từ bảng kiểm tra quy phạm bị loại.

### 4.4.2. Kết quả

| Loại lỗi | Nhóm | Thiết kế để phát hiện | Tỉ lệ bị loại |
|---|---|---|---|
| Sai đơn vị, sai phiên bản | Kỹ thuật | Có | (chờ kết quả) |
| Sửa trích dẫn, đổi số | Kỹ thuật | Có | (chờ kết quả) |
| Chủ thể bịa, từ tình thái bịa hoặc đảo | Kỹ thuật | Có | (chờ kết quả) |
| Hành vi lấy từ câu khác | Kỹ thuật | Có | (chờ kết quả) |
| Bỏ phủ định, bỏ điều kiện, bỏ ngoại lệ | Ngữ nghĩa | Không | (chờ kết quả) |

| Chỉ số | ĐK3 | ĐK4 |
|---|---|---|
| Số quy phạm | (chờ kết quả) | (chờ kết quả) |
| Lỗi theo gold (tỉ lệ quy phạm không khớp gold) | (chờ kết quả) | (chờ kết quả) |
| Tỉ lệ lỗi còn sót sau kiểm chứng | - | (chờ kết quả) |

| Chỉ số từ bảng kiểm tra | Giá trị |
|---|---|
| Tỉ lệ quy phạm bị loại thực sự sai | (chờ kết quả) |
| Tỉ lệ bị loại nhưng đúng (diễn đạt lại hoặc mượn câu dẫn) | (chờ kết quả) |
| Tỉ lệ được giữ nhưng sai | (chờ kết quả) |

Ghi chú: tỉ lệ loại nhầm 0% trên bản ghi sạch của bộ chèn lỗi không phải bằng chứng về độ chính xác, vì bản ghi sạch lấy từ chính ĐK4.

## 4.5. RQ3: Truy xuất và chất lượng câu trả lời

### 4.5.1. Chỉ số

| Nhóm | Chỉ số | Cách tính |
|---|---|---|
| Truy xuất | Recall@1, 3, 5, 10 | Theo mã đơn vị gold |
| Truy xuất | Số token ngữ cảnh ở top-5 | Đếm theo cùng một bộ đếm cho mọi điều kiện |
| Tự động | Tỉ lệ từ chối đúng khi phải từ chối; tỉ lệ từ chối nhầm | So với kỳ vọng của câu hỏi |
| Tự động | Độ chính xác và độ phủ trích dẫn so với gold | Đơn vị được trích so với tập đơn vị gold |
| Tự động | Số phát biểu bị cổng trích dẫn loại | Phát biểu không có mã đoạn hợp lệ |
| Người chấm | Mức bám nguồn | Mỗi phát biểu: 2 đủ căn cứ, 1 một phần, 0 không |
| Người chấm | Trích dẫn đúng | Mỗi phát biểu: 1 nếu đoạn được trích chứa căn cứ |
| Người chấm | Độ đúng | Mỗi câu trả lời: 0, 1, 2 |
| Người chấm | Từ chối hợp lý | Mỗi câu trả lời bị từ chối: 1 hoặc 0 |

Bảng chấm che tên điều kiện, trộn các điều kiện và chỉ cho người chấm thấy nguyên văn đơn vị; giám khảo LLM chấm cùng bảng theo cùng rubric.

### 4.5.2. Kết quả truy xuất

| Điều kiện | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Token ngữ cảnh (top-5) |
|---|---|---|---|---|---|
| ĐK1 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK2 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK3 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK4 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

Kết quả được báo cáo riêng cho tập dev (dùng để chọn phương pháp truy xuất) và tập held-out.
Vì Recall@K có lợi cho bản ghi lớn (một đoạn 384 token của ĐK1 chứa nhiều khoản), kết quả được báo cáo thêm ở cùng ngân sách token: lấy bản ghi theo thứ hạng cho tới khi tổng số token mà model sinh phải đọc vượt 500, 1.000 hoặc 2.000 token.
Tương tự, độ chính xác trích dẫn được báo cáo theo ký tự: phần văn bản nguồn được trích nằm trong đơn vị đáp án chiếm bao nhiêu, thay vì chỉ hỏi bản ghi được trích có chứa đơn vị đáp án hay không.

Ghi chú: đã có một lượt chạy thử truy xuất trên nhãn do model đề xuất, chưa qua người duyệt, chỉ để kiểm tra công cụ; số liệu đó không dùng để báo cáo.

### 4.5.3. Kết quả câu trả lời

| Điều kiện | Độ đúng (TB) | Bám nguồn | Trích dẫn đúng | P trích dẫn (gold) | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|
| ĐK1 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK2 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK3 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK4 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

### 4.5.4. Kết quả theo loại câu hỏi

| Loại câu | ĐK1 | ĐK2 | ĐK3 | ĐK4 |
|---|---|---|---|---|
| Tra cứu | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| Tổng hợp | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| Hiệu lực | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| Ngoài phạm vi | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

### 4.5.5. Độ ổn định theo cách diễn đạt

Với mỗi nhóm diễn đạt lại, đo tỉ lệ các câu trong nhóm cho cùng kết quả (cùng trúng hoặc cùng trượt; cùng độ đúng): (chờ kết quả).

## 4.6. Kiểm định thống kê

Các so sánh chính là các cặp liền kề, đúng với câu hỏi mà mỗi bậc đặt ra: ĐK1 với ĐK2, ĐK2 với ĐK3, ĐK3 với ĐK4; thêm ĐK1 với ĐK4 cho giả thuyết tổng thể.

| Chỉ số | Kiểm định | Ghi chú |
|---|---|---|
| Trúng hay trượt ở Recall@5 theo từng câu | McNemar | Chỉ dùng các câu hai điều kiện khác nhau |
| Câu trả lời đúng hoàn toàn (độ đúng = 2) theo từng câu | McNemar | |
| Độ đúng trung bình, mức bám nguồn | Khoảng tin cậy 95% bootstrap ghép cặp | 10.000 lần lấy mẫu lại theo câu hỏi, hạt giống cố định |
| Chênh lệch Recall@K | Khoảng tin cậy 95% bootstrap ghép cặp | |

Vì có nhiều phép so sánh, kết luận chính chỉ dựa trên các cặp liền kề đã nêu trước; các so sánh khác được báo cáo như phân tích thăm dò **[mục còn mở: có hiệu chỉnh đa so sánh hay không]**.

| So sánh | Chênh lệch | KTC 95% | p (McNemar) |
|---|---|---|---|
| ĐK2 - ĐK1 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK3 - ĐK2 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK4 - ĐK3 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |
| ĐK4 - ĐK1 | (chờ kết quả) | (chờ kết quả) | (chờ kết quả) |

## 4.7. Phân tích lỗi

Khung phân loại lỗi, áp dụng cho các câu một điều kiện trả lời đúng mà điều kiện khác sai:

| Nhóm lỗi | Mô tả | Số lượng theo điều kiện |
|---|---|---|
| Truy xuất trượt | Đơn vị căn cứ không có trong top-5 | (chờ kết quả) |
| Thiếu ngữ cảnh | Tìm đúng đơn vị nhưng bản ghi thiếu câu dẫn hoặc điều kiện | (chờ kết quả) |
| Thiếu bao phủ | Đơn vị căn cứ không có bản ghi nào trong kho (chỉ ĐK3, ĐK4) | (chờ kết quả) |
| Trích xuất sai | Quy phạm sai tính quy phạm, thiếu điều kiện, sai chủ thể | (chờ kết quả) |
| Sinh sai | Có đủ căn cứ nhưng model diễn giải sai hoặc bỏ sót | (chờ kết quả) |
| Từ chối sai | Từ chối khi đủ căn cứ, hoặc trả lời khi phải từ chối | (chờ kết quả) |

Phần này kèm các ví dụ cụ thể, mỗi ví dụ có câu hỏi, đơn vị căn cứ, bản ghi được tìm thấy ở từng điều kiện và câu trả lời.

## 4.8. Các mối đe dọa tới tính hợp lệ

### 4.8.1. Tính hợp lệ nội tại

- **Kích thước bản ghi khác nhau giữa các điều kiện**: đoạn ĐK1 lớn hơn nhiều so với bản ghi ĐK2-ĐK4 nên phủ nhiều đơn vị hơn; Recall@K vì vậy không so sánh trực tiếp được nếu không xét số token ngữ cảnh.
- **Cách biểu diễn ĐK3 và ĐK4**: thiết kế đầu tiên chỉ chứa các ô của quy phạm, làm mất các từ cần để khớp câu hỏi (tên Điều, câu dẫn) và mất các câu không có quy phạm (khoảng một phần ba đơn vị đáp án); khác biệt ĐK2-ĐK3 khi đó phản ánh việc mất nội dung. Thiết kế chính giữ nguyên văn của ĐK2 và chỉ cộng thêm quy phạm; thiết kế cũ được báo cáo như một biến thể.
- **Điều kiện "láng giềng phải khớp câu hỏi"** của đồ thị được chọn sau khi xem kết quả chạy thử trên tập dev với nhãn do model đề xuất; nó được cố định trước khi có nhãn của người và trước khi chạy held-out.
- **Bộ kiểm chứng được điều chỉnh trên chính phạm vi thực nghiệm**: v1 và v2 quá chặt, v3 là kết quả điều chỉnh sau khi xem đầu ra của pilot, trước mọi phép đo RQ2 và RQ3; việc này được ghi trong nhật ký quyết định.
- **Một lượt trích xuất, một model**: ĐK3 và ĐK4 phụ thuộc vào một lượt chạy của một model; độ lặp lại được kiểm tra một phần bằng các model khác đã chạy cùng cấu hình.

### 4.8.2. Tính hợp lệ của phép đo

- **Câu hỏi do model soạn nháp**: câu có thể dùng từ ngữ gần với văn bản luật hơn câu hỏi của người dùng thật, làm lợi cho truy xuất từ khóa; báo cáo nêu rõ nguồn của toàn bộ câu.
- **Neo theo đề xuất của model**: người gán nhãn xem đề xuất có thể bị ảnh hưởng; hệ thống ghi chế độ gán nhãn của từng người và các trường được giữ nguyên so với đề xuất.
- **Người gán nhãn là thành viên nhóm**: hai thành viên đồng thời là tác giả hệ thống; giảm thiểu bằng bảng chấm che tên điều kiện, gán nhãn độc lập và đo đồng thuận, nhưng không loại bỏ hoàn toàn.
- **Không có chuyên gia pháp lý xác nhận**: kappa chỉ phản ánh độ nhất quán giữa hai người theo hướng dẫn.
- **Giám khảo LLM**: chỉ là công cụ bổ sung; kết luận dựa trên điểm của người chấm.
- **Bộ đếm token**: ngân sách ngữ cảnh đếm theo âm tiết, có thể lệch so với tokenizer thật của model sinh.

### 4.8.3. Tính hợp lệ của kết luận

- **Cỡ mẫu nhỏ**: khoảng 150 câu, trong đó khoảng 30% là held-out; khác biệt nhỏ có thể không có ý nghĩa thống kê, nên kết quả được báo cáo kèm khoảng tin cậy.
- **Mô hình không đặt được hạt giống**: một số model không cho đặt seed; tái lập bằng đầu ra đã lưu thay vì chạy lại.

### 4.8.4. Tính hợp lệ bên ngoài

- **Phạm vi hẹp**: 5 văn bản, 94 Điều của pháp luật lao động; kết quả chưa chắc khái quát được cho lĩnh vực khác hay toàn bộ hệ thống pháp luật.
- **Không kiểm hiệu lực theo thời gian và mâu thuẫn giữa văn bản**: bộ kiểm chứng không xử lý các lỗi này.

## 4.9. Các mục còn mở

| Mục | Nội dung cần chốt | Thời điểm phải chốt |
|---|---|---|
| Cách biểu diễn ĐK3 và ĐK4 | Đề xuất 09/11: bản ghi ĐK2 cộng quy phạm, đồ thị dẫn chiếu hai chiều có kiểm câu hỏi; chờ giảng viên duyệt | Trước khi khóa bộ câu hỏi và chạy thật |
| Model sinh câu trả lời | Một model cố định cho cả bốn điều kiện | Trước lượt chạy câu trả lời trên tập dev |
| Giám khảo LLM | Model khác model sinh | Cùng lúc với model sinh |
| Phương pháp truy xuất | BM25, BGE-M3 hay kết hợp | Sau khi chạy trên tập dev, trước held-out |
| Báo cáo Recall ở cùng ngân sách token | Đã thêm (500, 1.000, 2.000 token) cùng độ chính xác trích dẫn theo ký tự | Đã chốt 09/11 |
| Bộ đếm token | Thay âm tiết bằng tokenizer của model sinh | Trước lượt chạy câu trả lời |
| Hiệu chỉnh đa so sánh | Có áp dụng hay không | Trước khi xem kết quả held-out |

## Tóm tắt chương

(Viết sau khi có kết quả.)
