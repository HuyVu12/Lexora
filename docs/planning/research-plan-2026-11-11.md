# Kế hoạch nghiên cứu từ 11/11 đến 20/12/2026

Trạng thái: đang thực hiện; chờ giảng viên duyệt.
Ngày lập: 11/11/2026.
Khi viết, tài liệu này chỉ là kế hoạch; không có mã, lượt chạy hay lượt gọi model nào được thực hiện lúc đó.
Cập nhật 11/11/2026: người dùng trả lời câu 12.1-12.4 (ghi ở `docs/decisions.md`); phần code offline của WP2-WP5 đã cài và WP2, WP3 đã chạy trên bộ chạy thử, xem `docs/results/budget-curves-2026-11-11.md`.
Chưa có lượt gọi model hay tải mạng nào cho kế hoạch này.
Nếu được duyệt, nó thay cho mục 11 "Hướng tiếp theo" của `docs/planning/graph-legal-reasoning-2026-11-10.md`.

Căn cứ:

- Đề cương: `docs/De_cuong_DATN_Legal_AI.docx.pdf`.
- Giao thức thực nghiệm: `docs/evaluation-protocol.md`.
- Kết quả chạy thử: `docs/results/dk-comparison-2026-11-10.md`, `docs/planning/graph-legal-reasoning-2026-11-10.md`.
- Khung chương 4: `docs/thesis/chuong-4-thuc-nghiem-va-danh-gia.md`.
- Nhật ký quyết định: `docs/decisions.md`.
- Số liệu truy xuất trong tài liệu này đọc trực tiếp từ `metrics.json` của các lượt trong `experiments/runs/dryrun-*`.

## 1. Tóm tắt

Kết quả chạy thử cho thấy ba điều.
Thứ nhất, ĐK2 trích dẫn chính xác hơn ĐK1 rõ rệt, nhưng ĐK1 phủ nhiều căn cứ hơn ở câu hỏi khó khi ngân sách ngữ cảnh từ 2.000 token.
Thứ hai, ĐK3 gần như trùng ĐK2 và ĐK4 gần như trùng ĐK3 ở tầng câu trả lời, vì model sinh đọc nguyên văn và bỏ qua dòng quy phạm.
Thứ ba, mọi con số hiện có đều dùng nhãn do model soạn và giám khảo là model, nên chưa báo cáo được.

Kế hoạch gồm năm việc chính, theo thứ tự ưu tiên:

1. Có nhãn người cho bộ câu hỏi, gold trích xuất và một mẫu câu trả lời (bắt buộc theo đề cương).
2. Báo cáo lại số liệu đã có theo đúng điều đề tài tuyên bố: truy vết và hiệu quả token.
3. Xóa lợi thế độ phủ của ĐK1 bằng cách đóng gói ngữ cảnh theo Điều cho ĐK2-ĐK4.
4. Đo việc ĐK1 không làm được về bản chất: hiệu lực và sửa đổi ở mức Khoản, Điểm.
5. Cho kho quy phạm ĐK3/ĐK4 một nhiệm vụ mà ĐK2 không làm được: truy vấn theo trường của quy phạm, nơi kiểm chứng có tác dụng đo được.

Hai việc phụ: chuyển kết quả chính sang model mã nguồn mở đúng đề cương, và một thí nghiệm nhỏ ngoài luật lao động để tên đề tài "hỏi đáp pháp luật" có căn cứ.

Nhánh "đồ thị quan hệ + LLM chọn láng giềng" dừng ở các lượt đã chạy và được báo cáo là thăm dò, không chạy thêm (cần người dùng quyết, xem mục 12).

## 2. Hiện trạng số liệu

### 2.1. Truy xuất hybrid ở cùng ngân sách token

Tỉ lệ đơn vị đáp án nằm trong ngữ cảnh, ĐK1 / ĐK2, nhãn do model soạn.

| Bộ câu hỏi | 500 token | 1.000 token | 2.000 token |
|---|---|---|---|
| Đơn giản (131 câu có nhãn, corpus v2) | 0,56 / 0,82 | 0,74 / 0,88 | 0,85 / 0,92 |
| Phức tạp (30 câu, corpus v1) | 0,40 / 0,48 | 0,64 / 0,64 | 0,80 / 0,78 |
| Xung đột (25 câu) | 0,19 / 0,21 | 0,29 / 0,35 | 0,47 / 0,43 |
| Tình huống (44 câu) | 0,12 / 0,16 | 0,25 / 0,25 | 0,42 / 0,33 |

ĐK3 và ĐK4 không đồ thị ngang hoặc hơi kém ĐK2 ở cùng ngân sách, vì bản ghi dài hơn (56 so với 45 token).

### 2.2. Câu trả lời trên bộ tình huống (Haiku, 3.000 token, giám khảo Sonnet)

| Chỉ số | ĐK1 | ĐK2 | ĐK3 không đồ thị |
|---|---|---|---|
| Trích trúng đơn vị đáp án | 0,485 | 0,417 | 0,401 |
| Vấn đề giải quyết được | 0,522 | 0,477 | 0,482 |
| Trích dẫn chính xác theo ký tự | 0,092 | 0,244 | 0,238 |
| Khớp kết luận chuẩn | 0,352 | 0,398 | 0,398 |
| Độ đúng | 0,386 | 0,420 | 0,398 |

Mức nhiễu của việc sinh lại và của giám khảo khoảng ±0,07 với 25-44 câu.

### 2.3. Khoảng cách so với đề cương cần đóng

| Yêu cầu của đề cương | Hiện trạng | Gói việc xử lý |
|---|---|---|
| Bộ câu hỏi khóa trước khi tinh chỉnh, 30% held-out | Câu hỏi và nhãn do model soạn, chưa duyệt, chưa khóa | WP1 |
| Gold trích xuất 40-60 điều khoản, hai người, kappa | Công cụ có, nhãn chưa có | WP1 |
| Answer correctness do người chấm theo rubric trên mẫu | Chỉ có giám khảo Sonnet | WP1 |
| Hiệu lực là thuộc tính của KB | `legal_status` là `unknown` cho cả 9 văn bản | WP4 |
| Model và embedding mã nguồn mở | Trích xuất và embedding đúng; sinh câu trả lời, giám khảo, đồ thị dùng Claude | WP6 |
| Phạm vi 8-12 văn bản, 60-100 điều khoản | Corpus v2: 9 văn bản, 711 Điều | Ghi vào bảng điều chỉnh (WP10) |
| Chương 2 khảo sát nghiên cứu liên quan | Mục 2.11 còn để trống trích dẫn | WP8 |

## 3. Luận điểm sẽ bảo vệ

Luận điểm tổng: trong hỏi đáp pháp luật, cách tổ chức tri thức quyết định khả năng truy vết và khả năng làm những việc phụ thuộc cấu trúc, chứ chưa chắc quyết định độ đúng của câu trả lời khi model sinh đã đủ mạnh.

Bốn luận điểm con, mỗi luận điểm gắn với một bậc của thiết kế đối chứng:

1. Cấu trúc văn bản (ĐK2 so với ĐK1) cho trích dẫn chính xác hơn và cùng độ phủ với ít token hơn.
2. Cấu trúc văn bản cho phép xử lý hiệu lực và sửa đổi ở mức Khoản, Điểm; đoạn cắt cố định không làm được.
3. Kho quy phạm (ĐK3) không cải thiện câu hỏi tra cứu thông thường, nhưng trả lời được câu hỏi liệt kê theo chủ thể, tính quy phạm, thời hạn mà truy xuất theo đoạn không gom đủ.
4. Kiểm chứng (ĐK4) có giá trị ở tầng kho tri thức, và chỉ lan tới câu trả lời khi câu trả lời thật sự dựa vào quy phạm.

Mỗi luận điểm có thể bị bác bởi dữ liệu.
Kết quả âm được báo cáo như đề cương đã cam kết.

## 4. Giả thuyết khai báo trước

Các giả thuyết dưới đây được chốt trước khi có nhãn người và trước khi chạy held-out.
Chỉ số chính của mỗi giả thuyết là chỉ số duy nhất dùng để kết luận; các chỉ số khác là phân tích bổ sung.

| Mã | Giả thuyết | So sánh | Chỉ số chính | Bộ câu hỏi |
|---|---|---|---|---|
| H1 | Cấu trúc tăng độ chính xác trích dẫn | ĐK2 so với ĐK1 | Độ chính xác trích dẫn theo ký tự | Bộ khó, bộ tra cứu |
| H2 | Đóng gói theo Điều làm ĐK2 không kém ĐK1 về độ phủ | ĐK2 so với ĐK1 | Recall ở 3.000 token, biên không kém 0,05 | Bộ khó |
| H3 | Hiệu lực mức đơn vị giảm trích dẫn quy định lỗi thời | ĐK2 so với ĐK1 và ĐK1-hl | Tỉ lệ câu trả lời trích dẫn đơn vị lỗi thời | Bộ hiệu lực |
| H4 | Truy vấn quy phạm gom đủ căn cứ hơn cho câu liệt kê | ĐK3-q so với ĐK2 | F1 tập đơn vị được trích dẫn so với gold | Bộ liệt kê |
| H5 | Kiểm chứng chặn lỗi trích xuất lan sang câu trả lời | ĐK4-q so với ĐK3-q | Tỉ lệ câu trả lời lặp lại lỗi cài | Bộ liệt kê, KB cài lỗi |
| H0a | Giữ nguyên từ đề cương | ĐK3 so với ĐK2 | Độ đúng, bám nguồn | Bộ khó, bộ tra cứu |
| H0b | Giữ nguyên từ đề cương | ĐK4 so với ĐK3 | Độ đúng, bám nguồn | Bộ khó, bộ tra cứu |

Dự đoán ghi trước: H1 đạt; H2, H3, H4, H5 chưa biết; H0a và H0b không có khác biệt.

## 5. Nguyên tắc phương pháp

1. Mọi lựa chọn thiết kế (biến thể đóng gói, tham số, prompt) được chọn trên tập dev rồi khóa; held-out chạy đúng một lần.
2. Không chọn biến thể theo độ chênh giữa các điều kiện; chỉ chọn theo chỉ số của một điều kiện đã nêu trước (ví dụ recall của ĐK2).
3. Không làm yếu ĐK1: giữ 384 token gối 64, và báo cáo thêm độ nhạy theo cỡ đoạn.
4. Mọi điều kiện dùng chung corpus, bộ câu hỏi, lượt tách vấn đề, cấu hình truy xuất, model sinh, prompt, ngân sách token; `preflight` phải đạt trước khi báo cáo.
5. Kết luận dựa trên nhãn người và chỉ số tất định; giám khảo LLM chỉ bổ sung và phải có độ đồng thuận với người.
6. Mỗi câu ở bộ khó được sinh hai lần để đo riêng nhiễu sinh; mức nhiễu được báo cáo cạnh mọi chênh lệch.
7. Bốn so sánh chính (ĐK1-ĐK2, ĐK2-ĐK3, ĐK3-ĐK4, ĐK1-ĐK4) dùng bootstrap ghép cặp 10.000 lần, hạt giống cố định, và hiệu chỉnh Holm; mọi so sánh khác ghi là thăm dò.
8. Mọi điều chỉnh sau khi khóa đều ghi lý do vào `docs/decisions.md`.
9. Dừng thêm biến thể từ 25/11/2026 (quy tắc đã có).
10. Mọi lượt gọi mạng hoặc model cần người dùng duyệt endpoint, model, dữ liệu và phạm vi theo `AGENTS.md`.

## 6. Tên các điều kiện

| Tên | Định nghĩa | Vai trò |
|---|---|---|
| ĐK1 | Đoạn 384 token, gối 64 | Chính |
| ĐK2 | Đơn vị lá kèm đường dẫn, tên Điều, câu dẫn | Chính |
| ĐK3 | Bản ghi ĐK2 cộng dòng quy phạm gọn, đồ thị dẫn chiếu hai chiều | Chính |
| ĐK4 | ĐK3 chỉ giữ quy phạm qua `kb-validator-v3` | Chính |
| ĐK1-hl | ĐK1 có lọc hiệu lực ở mức văn bản | Đối chứng phụ cho H3 |
| ĐK3-q | Truy vấn theo trường quy phạm, ngữ cảnh là dòng quy phạm kèm trích dẫn nguyên văn | Mở rộng khai báo trước cho H4 |
| ĐK4-q | ĐK3-q trên kho đã kiểm chứng | Mở rộng khai báo trước cho H5 |
| Biến thể đã có | chỉ quy phạm, không đồ thị, đồ thị một chiều, cùng Điều, quan hệ Sonnet, chain, chọn láng giềng | Đóng băng, báo cáo từ lượt đã chạy |

## 7. Các gói việc

Phân công dưới đây là đề xuất theo phân công của đề cương (Kha: RQ1, RQ2; Vũ: RQ3) và cần nhóm xác nhận.
Số giờ là ước tính của người lập kế hoạch, chưa đo.

### WP0. Chốt hướng và đóng băng biến thể (11-12/11)

Mục tiêu: có quyết định bằng văn bản trước khi làm tiếp.

Việc cần làm:

1. Nhóm trả lời các câu hỏi ở mục 12.
2. Gửi giảng viên một trang tóm tắt (nội dung ở mục 10.4) và xin ý kiến về: corpus v2, thiết kế ĐK3/ĐK4, hai điều kiện mở rộng, model.
3. Ghi quyết định vào `docs/decisions.md`: danh sách điều kiện ở mục 6, giả thuyết ở mục 4, quy tắc dừng.
4. Đánh dấu các cấu hình trong `configs/experiments/ablations` và các biến thể `corpus-v2/dk*-{chain,concept,sibling,relation*}` là đóng băng.

Đầu ra: một mục nhật ký quyết định; phản hồi của giảng viên được lưu.
Người phụ trách: cả hai.

### WP1. Nhãn người (12/11 đến 25/11, làm song song mỗi ngày)

Mục tiêu: mọi số liệu báo cáo đều dựa trên nhãn do hai người gán độc lập rồi đối soát.

Hai thành viên không có nền luật, nên mọi nhãn được thiết kế thành việc đối chiếu chữ: đơn vị này có chứa căn cứ của câu hỏi không, câu này có đặt nghĩa vụ cho chủ thể X không.
Kết luận pháp lý lấy từ nguồn ngoài (kết quả xét xử của bản án, nguyên văn văn bản), không lấy từ nhận định của nhóm.

| Thứ tự | Bộ nhãn | Quy mô | Công cụ | Ước tính mỗi người |
|---|---|---|---|---|
| 1 | Bộ khó: tình huống 44, xung đột 25, phức tạp 30 | 99 câu | Trang Nghiên cứu > Bộ câu hỏi, chế độ đề xuất chọn một lần | 13 giờ |
| 2 | Gold trích xuất v1 | 40 Điều, 290 câu | Trang Nghiên cứu > Gold | 15 giờ |
| 3 | Bộ tra cứu v1 | 152 câu | Như dòng 1 | 5 giờ |
| 4 | Bộ hiệu lực v1 (mới, WP4) | khoảng 30 câu | Như dòng 1, kèm tệp phụ | 3 giờ |
| 5 | Bảng kiểm tra quy phạm bị loại | 104 dòng | `kb-audit-sheet`, `kb-audit-score` | 2 giờ |
| 6 | Bộ liệt kê v1 (mới, WP5) | khoảng 40 câu | Suy ra từ gold dòng 2, kiểm lại | 3 giờ |
| 7 | Chấm câu trả lời (sau lượt chạy chính) | 160 câu trả lời | `answer-sheet`, `answer-grades` | 8 giờ |

Việc cần làm:

1. Nhập các bộ nháp (`experiments/question-drafts-*`) vào store dùng chung trên máy chủ gán nhãn, gắn với phiên bản corpus đã khóa.
2. Rà lại hướng dẫn gán nhãn (`docs/guides/huong-dan-gan-nhan.md`, `huong-dan-gan-nhan-gold.md`, các guideline theo bộ) cho khớp corpus v2; bổ sung quy tắc cho câu tình huống: đánh dấu mọi đơn vị mà kết quả xét xử dựa vào.
3. Gán nhãn thử 10 câu mỗi bộ, đo kappa và Dice, sửa hướng dẫn một lần, rồi gán phần còn lại; không sửa hướng dẫn sau đó.
4. Đối soát trong trang So sánh, ghi lý do bất đồng, khóa bộ câu hỏi với chia dev/held-out theo nhóm diễn đạt lại, phân tầng theo loại câu, hạt giống `lexora-split-v1`.
5. Nhãn của bộ tra cứu v1 được soạn trên corpus v1; khi gán trên corpus v2 phải tìm thêm đơn vị chỉ có ở v2 (chế tài trong NĐ 12/2022 và các luật mới).
6. Chấm câu trả lời: mẫu phân tầng 40 câu hỏi nhân 4 điều kiện chính, bảng che tên điều kiện, hai người chấm độc lập; rubric gồm bám nguồn theo phát biểu, trích dẫn đúng, độ đúng 0-1-2 so với kết luận chuẩn.
7. Tính đồng thuận người với người và người với giám khảo Sonnet trên cùng mẫu.

Chỉ số độ tin cậy cần báo cáo: Cohen's kappa cho loại câu và trả lời hay từ chối; Dice và tỉ lệ khớp hoàn toàn cho tập đơn vị; F1 giữa hai người cho ô và quy phạm của gold; kappa cho bảng kiểm tra và cho điểm chấm câu trả lời.

Tiêu chí hoàn thành: bộ khó và gold khóa trước 23/11; bộ tra cứu khóa trước 25/11.
Phương án lùi: nếu chậm, giảm gold xuống 30 Điều và bộ tra cứu xuống mẫu phân tầng 80 câu, ghi lý do.
Người phụ trách: cả hai; Kha chủ trì gold và bảng kiểm tra, Vũ chủ trì bộ câu hỏi và chấm câu trả lời.

### WP2. Báo cáo lại số liệu đã có và độ nhạy của ĐK1 (12-14/11, offline)

Mục tiêu: đo đúng điều đề tài tuyên bố, không cần lượt gọi model.

Việc cần làm:

1. Mở rộng danh sách ngân sách token trong `retrieval_run.score_top` từ 500, 1.000, 2.000 lên 250, 500, 1.000, 1.500, 2.000, 3.000, 4.000, 6.000; chạy lại truy xuất của ĐK1-ĐK4 trên bốn bộ chạy thử.
2. Thêm chỉ số "ngân sách cần để đạt": số token nhỏ nhất để recall trung bình đạt một ngưỡng nêu trước (0,8 cho bộ tra cứu, 0,4 cho bộ khó).
3. Thêm hai chỉ số tải kiểm chứng vào `answer_run.score`, tính từ `answers.jsonl` và `records.jsonl` đã lưu:
   - số token của các bản ghi được trích dẫn chia cho số phát biểu;
   - tỉ lệ trích dẫn trỏ tới bản ghi chỉ ánh xạ về một đơn vị lá.
4. Độ nhạy cỡ đoạn của ĐK1: thêm cấu hình 128, 256, 512 token (gối 1/6 cỡ đoạn) trong `configs/experiments/ablations`, chạy truy xuất trên tập dev; chỉ đo truy xuất, không sinh câu trả lời.
5. Viết test đơn vị cho các chỉ số mới.

Đầu ra: `docs/results/budget-curves-<ngày>.md` với bảng và hình đường cong recall theo ngân sách cho từng bộ.
Tiêu chí hoàn thành: số liệu khớp các giá trị 500, 1.000, 2.000 đã có.
Chi phí: CPU cho BGE-M3 trên các đoạn mới; không cần duyệt.
Người phụ trách: Vũ.

### WP3. Đóng gói ngữ cảnh theo Điều cho ĐK2-ĐK4 (12-16/11, offline)

Mục tiêu: lấy độ phủ của đoạn liền mạch mà vẫn giữ trích dẫn tới Khoản, Điểm (H2).

Thiết kế `pack-article-v1`:

- Truy xuất và xếp hạng giữ nguyên theo đơn vị lá.
- Khi đóng gói, các bản ghi được gom theo cặp văn bản và Điều, theo thứ tự xuất hiện đầu tiên trong bảng xếp hạng; trong một Điều, các đơn vị in theo thứ tự văn bản.
- Tên văn bản, tên Điều và câu dẫn in một lần cho mỗi khối.
- Mỗi đơn vị lá vẫn giữ mã đoạn riêng (E01, E02...) để trích dẫn tới Khoản, Điểm.
- Ngân sách token tính trên toàn bộ phần model đọc, như mọi điều kiện.

Ba biến thể, chốt trước:

| Biến thể | Nội dung |
|---|---|
| P0 | Danh sách phẳng như hiện tại |
| P1 | Chỉ gom và in tiêu đề, câu dẫn một lần; không thêm đơn vị |
| P2 | P1, cộng thêm các Khoản, Điểm anh em chưa được xếp hạng của 3 Điều đứng đầu, theo thứ tự văn bản, mỗi khối không quá 400 token |

Việc cần làm:

1. Thêm tùy chọn `context_packing` vào cấu hình dùng chung; cài trong `answer_run.pack` và phần chấm theo ngân sách của `retrieval_run` để hai nơi dùng cùng một hàm.
2. `preflight`: thêm kiểm tra ĐK2, ĐK3, ĐK4 dùng cùng `context_packing`.
3. Chạy P0, P1, P2 cho ĐK2 trên tập dev của bộ khó.
4. Quy tắc chọn: lấy biến thể có recall ở 3.000 token của ĐK2 cao nhất; nếu không biến thể nào hơn P0 ít nhất 0,03 thì giữ P0 và báo cáo kết quả âm.
5. Áp biến thể đã chọn cho ĐK3 và ĐK4 mà không chọn lại.
6. Test đơn vị: thứ tự khối, mã đoạn không đổi, không vượt ngân sách, không lặp đơn vị.

Khác với biến thể "cùng Điều" đã thử ngày 09/11 (không giúp): biến thể đó thay kết quả xếp hạng bằng láng giềng ở K cố định và bắt láng giềng khớp câu hỏi; `pack-article-v1` không đổi xếp hạng, chỉ đổi cách dùng ngân sách.

Chỉ số: recall theo ngân sách, tỉ lệ câu tìm đủ, độ chính xác trích dẫn theo ký tự (đo ở lượt chính).
Rủi ro: P2 kéo vào Khoản không liên quan và đẩy mất đơn vị đúng; quy tắc chọn ở bước 4 xử lý trường hợp này.
Chi phí: offline.
Người phụ trách: Vũ.

### WP4. Hiệu lực và sửa đổi ở mức đơn vị (13-21/11)

Mục tiêu: đáp ứng yêu cầu "hiệu lực là thuộc tính" của đề cương và kiểm tra H3.

#### 4.1. Dữ liệu

1. Điền `effective_from`, `effective_to` và tình trạng hiệu lực từ metadata vbpl.vn đã lưu trong `document.json` (`ingestion/vbpl_api.py` đã đọc `effFrom`, `effTo`, `effStatus`) vào bản ghi văn bản của corpus; ghi rõ đây là tình trạng vbpl.vn báo tại ngày truy cập, không phải xác nhận của nhóm.
2. Xác định văn bản thay thế NĐ 12/2022/NĐ-CP (hết hiệu lực 10/09/2026) trên vbpl.vn và tải về bằng `cli vbpl-fetch`; cần người dùng duyệt từng văn bản.
3. Đưa cặp NĐ 152/2020 và NĐ 70/2023 (đã tải trong corpus "Lao động v1" làm văn bản cũ) cùng NĐ 219/2025 vào phạm vi; quan hệ giữa chúng lấy từ metadata và nguyên văn, chưa xác minh khi lập kế hoạch.
4. Xem lại 3 Điều chứa đoạn sửa đổi văn bản khác đang bị bỏ khỏi corpus v2: đây là nguồn của các sửa đổi mức đơn vị đang có hiệu lực.
5. Khóa corpus "Phạm vi thực nghiệm v3": giữ nguyên mã và nguyên văn mọi đơn vị của v2 để nhãn dùng lại được, như v2 đã làm với v1.

#### 4.2. Cạnh sửa đổi bằng quy tắc

Module mới `kb/amendments.py` (`amendment-rules-v1`):

- Nhận diện câu lệnh sửa đổi: "Sửa đổi, bổ sung khoản X Điều Y như sau", "Bãi bỏ ...", "Thay thế cụm từ ...", "Bổ sung Điều ... vào sau Điều ...".
- Giải đích bằng bộ dẫn chiếu sẵn có (`kb/references.py`, bí danh trong `configs/knowledge-graph.json`).
- Mỗi cạnh ghi: đơn vị sửa, đơn vị bị sửa, loại (sửa đổi, bổ sung, bãi bỏ, thay thế), ngày hiệu lực, trích dẫn nguyên văn câu lệnh.
- Đích không giải được ghi là chưa giải quyết, không suy đoán.
- Không dùng model.

Kiểm tra: hai người đối chiếu toàn bộ cạnh sinh ra với nguyên văn (số lượng dự kiến nhỏ); báo cáo số cạnh đúng, sai, chưa giải quyết.

#### 4.3. Trạng thái đơn vị tại một ngày

Hàm tất định `unit_status(unit, as_of)` trả một trong: còn hiệu lực, chưa có hiệu lực, hết hiệu lực (theo văn bản), đã bị sửa đổi hoặc bãi bỏ (theo cạnh), không rõ.

#### 4.4. Dùng trong truy xuất (ĐK2-ĐK4)

- Đơn vị hết hiệu lực tại ngày của câu hỏi bị loại khỏi ngữ cảnh.
- Đơn vị đã bị sửa đổi được thay bằng đơn vị sửa đổi, kèm một dòng ghi chú trạng thái.
- Câu hỏi không ghi ngày dùng ngày khóa corpus v3.
- ĐK1-hl: lọc ở mức văn bản cho đoạn 384 token; đây là đối chứng để tách phần lợi ích chỉ có ở mức đơn vị.

#### 4.5. Bộ hiệu lực v1

Khoảng 30 câu, soạn nháp bằng model rồi hai người duyệt:

| Nhóm | Số câu | Nội dung |
|---|---|---|
| Văn bản hết hiệu lực | 10 | Câu về chế tài có căn cứ ở cả NĐ 12/2022 và văn bản thay thế |
| Sửa đổi mức đơn vị | 10 | Câu có căn cứ ở Khoản đã bị sửa và Khoản sửa |
| Theo thời điểm trong quá khứ | 5 | Câu ghi rõ ngày xảy ra việc; theo đề cương, hệ thống được phép nêu giới hạn thay vì suy đoán |
| Đối chứng | 5 | Câu không liên quan tới thay đổi hiệu lực |

Mỗi câu có: ngày áp dụng, tập đơn vị đáp án tại ngày đó, tập đơn vị lỗi thời.
Hai tập này suy ra từ metadata và cạnh sửa đổi, người gán nhãn chỉ đối chiếu chữ.
Lưu ở `experiments/question-drafts-validity-v1/` theo cách của các bộ nháp khác.

#### 4.6. Chỉ số

| Chỉ số | Cách tính | Loại |
|---|---|---|
| Tỉ lệ câu trả lời trích dẫn đơn vị lỗi thời | Trích dẫn giao với tập lỗi thời khác rỗng | Tất định, chỉ số chính của H3 |
| Tỉ lệ ngữ cảnh chứa đơn vị lỗi thời | Từ lượt truy xuất | Tất định |
| Recall đơn vị đúng phiên bản | Từ lượt truy xuất | Tất định |
| Câu trả lời có nêu tình trạng hiệu lực khi cần | Giám khảo, kiểm lại bằng người trên toàn bộ 30 câu | Bổ sung |

Việc cần duyệt: tải văn bản thay thế NĐ 12/2022 (một văn bản); các lượt soạn nháp câu hỏi.
Rủi ro: số sửa đổi mức đơn vị trong corpus quá ít để có 10 câu; khi đó giảm nhóm này và ghi rõ.
Người phụ trách: Kha (dữ liệu, cạnh sửa đổi, trạng thái), Vũ (truy xuất, bộ câu hỏi, chỉ số).

### WP5. Truy vấn theo trường của quy phạm: ĐK3-q và ĐK4-q (16-24/11)

Mục tiêu: kiểm tra H4 và H5 ở loại câu hỏi mà kho quy phạm sinh ra để trả lời.
Thiết kế này gần với chữ của đề cương hơn thiết kế ĐK3 hiện tại: nguồn tri thức cho RAG là chính kho quy phạm.

#### 5.1. Bộ liệt kê v1

Khoảng 40 câu yêu cầu gom nhiều quy định theo một tiêu chí:

| Nhóm | Ví dụ | Trường dùng để lọc |
|---|---|---|
| Nghĩa vụ của một chủ thể | Người sử dụng lao động có những nghĩa vụ gì khi thử việc? | tính quy phạm, `actor` |
| Hành vi bị cấm | Những hành vi nào bị cấm khi giao kết hợp đồng? | tính quy phạm |
| Quyền của một chủ thể | Người lao động có những quyền gì khi bị chấm dứt hợp đồng trái luật? | tính quy phạm, `actor`, `beneficiary` |
| Thời hạn | Các thời hạn tính bằng ngày trong xử lý kỷ luật lao động | `deadlines` |
| Định lượng | Các mức, tỉ lệ liên quan tới tiền lương làm thêm giờ | `quantities` |

Gold không phụ thuộc model: suy ra từ gold trích xuất v1 do người gán (40 Điều, 290 câu, có tính quy phạm và các ô).
Đơn vị đáp án của một câu hỏi là các đơn vị có quy phạm gold thỏa tiêu chí trong phạm vi chủ đề của câu.
Hai người kiểm lại từng tập đáp án bằng đối chiếu chữ.
Vì gold chỉ phủ 40 Điều, precision chỉ tính trên các đơn vị đã có nhãn (đơn vị ngoài 40 Điều bị bỏ qua khi chấm); giới hạn này được nêu trong báo cáo.
Thí nghiệm chạy trên corpus v1 (94 Điều), nơi đã có kho quy phạm của sáu model, nên không cần lượt trích xuất mới.

#### 5.2. Thiết kế ĐK3-q và ĐK4-q

1. Phân tích câu hỏi (`query-slots-v1`, một lượt gọi model mỗi câu, dùng chung): trả tính quy phạm cần tìm, cụm chủ thể, trường bắt buộc có (thời hạn, định lượng), và câu tìm kiếm theo chủ đề.
   ĐK1 và ĐK2 dùng câu tìm kiếm theo chủ đề của cùng lượt này.
2. Lọc: giữ các quy phạm khớp tính quy phạm, có trường bắt buộc, và chủ thể khớp theo so khớp chuỗi bỏ dấu với một bảng bí danh cố định (`configs/experiments/actor-aliases.json`, chốt trước khi chạy).
3. Xếp hạng: điểm hybrid của câu tìm kiếm theo chủ đề trên nguyên văn đơn vị chứa quy phạm.
4. Ngữ cảnh: mỗi quy phạm một dòng cấu trúc kèm trích dẫn nguyên văn của ô hành vi, gom theo Điều; không in toàn văn đơn vị.
   Mã đoạn vẫn trỏ về đơn vị lá để cổng trích dẫn hoạt động như cũ.
5. ĐK4-q dùng cùng thiết kế trên tập quy phạm qua `kb-validator-v3`.
6. Cùng ngân sách token với ĐK1 và ĐK2.

#### 5.3. Kho quy phạm dùng để so ĐK3-q với ĐK4-q

| Kho | Vai trò | Tỉ lệ bị loại đã đo |
|---|---|---|
| gpt-oss-120b | Chính | 7,5% |
| gemma4:31b | Model yếu hơn, lặp lại | 31,8% |
| gpt-oss-120b cài lỗi bằng `kb-plant` | Phép thử lan truyền lỗi | Lỗi cài: chủ thể bịa, đảo tính quy phạm, đổi số |

Phép thử cài lỗi lặp lại thí nghiệm ngày 10/11 (125 lỗi, không lỗi nào lan sang câu trả lời) dưới thiết kế mới, nơi model sinh không còn nguyên văn đầy đủ để dựa vào.

#### 5.4. Chỉ số

| Chỉ số | Cách tính | Giả thuyết |
|---|---|---|
| P, R, F1 của tập đơn vị được trích dẫn so với gold | Chỉ trên đơn vị có nhãn | H4 (chính) |
| Tỉ lệ câu gom đủ mọi đơn vị đáp án | Từ câu trả lời | H4 |
| Tỉ lệ câu trả lời lặp lại giá trị cài lỗi | So khớp chuỗi với giá trị đã cài | H5 (chính) |
| Tỉ lệ phát biểu sai tính quy phạm hoặc sai chủ thể | Người chấm trên mẫu | H5 |
| Recall mất do loại nhầm quy phạm đúng | ĐK4-q so với ĐK3-q trên kho sạch | Đánh đổi của kiểm chứng |
| Số token ngữ cảnh đã dùng | Từ lượt chạy | Hiệu quả |

#### 5.5. Cổng quyết định ngày 19/11

Trước khi cài phần sinh câu trả lời, chạy offline trên tập dev của bộ liệt kê:

- Tỉ lệ đơn vị đáp án gold có ít nhất một quy phạm trong kho gpt-oss (độ phủ trích xuất).
- Recall của bước lọc và xếp hạng ở 2.000 token so với ĐK2.

Nếu độ phủ trích xuất dưới 60% hoặc recall của ĐK3-q thấp hơn ĐK2, dừng phần sinh câu trả lời, báo cáo kết quả ở tầng truy xuất và phân tích nguyên nhân như một mắt xích RQ1 tới RQ3.
Ngưỡng 60% là đề xuất, cần nhóm xác nhận trước khi xem số.

#### 5.6. Việc cần làm

1. Module `retrieval/norm_query.py` (`norm-query-v1`), prompt `prompts/query-slots-v1.md`, cấu hình `configs/experiments/dk{3,4}-query.json`.
2. Chế độ ngữ cảnh "chỉ quy phạm kèm trích dẫn" trong `indexing/records.py` (dùng lại `compact_claim`).
3. `preflight`: ĐK3-q và ĐK4-q cùng lượt phân tích câu hỏi, cùng lượt trích xuất, ĐK4-q là tập con.
4. Lệnh sinh bộ liệt kê nháp từ gold và bảng kiểm lại cho người.
5. Test đơn vị cho lọc, so khớp chủ thể, đóng gói.

Không thay đổi bộ kiểm chứng trong đợt này.
Việc cho phép lấy chủ thể từ câu dẫn của khoản (nguyên nhân loại nhầm đã biết) là thay đổi sau khi đã xem kết quả, nên chỉ ghi vào hướng phát triển, trừ khi nhóm khai báo nó là một biến thể riêng trước khi đo.

Việc cần duyệt: lượt gọi model cho phân tích câu hỏi và sinh câu trả lời (số lượng ở mục 9).
Rủi ro: gold trích xuất chậm làm bộ liệt kê chậm theo; phương án lùi là 20 câu trên phần gold đã đối soát.
Người phụ trách: Kha (lọc theo trường, kho quy phạm, cài lỗi), Vũ (truy xuất, ngữ cảnh, chấm).

### WP6. Model mã nguồn mở cho kết quả chính (quyết định trước 24/11)

Mục tiêu: kết quả chính khớp cam kết của đề cương về mô hình mã nguồn mở.

Đề xuất:

| Vai trò | Model | Ghi chú |
|---|---|---|
| Trích xuất ĐK3/ĐK4 | gpt-oss-120b qua 9Router | Đã chốt 08/11 |
| Tách vấn đề, phân tích câu hỏi | gpt-oss-120b | Một lượt dùng chung cho mọi điều kiện |
| Sinh câu trả lời, kết quả chính | gpt-oss-120b | `answer-run --router-model ... --approve-router` |
| Sinh câu trả lời, kiểm độ vững | Claude Haiku 5.5 | Chỉ trên bộ khó |
| Giám khảo bổ sung | Claude Sonnet 5.5 | Đề cương cho phép model làm công cụ chấm hỗ trợ; kết luận dựa trên người chấm |
| Embedding | BGE-M3 cục bộ | Đã chốt |

Việc cần làm:

1. Chạy thử 20 câu để đo tỉ lệ lỗi gọi và thời gian của 9Router trước khi khóa.
2. Quy tắc dự phòng chốt trước: nếu sau hai lần thử lại còn hơn 5% lượt lỗi, toàn bộ đợt chạy chuyển sang Haiku 5.5 và ghi vào nhật ký; không đổi model giữa chừng hay theo từng câu.
3. Chốt mục còn mở về bộ đếm token ở chương 4.9: giữ bộ đếm âm tiết cho mọi điều kiện và nêu là giới hạn, hoặc đổi sang bộ đếm của model sinh.
4. Ghi lý do dùng model đóng cho giám khảo và kiểm độ vững vào bảng điều chỉnh so với đề cương.

Người phụ trách: Vũ; cần người dùng duyệt endpoint, model, dữ liệu, phạm vi.

### WP7. Thí nghiệm tổng quát hóa ngoài luật lao động (28/11 đến 05/12, ưu tiên thấp nhất)

Mục tiêu: có số liệu cho câu "phương pháp không phụ thuộc lĩnh vực; thực nghiệm chính trên lao động".

Thiết kế: chạy nguyên pipeline đã khóa trên một luật và một nghị định của lĩnh vực khác, không tinh chỉnh.

Việc cần làm:

1. Chọn hai văn bản khác hẳn lao động, tổng khoảng 100-150 Điều, ưu tiên lĩnh vực có sẵn câu hỏi có nhãn bên ngoài (ví dụ giao thông hoặc doanh nghiệp); số hiệu cụ thể xác nhận trên vbpl.vn khi thực hiện.
2. Kiểm tra giấy phép và cách lấy các bộ dữ liệu ngoài (VLQA, dữ liệu ALQAC) trước khi dùng; đây là truy cập ngoài, cần người dùng duyệt.
   Nếu không dùng được: model soạn 20-30 câu, hai người duyệt.
3. Rà 11 tệp prompt có nhắc luật lao động; với prompt ghi cứng lĩnh vực trong vai trò hệ thống, tạo bản trung tính chỉ dùng cho lượt này và ghi rõ.
4. Chạy: tải văn bản, tách cấu trúc, trích xuất gpt-oss, kiểm chứng, truy xuất ĐK1 và ĐK2.

Chỉ số:

| Tầng | Chỉ số | Cách đo |
|---|---|---|
| Parser | Tỉ lệ Điều tách đúng cấu trúc | Hai người kiểm mẫu 30 Điều |
| Trích xuất | Tỉ lệ câu có quy phạm, tỉ lệ bị bộ kiểm chứng loại | Tự động |
| Trích xuất | Tỉ lệ quy phạm khớp nguyên văn và hợp lý | Hai người kiểm mẫu 50 quy phạm bằng đối chiếu chữ |
| Truy xuất | Recall theo ngân sách, ĐK1 và ĐK2 | Bộ câu hỏi ở bước 2 |

Không chạy ĐK3/ĐK4 và không sinh câu trả lời ở lĩnh vực mới.
Việc cần duyệt: hai lượt `vbpl-fetch`, khoảng 100-150 lượt trích xuất qua 9Router, tải dữ liệu ngoài.
Đây là gói bị cắt đầu tiên nếu trễ; khi đó tính tổng quát ghi vào hạn chế.
Người phụ trách: Kha.

### WP8. Nghiên cứu liên quan cho chương 2 (làm rải từ 12/11, xong trước 05/12)

Mục tiêu: điền các chỗ **[cần bổ sung trích dẫn]** ở mục 2.11 và định vị lại đóng góp.

Danh sách đọc (thông tin thư mục phải đối chiếu bản gốc trước khi trích; khi lập kế hoạch mới đọc tóm tắt):

| Mục chương 2 | Công trình | Dùng để |
|---|---|---|
| 2.11.1 | ALQAC 2025, ALQAC 2026; Zalo AI Challenge Legal Text Retrieval; VLQA (arXiv 2507.19995); VLegal-Bench (arXiv 2512.14554); VLSP 2025 LegalSLM | Bối cảnh dữ liệu và bài toán tiếng Việt |
| 2.11.2 | De Jure (arXiv 2604.02276); Galli và cộng sự về trích nghĩa vụ từ luật EU; Horner và cộng sự về logic nghĩa vụ | Công trình gần nhất với lược đồ quy phạm có nguyên văn |
| 2.11.3 | LegalBench-RAG; các nghiên cứu chia đoạn theo cấu trúc trên luật Hàn, Đức; Magesh và cộng sự 2024 | Cơ sở cho ĐK1 so với ĐK2 và cho yêu cầu truy vết |
| 2.11.3 | SAT-Graph RAG (arXiv 2505.00039); Three-Tier Knowledge Graph RAG cho luật Việt Nam (FAIA, 09/2026); ViHERMES (arXiv 2602.07361); KG-RAG trên PDPA Thái Lan (arXiv 2605.19806); đồ thị Bộ luật Hình sự (UD-JST, 12/2025) | Đồ thị và hiệu lực theo thời gian |
| Sản phẩm | AI Pháp luật trên Cổng Pháp luật quốc gia, AI Luật của LuatVietnam, Clex của CMC, Lexis+ AI, Westlaw | Bối cảnh thực tiễn |

Việc cần làm:

1. Mỗi công trình một dòng trong bảng so sánh: dữ liệu, cách biểu diễn, cách kiểm chứng, cách đánh giá, điểm khác với đề tài.
2. Viết lại mục 2.11.4: đóng góp "bằng chứng nguyên văn tới từng ô" không còn độc nhất; điểm riêng là kiểm chứng tất định bằng offset và mã băm, tiếng Việt, và đo tác động xuôi dòng bằng thiết kế bốn bậc cộng chèn lỗi.
3. Bổ sung khái niệm đóng gói ngữ cảnh rộng từ đơn vị nhỏ vào mục 2.2 làm cơ sở cho WP3.

Người phụ trách: cả hai, chia theo mục.

### WP9. Thực nghiệm chính thức (28/11 đến 09/12)

Điều kiện tiên quyết, kiểm ngày 27-28/11:

- Bộ câu hỏi và gold đã khóa, có mã băm.
- Corpus v3 đã khóa.
- Mọi cấu hình đã chốt trên dev: phương pháp truy xuất, biến thể đóng gói, prompt, ngân sách, model.
- `preflight` đạt trên dev.
- Toàn bộ test offline đạt.

Ma trận:

| Bộ câu hỏi | Điều kiện | Model sinh | Số lần sinh mỗi câu |
|---|---|---|---|
| Tra cứu (v1) | ĐK1-ĐK4 | gpt-oss-120b | 1 |
| Khó (tình huống, xung đột, phức tạp) | ĐK1-ĐK4 | gpt-oss-120b | 2 |
| Khó | ĐK1-ĐK4 | Haiku 5.5 | 1 |
| Hiệu lực | ĐK1, ĐK1-hl, ĐK2, ĐK3, ĐK4 | gpt-oss-120b | 2 |
| Liệt kê | ĐK1, ĐK2, ĐK3-q, ĐK4-q; thêm ĐK3-q và ĐK4-q trên kho gemma4 và kho cài lỗi | gpt-oss-120b | 2 |

Trình tự:

1. 28/11: kiểm mã băm, hạn mức, chạy thử 20 câu.
2. 29/11 đến 02/12: tách vấn đề và phân tích câu hỏi một lần; truy xuất; sinh câu trả lời; ghi mọi lỗi, không bỏ âm thầm câu thất bại.
3. 03-05/12: hai người chấm bảng che tên điều kiện; giám khảo Sonnet chấm toàn bộ; song song chạy WP7.
4. 06-07/12: đối soát điểm, tính đồng thuận, phân tích lỗi theo khung chương 4.7.
5. 08-09/12: điền bảng RQ1-RQ3, khóa kết quả.

Đo mức nhiễu:

- Nhiễu sinh: chênh lệch giữa hai lần sinh của cùng điều kiện trên bộ khó.
- Nhiễu giám khảo: chấm lại 50 câu trả lời lần hai.
- Mọi chênh lệch giữa các điều kiện được trình bày cạnh hai mức nhiễu này.

RQ1 và RQ2 (không phụ thuộc lượt sinh câu trả lời, đo sớm trong 24-27/11 theo mốc giai đoạn 4 của đề cương):

- `gold-score` cho `norm-rules-v2`, ĐK3, ĐK4 của gpt-oss, gemma4 và Opus trên gold đã khóa.
- `kb-inject` trên các kho ĐK4; lỗi còn sót so với gold.
- `kb-audit-score` trên bảng kiểm tra 104 dòng.

Chạy lại chỉ khi có lỗi phương pháp, ghi rõ phiên bản.

### WP10. Viết luận văn, demo và bảo vệ (viết rải từ 12/11, dồn 10-20/12)

Xem mục 10.

## 8. Lịch

| Ngày | Vũ | Kha | Mốc |
|---|---|---|---|
| 11-12/11 | WP0; bắt đầu WP2 | WP0; rà hướng dẫn gán nhãn | Quyết định ghi vào nhật ký; gửi giảng viên |
| 12-15/11 | WP2, WP3; gán nhãn bộ khó | WP4 dữ liệu và cạnh sửa đổi; gán nhãn gold | Gán nhãn thử 10 câu mỗi bộ, sửa hướng dẫn một lần |
| 16-19/11 | WP4 truy xuất và bộ hiệu lực; WP5 thử offline | WP5 lọc theo trường; gán nhãn gold | 16/11: chọn biến thể đóng gói; 19/11: cổng quyết định WP5 |
| 20-23/11 | WP5 ngữ cảnh và chấm; gán nhãn bộ tra cứu | Đối soát gold; bảng kiểm tra quy phạm bị loại; bộ liệt kê | 23/11: khóa bộ khó và gold |
| 24-25/11 | Khóa bộ câu hỏi; chốt cấu hình trên dev; WP6 chạy thử | RQ1, RQ2 đo sớm trên gold | 25/11: dừng thêm biến thể |
| 26-27/11 | `preflight` trên dev; đóng băng MVP; `demo-build` | Test, sao lưu, tài liệu lệnh | 27/11: MVP hoàn thành |
| 28/11 đến 02/12 | Lượt chạy chính | WP7; theo dõi lượt chạy | Held-out chạy một lần |
| 03-05/12 | Chấm câu trả lời | Chấm câu trả lời; WP7 | |
| 06-09/12 | Đối soát, phân tích lỗi, bảng RQ3 | Bảng RQ1, RQ2 | 09/12: khóa kết quả |
| 10-13/12 | Chương 3, 4 | Chương 2, 3 | Bản nháp đủ 5 chương |
| 14-16/12 | Demo, slide | Slide, hướng dẫn cài đặt | |
| 17-18/12 | Phản biện thử | Phản biện thử | |
| 19-20/12 | Dự phòng | Dự phòng | Không thêm tính năng |

Thứ tự cắt khi trễ:

1. WP7 (tổng quát hóa).
2. Phần sinh câu trả lời của WP5 (giữ kết quả tầng truy xuất).
3. Lần sinh thứ hai và lượt Haiku.
4. Độ nhạy cỡ đoạn ĐK1.

Không cắt: WP1, bốn điều kiện chính của WP9, và phần tối thiểu của WP4 (điền hiệu lực, chỉ số trích dẫn lỗi thời).

## 9. Ước tính lượt gọi model và mục cần duyệt

Số lượt là ước tính từ quy mô các bộ câu hỏi dự kiến (152 tra cứu, 99 khó, 30 hiệu lực, 40 liệt kê); con số thật phụ thuộc số câu sau khi khóa.

| Việc | Model | Số lượt ước tính |
|---|---|---|
| Soạn nháp bộ hiệu lực | model soạn nháp do nhóm chọn | khoảng 10 |
| Tách vấn đề, toàn bộ bộ câu hỏi | gpt-oss-120b | khoảng 320 |
| Phân tích câu hỏi bộ liệt kê | gpt-oss-120b | khoảng 40 |
| Sinh câu trả lời: tra cứu | gpt-oss-120b | khoảng 610 |
| Sinh câu trả lời: khó, hai lần | gpt-oss-120b | khoảng 790 |
| Sinh câu trả lời: hiệu lực, hai lần | gpt-oss-120b | khoảng 300 |
| Sinh câu trả lời: liệt kê, hai lần, gồm kho gemma4 và kho cài lỗi | gpt-oss-120b | khoảng 640 |
| Sinh câu trả lời: kiểm độ vững bộ khó | Haiku 5.5 | khoảng 400 |
| Giám khảo | Sonnet 5.5 | khoảng 2.700, hoặc khoảng 1.300 nếu chỉ chấm một lần sinh |
| Trích xuất hai văn bản lĩnh vực khác | gpt-oss-120b | khoảng 100-150 |

Phương án tối thiểu (một lần sinh, không Haiku, giám khảo chỉ trên bộ khó, hiệu lực và liệt kê): khoảng 1.400 lượt gpt-oss và khoảng 700 lượt Sonnet.

Mục cần người dùng duyệt trước khi thực hiện:

- `vbpl-fetch`: văn bản thay thế NĐ 12/2022; hai văn bản lĩnh vực khác.
- 9Router: endpoint, model gpt-oss-120b, dữ liệu là câu hỏi và đoạn luật công khai, phạm vi theo bảng trên.
- Claude Code: Haiku 5.5 và Sonnet 5.5 theo bảng trên.
- Tải bộ dữ liệu ngoài cho WP7.
- Đồng bộ Jira hoặc GitHub nếu nhóm muốn theo dõi các gói việc ở đó.

Không gói việc nào cần thêm thư viện.

## 10. Kế hoạch báo cáo

### 10.1. Thay đổi theo chương

| Chương | Thay đổi |
|---|---|
| 1 | Cập nhật phạm vi (corpus v3, số văn bản và số Điều thật); viết lại mục 1.6 theo bốn luận điểm ở mục 3; thêm bảng điều chỉnh so với đề cương |
| 2 | Điền mục 2.11 theo WP8; thêm cơ sở cho đóng gói theo Điều và cho hiệu lực theo thời gian |
| 3 | Thêm mô tả `pack-article-v1`, `amendment-rules-v1` và trạng thái đơn vị, `norm-query-v1`; cập nhật bảng công nghệ và model |
| 4 | Xem 10.2 |
| 5 | Hạn chế: không có chuyên gia pháp lý, bộ kiểm chứng chỉ kiểm hình thức, một lĩnh vực chính, cỡ mẫu; hướng phát triển: kiểm chứng theo nghĩa, đồ thị quan hệ, lấy chủ thể từ câu dẫn |

### 10.2. Bảng và hình của chương 4

| Mã | Nội dung | Nguồn |
|---|---|---|
| B1 | Độ tin cậy của nhãn: kappa, Dice, F1 giữa hai người | WP1 |
| B2 | RQ1: P, R, F1 theo ô và theo quy phạm; theo model | `gold-score` |
| B3 | RQ2: tỉ lệ bị loại theo loại lỗi chèn; lỗi còn sót so với gold; độ chính xác của việc loại | `kb-inject`, `kb-audit-score` |
| H1 | RQ2: tỉ lệ bị loại theo model trích xuất | `kb-compare` |
| H2 | Đường cong recall theo ngân sách token, ĐK1-ĐK4, mỗi bộ một hình | WP2 |
| B4 | Ngân sách cần để đạt ngưỡng recall; độ nhạy cỡ đoạn ĐK1 | WP2 |
| B5 | RQ3 chính: độ đúng, bám nguồn, trích dẫn đúng, trích dẫn theo ký tự, từ chối đúng và nhầm, theo điều kiện | WP9 |
| B6 | Bốn so sánh chính: chênh lệch, khoảng tin cậy 95%, p sau hiệu chỉnh Holm, thắng/thua | WP9 |
| B7 | Mức nhiễu sinh và nhiễu giám khảo | WP9 |
| B8 | Kết quả theo loại câu hỏi | WP9 |
| B9 | Tải kiểm chứng: token được trích mỗi phát biểu, tỉ lệ trích dẫn tới một đơn vị | WP2, WP9 |
| B10 | Hiệu lực: tỉ lệ trích dẫn lỗi thời theo điều kiện, gồm ĐK1-hl; độ chính xác của cạnh sửa đổi | WP4 |
| B11 | Liệt kê: P, R, F1; tỉ lệ gom đủ; ĐK1, ĐK2, ĐK3-q, ĐK4-q | WP5 |
| H3 | Lan truyền lỗi: tỉ lệ câu trả lời lặp lại lỗi cài, ĐK3-q so với ĐK4-q, theo kho | WP5 |
| B12 | Tổng quát hóa ngoài lao động | WP7 |
| B13 | Thăm dò: đồ thị quan hệ và chọn láng giềng, ghi rõ nhãn model và không dùng để kết luận | Lượt đã chạy |
| B14 | Phân tích lỗi theo nhóm và ví dụ | WP9 |
| B15 | Thời gian, token và chi phí theo lượt chạy | Manifest, nhật ký gọi |

Mỗi bảng trỏ được về thư mục lượt chạy và manifest.

### 10.3. Bảng điều chỉnh so với đề cương

Một bảng trong chương 1 hoặc chương 4, mỗi dòng gồm: nội dung đề cương, thực tế, lý do, ngày quyết định.
Các dòng đã biết: số văn bản và số Điều; phạm vi bộ kiểm chứng; đo RQ1 theo quy phạm; model đóng cho giám khảo và kiểm độ vững; câu hỏi do model soạn nháp; bộ câu hỏi khóa trễ; thêm corpus v2, v3 và các bộ câu hỏi mới; hai điều kiện mở rộng ĐK3-q, ĐK4-q và đối chứng ĐK1-hl.

### 10.4. Tóm tắt gửi giảng viên (ngày 12/11)

Một trang, gồm:

1. Kết quả chạy thử trung thực: bảng ở mục 2.1 và 2.2, ghi rõ nhãn do model soạn.
2. Điều đã thấy: cấu trúc giúp truy vết; kho quy phạm và kiểm chứng chưa giúp câu trả lời tra cứu.
3. Đề xuất: bốn luận điểm ở mục 3 và hai điều kiện mở rộng.
4. Các điều chỉnh so với đề cương cần thầy duyệt.
5. Lịch tới 20/12.

### 10.5. Báo cáo tiến độ

- Sau mỗi gói việc: một tài liệu kết quả trong `docs/results/` và một dòng trong `docs/decisions.md`.
- Mỗi tuần: `docs/planning/progress-<ngày>.md` theo mẫu của `progress-2026-11-08.md`.

### 10.6. Tài liệu trong repo cần cập nhật khi thực hiện

- `docs/evaluation-protocol.md`: thêm chỉ số theo ngân sách token, bộ hiệu lực, bộ liệt kê, đo mức nhiễu.
- `docs/thesis/chuong-4-thuc-nghiem-va-danh-gia.md`: mục 4.1.2, 4.1.3 và bảng 4.9.
- `PRODUCT.md` (mục Evidence on Hand và Operating Context) và `AGENTS.md` còn ghi ĐK3/ĐK4 và chấm câu trả lời chưa làm.
- `CLAUDE.md`: lệnh mới nếu có.

### 10.7. Dàn ý bảo vệ

1. Vấn đề: câu trả lời "có nguồn" chưa chắc "đúng nguồn".
2. Thiết kế bốn bậc và vì sao mỗi bậc đổi một yếu tố.
3. Kết quả một: cấu trúc cho trích dẫn chính xác hơn với ít token hơn.
4. Kết quả hai: hiệu lực ở mức Khoản, Điểm.
5. Kết quả ba: kho quy phạm trả lời câu liệt kê; kiểm chứng chặn lỗi lan truyền.
6. Kết quả âm và vì sao: câu tra cứu không cần kho quy phạm.
7. Demo: nhập văn bản, duyệt quy phạm, hỏi đáp có trích dẫn, cảnh báo hiệu lực.
8. Hạn chế và hướng phát triển.

## 11. Rủi ro

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Gán nhãn chậm | Dưới 50% bộ khó vào 18/11 | Giảm gold xuống 30 Điều, bộ tra cứu xuống 80 câu; không dùng nhãn model thay thế |
| Đồng thuận thấp | Kappa dưới 0,6 sau lượt thử | Sửa hướng dẫn một lần, gán lại phần thử; báo cáo kappa thật |
| 9Router quá tải | Hơn 5% lượt lỗi sau thử lại | Quy tắc dự phòng ở WP6 |
| H2 không đạt | Không biến thể đóng gói nào hơn P0 | Báo cáo đánh đổi độ phủ và truy vết như kết quả |
| H4 không đạt | Cổng 19/11 không qua | Báo cáo ở tầng truy xuất; phân tích độ phủ trích xuất |
| Ít sửa đổi mức đơn vị trong corpus | Dưới 10 cạnh | Thu nhỏ nhóm câu này; giữ nhóm văn bản hết hiệu lực |
| Giảng viên không đồng ý điều kiện mở rộng | Phản hồi sau 12/11 | Chỉ giữ ĐK1-ĐK4 và WP1-WP4; WP5 thành hướng phát triển |
| Chọn chỉ số sau khi xem kết quả | Thêm chỉ số ngoài mục 4 | Ghi là thăm dò; không dùng để kết luận |
| Rò rỉ dev sang held-out | Sửa hệ thống sau khi xem held-out | Công bố vi phạm theo giao thức; tạo tập kiểm tra mới nếu được |

## 12. Câu hỏi cần quyết trước khi bắt đầu

1. "Không chỉ luật lao động" có nghĩa là luận văn cần thí nghiệm ngoài lao động (WP7) hay chỉ cần định vị so với giải pháp pháp luật nói chung?
2. Dừng nhánh "đồ thị quan hệ + chọn láng giềng" ở các lượt đã chạy và dùng WP5 làm điều kiện mở rộng duy nhất, hay giữ cả hai?
3. Chấp nhận đổi cách đóng gói ngữ cảnh của ĐK2-ĐK4 (WP3) trong kết quả chính, hay báo cáo nó như biến thể?
4. Kết quả chính dùng gpt-oss-120b để sinh câu trả lời (WP6), hay giữ Claude và giải trình?
5. Ngưỡng 60% ở cổng quyết định WP5 và biên 0,05 của H2 có được chấp nhận không?
6. Bộ câu hỏi và gold hiện đã có bao nhiêu nhãn người?
7. Có người có nền luật nào hỗ trợ kiểm một mẫu không? Nếu có, kết quả của họ được báo cáo riêng như đề cương nêu.
8. Giảng viên đã phản hồi gì về corpus v2 và thiết kế ĐK3/ĐK4 ngày 09/11?

## 13. Định nghĩa hoàn thành

- Bộ câu hỏi, gold và corpus khóa bằng mã băm trước lượt chạy chính.
- `preflight` đạt cho mọi nhóm điều kiện được báo cáo.
- Mỗi giả thuyết ở mục 4 có một kết luận đạt, không đạt hoặc không đủ dữ liệu, kèm khoảng tin cậy và mức nhiễu.
- Mọi bảng ở mục 10.2 trỏ về lượt chạy tái lập được từ đầu ra đã lưu.
- Bảng điều chỉnh so với đề cương đầy đủ và đã trình giảng viên.
- Toàn bộ test offline đạt; `svelte-check` không lỗi; E2E trình duyệt đạt trên store dựng bằng `demo-build`.
