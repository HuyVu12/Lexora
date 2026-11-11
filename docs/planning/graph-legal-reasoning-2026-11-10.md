# Đồ thị tri thức cho tình huống phức tạp và văn bản chồng chéo (10/11/2026)

Tài liệu đề xuất, chưa triển khai.
Mục tiêu: dùng đồ thị quan hệ giữa các văn bản để xử lý vụ việc nhiều vấn đề và các văn bản quy phạm chồng chéo (hướng dẫn, ngoại lệ, chế tài, sửa đổi), thay vì chỉ thêm vài láng giềng khi truy xuất.
Căn cứ: kết quả chạy thử `docs/results/dk-comparison-2026-11-10.md`, lượt quan hệ `experiments/runs/relations-v2-sonnet/`, mã nguồn `src/legal_ai/evaluation/relation_run.py`, `src/legal_ai/kb/references.py`, `src/legal_ai/evaluation/retrieval_run.py`.

## 1. Hiện trạng

### 1.1 Bốn điều kiện đang được cài đặt thế nào

| ĐK | Ý tưởng | Cài đặt hiện tại (corpus v2) |
|---|---|---|
| ĐK1 | Đoạn cố định | Đoạn 384 token, cắt ngang Điều |
| ĐK2 | Theo cấu trúc | Một bản ghi cho mỗi đơn vị lá (Điều/Khoản/Điểm), gắn ID và offset |
| ĐK3 | Quy phạm do LLM trích | Bản ghi ĐK2 (nguyên văn đầy đủ) cộng một dòng quy phạm (`claims_view: compact`), mở rộng theo đồ thị |
| ĐK4 | Quy phạm đã kiểm chứng | ĐK3 bỏ các quy phạm không qua `kb-validator-v3` |

Ví dụ thật, BLLĐ Điều 26, bản ghi ĐK3 đưa cho model sinh:

```
Điều 26. Tiền lương thử việc
Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.
[Quy phạm 1] nghĩa vụ · Chủ thể: hai bên · Bên thụ hưởng: người lao động · Điều kiện: trong thời gian thử việc · Định lượng: 85%
```

### 1.2 Đồ thị hiện có

Nút: văn bản, Chương, Điều, Khoản, Điểm, quy phạm, thực thể.
Cạnh, ba nguồn:

1. Cấu trúc: Điều chứa Khoản, Khoản chứa Điểm.
2. Dẫn chiếu theo quy tắc (`kb/references.py`): biểu thức chính quy bắt "khoản 1 Điều 21 của Bộ luật này", "Điều 26 của Bộ luật Lao động"; "Bộ luật này", "Nghị định này" chỉ chính văn bản chứa câu; tên văn bản tra qua bí danh trong `configs/knowledge-graph.json`; dẫn chiếu không xác định được văn bản đích được ghi là chưa giải quyết.
3. Quan hệ có kiểu giữa các Điều (`relation-run-v1`, Claude Sonnet 5.5 qua Claude Code, 711 Điều, 711 lượt, 0 lỗi):
   - mỗi Điều nhận khoảng 40 ứng viên chọn tự động trên toàn corpus: Điều có dẫn chiếu tới/từ nó, Điều giống nhất theo BM25 (đủ 10), thêm 30 Điều gần nhất theo BGE-M3;
   - model chọn ứng viên có quan hệ và gắn một trong 5 loại (ngoại lệ, thủ tục, hệ quả, điều kiện, chi tiết), kèm trích dẫn nguyên văn ở hai đầu;
   - kiểm tra offline: đích nằm trong danh sách ứng viên, loại hợp lệ, hai trích dẫn đúng nguyên văn;
   - kết quả: 2.130 quan hệ được giữ (điều kiện 716, chi tiết 633, thủ tục 401, hệ quả 284, ngoại lệ 96), 5 bị loại; 636 cạnh nối hai văn bản khác nhau, 1.494 cạnh trong cùng văn bản.

Ví dụ thật quanh BLLĐ Điều 26:

```
BLLĐ Đ24 Thử việc  --chi tiết-->  BLLĐ Đ26 Lương thử việc >= 85%  --điều kiện-->  BLLĐ Đ90 Lương >= tối thiểu
                                        ^
                                        | "điều kiện" (thực chất là chế tài)
NĐ 12/2022 Đ10: "Trả lương cho người lao động trong thời gian thử việc thấp hơn 85% mức lương của công việc đó"
```

### 1.3 Đồ thị đang được dùng thế nào

- Trong ĐK3/ĐK4: sau khi xếp hạng, mỗi bản ghi được thêm tối đa 2 láng giềng theo cạnh dẫn chiếu hoặc quan hệ, chỉ khi câu hỏi cũng khớp với láng giềng (`require_match: true`), độ dài danh sách giữ nguyên.
- Trong web app: xem và duyệt (Cytoscape, `frontend/src/routes/kb/[id]/graph`), cạnh gộp thực thể do người duyệt tạo.
- Model sinh nhận danh sách đoạn E01, E02... phẳng và không biết quan hệ giữa chúng.

## 2. Giới hạn

### 2.1 Ở kết quả

- ĐK2 so với ĐK1 đạt rõ ở độ chính xác trích dẫn (+0,15 đến +0,21, thắng/thua 36/6, 39/3, 22/1), không khác ở độ đúng.
- ĐK3 so với ĐK2 và ĐK4 so với ĐK3 chưa chứng minh được; chênh lệch độ đúng cỡ 0,05-0,10 nằm trong mức nhiễu của việc sinh câu trả lời và của giám khảo.
- Mở rộng theo đồ thị chỉ kéo thêm đơn vị đáp án vào ngữ cảnh ở 8 trường hợp (bộ xung đột) và 24 trường hợp (bộ tình huống); thêm đồ thị quan hệ không đổi kết luận.
- Điểm sáng duy nhất của ĐK3: số vấn đề giải quyết được trên bộ xung đột +0,085 [+0,03; +0,14], 13/2.

### 2.2 Ở thiết kế ĐK3/ĐK4

- Model sinh bỏ qua dòng quy phạm vì nguyên văn đầy đủ nằm ngay phía trên: cài 125 lỗi vào dòng quy phạm, câu trả lời không lặp lại lỗi nào, độ đúng khi có lỗi bằng khi sạch (+0,000 [-0,068; +0,068]).
- Vì vậy ĐK3 gần như là ĐK2, và việc ĐK4 làm sạch KB không tác động được tới câu trả lời.

### 2.3 Ở bộ kiểm chứng

- Chỉ kiểm tra hình thức (nguyên văn, schema, từ tình thái, trùng lặp), không kiểm tra nghĩa.
- Giữ quy phạm sai nghĩa: ở BLLĐ Điều 26, "Chủ thể: hai bên" là chủ thể của việc thỏa thuận, còn nghĩa vụ trả ít nhất 85% thuộc về người sử dụng lao động; "Hành vi: bằng" không phải hành vi.
- Loại nhầm quy phạm đúng: BLLĐ Điều 6 khoản 1 điểm d "Đóng cửa tạm thời nơi làm việc", chủ thể "Người sử dụng lao động" nằm ở câu dẫn của khoản nên bị loại; 31 bản ghi BLLĐ trong bộ xung đột mất quy phạm theo kiểu này.
- Bỏ phủ định, bỏ ngoại lệ, bỏ điều kiện gần như không bị bắt (0-3% trong `kb-inject`).
- Trên dữ liệu thật chỉ loại khoảng 5% quy phạm (3.631 còn 3.451), nên ĐK4 rất gần ĐK3.

### 2.4 Ở đồ thị

- Bước quan hệ bị chặn bởi danh sách ứng viên: Điều không lọt vào khoảng 40 ứng viên thì không bao giờ được nối.
- "Được giữ" chỉ nghĩa là trích dẫn có thật, không nghĩa là loại quan hệ đúng; cạnh NĐ 12/2022 Đ10 -> BLLĐ Đ26 bị gắn "điều kiện" trong khi là chế tài.
- Bộ 5 loại thiếu "chế tài", "sửa đổi/thay thế/bãi bỏ" và "mâu thuẫn".
- Chưa có cạnh nào được người kiểm tra, nên chưa có precision hay recall của đồ thị.
- Cạnh ở mức Điều, chưa xuống mức Khoản, Điểm hay quy phạm.
- Mở rộng dùng `require_match`, chặn đúng loại láng giềng có ích nhất: chế tài và ngoại lệ thường không trùng chữ với câu hỏi.

### 2.5 Ở hiệu lực văn bản

- Không có cạnh sửa đổi, thay thế; không lọc theo thời điểm xảy ra vụ việc.
- `legal_status` của cả 9 văn bản trong corpus v2 là `unknown`.
- NĐ 12/2022/NĐ-CP có `effective_to: 2026-09-10`, tức đã hết hiệu lực tại thời điểm viết tài liệu này, nhưng vẫn được truy xuất như mọi văn bản khác và văn bản thay thế không có trong corpus.

### 2.6 Ở dữ liệu đánh giá

- Nhãn đáp án, vấn đề và kết luận chuẩn do model soạn, chưa có người duyệt; giám khảo là Sonnet, chưa đo đồng thuận với người.
- 25-44 câu mỗi bộ; phát hiện chênh lệch cỡ 0,05 cần khoảng 150-200 câu cho mỗi so sánh.
- Bộ tình huống bị hiệu ứng sàn (không câu nào đạt độ đúng 2) vì corpus thiếu văn bản tòa đã dùng.

## 3. Cải tiến đề xuất

Ý tưởng chung: đồ thị là bản đồ lập luận pháp lý.
Với mỗi vấn đề, người làm luật tìm quy định gốc, lần theo hướng dẫn, ngoại lệ, chế tài và sửa đổi, rồi xác định quy định nào được ưu tiên áp dụng khi mâu thuẫn.
Hệ thống nên làm đúng chuỗi đó, và cho model sinh thấy chuỗi đó.

### 3.1 Nâng cấp đồ thị

Loại cạnh:

| Loại | Ví dụ | Tạo bằng |
|---|---|---|
| ngoại lệ, điều kiện, thủ tục, chi tiết/hướng dẫn, hệ quả | đã có | LLM (đã chạy) |
| chế tài (mới) | NĐ 12/2022 Đ10 -> BLLĐ Đ26 | LLM, chạy lại `relation-run` với prompt mới |
| sửa đổi, thay thế, bãi bỏ (mới), có ngày hiệu lực | văn bản mới sửa Điều X | metadata vbpl.vn và quy tắc ("được sửa đổi, bổ sung như sau") |
| mâu thuẫn tiềm ẩn (mới) | hai Điều quy định khác nhau cho cùng một việc | LLM đề xuất, người duyệt |

Thuộc tính nút văn bản: cơ quan ban hành, cấp hiệu lực pháp lý (Luật > Nghị định > Thông tư), ngày ban hành, ngày hiệu lực, ngày hết hiệu lực, tình trạng.
Phần lớn đã có trong `document.json` lấy từ vbpl.vn; cần điền `legal_status` từ dữ liệu đã tải thay vì để `unknown`.

Hạ cạnh xuống mức quy phạm: nối "nghĩa vụ trả ít nhất 85%" ở BLLĐ Đ26 với "phạt khi trả thấp hơn 85%" ở NĐ 12/2022 Đ10, thay vì chỉ nối Điều với Điều.
Khi đó KB quy phạm của ĐK3/ĐK4 mới có vai trò trong lập luận.

### 3.2 Truy xuất theo vấn đề và theo loại cạnh

```
Vụ việc
  -> tách vấn đề (decompose-v1, đã có)
  -> mỗi vấn đề: hybrid BM25 + BGE-M3 lấy quy định gốc
  -> mở rộng theo danh sách kiểm tra cố định:
       luôn kéo thêm ngoại lệ, chế tài, văn bản hướng dẫn, sửa đổi
       (không dùng require_match cho các loại này)
  -> lọc theo hiệu lực tại thời điểm xảy ra vụ việc
  -> gắn nhãn ưu tiên áp dụng, tất định, không dùng LLM:
       hiệu lực pháp lý cao hơn, ban hành sau, quy định riêng
       (theo Luật Ban hành văn bản quy phạm pháp luật)
```

Danh sách kiểm tra theo loại cạnh là điểm mấu chốt: chế tài được kéo vào vì câu hỏi "vi phạm thì sao?" luôn phải được hỏi, không phải vì câu hỏi có chữ "phạt".
Ngân sách token vẫn giữ chung cho mọi ĐK để so sánh công bằng.

### 3.3 Gói căn cứ có cấu trúc cho model sinh

Thay danh sách phẳng bằng gói theo vấn đề, quan hệ ghi rõ:

```
Vấn đề 1: Mức lương thử việc
  [Quy định gốc]  E01 BLLĐ Đ26: "ít nhất phải bằng 85% mức lương của công việc đó"
  [Giới hạn dưới] E02 BLLĐ Đ90: "không được thấp hơn mức lương tối thiểu"   (E02 là điều kiện của E01)
  [Chế tài]       E03 NĐ 12/2022 Đ10: "thấp hơn 85% mức lương..."           (E03 là chế tài của E01; hết hiệu lực 10/09/2026)
```

Model trả lời theo từng vấn đề: quy định, áp dụng vào sự kiện, kết luận.
Khi dùng ngoại lệ hoặc chế tài, câu trả lời phải trích dẫn cả hai đầu của cạnh; cổng trích dẫn hiện có bỏ phát biểu không có căn cứ.
Cách này xử lý thẳng nguyên nhân mục 2.2: quan hệ trở thành phần chính của ngữ cảnh, không còn là chú thích phụ.

### 3.4 Kiểm chứng cạnh và quy phạm theo nghĩa

- Cạnh: hai trích dẫn đúng nguyên văn (đã có); loại hợp lý với văn bản nguồn (cạnh "chế tài" phải xuất phát từ văn bản xử phạt và có cụm "phạt"); khoảng hiệu lực của hai đầu có giao nhau.
- Quy phạm: cho phép lấy chủ thể từ câu dẫn của khoản; kiểm tra chủ thể của nghĩa vụ có khớp với vị trí từ tình thái; cân nhắc một LLM thứ hai đối chiếu nghĩa và ghi kết quả là "chưa xác minh" khi không chắc.
- Cạnh và quy phạm dùng trong câu trả lời cho người dùng thật đi qua giao diện duyệt trong app, giữ trạng thái `needs_review` cho tới khi người duyệt.

### 3.5 Cách đo

- Báo cáo như một điều kiện mới (đề xuất tên ĐK3-graph và ĐK4-graph), tách khỏi kết quả chạy thử 10/11.
- Chỉ số tầng truy xuất, ít nhiễu: ngữ cảnh có đủ chuỗi căn cứ cần thiết không (quy định gốc, ngoại lệ, chế tài, hướng dẫn) so với nhãn người; không phụ thuộc model sinh và giám khảo.
- Chỉ số tầng câu trả lời: số vấn đề giải quyết được, độ khớp kết luận, độ đúng, độ chính xác trích dẫn theo ký tự.
- Chỉ số của đồ thị: precision theo cạnh và theo loại trên mẫu khoảng 100 cạnh, hai người gán nhãn độc lập, có kappa.
- Bộ xung đột mở rộng lên khoảng 100 câu có người duyệt; sinh câu trả lời hai lần mỗi câu để tách nhiễu sinh.
- Thiết kế chốt trên dev, đo một lần trên held-out; không chỉnh thiết kế dựa trên các bộ câu đã chạy thử rồi báo cáo trên chính các bộ đó.

## 4. Kế hoạch

| Giai đoạn | Việc | Ước tính | Cần duyệt |
|---|---|---|---|
| 1 | Thêm loại "chế tài" vào `relation-llm`, chạy lại 711 Điều; mở rộng theo danh sách kiểm tra; gói căn cứ có cấu trúc trong `answer-run` | 3-4 ngày | 711 lượt Sonnet 5.5 qua Claude Code |
| 2 | Điền tình trạng hiệu lực từ metadata vbpl; cạnh sửa đổi, thay thế; lọc theo thời điểm vụ việc; nhãn ưu tiên áp dụng | 2-3 ngày | Tải văn bản thay thế NĐ 12/2022 (một văn bản vbpl.vn) |
| 3 | Gán nhãn khoảng 100 cạnh; mở rộng và duyệt bộ xung đột | song song | Người gán nhãn |
| 4 | Cạnh ở mức quy phạm | nếu còn thời gian trước 27/11 | Tùy cách làm |

Giai đoạn 1 dùng lại đồ thị quan hệ, `decompose-v1` và truy xuất hybrid, chỉ đổi cách mở rộng và cách đóng gói ngữ cảnh, nên là bước có khả năng tạo khác biệt đo được nhanh nhất.

## 5. Câu hỏi mở

- Giữ ĐK3/ĐK4 hiện tại làm kết quả chính và báo cáo ĐK3-graph/ĐK4-graph là thí nghiệm bổ sung, hay thay thế?
- Model trích xuất quan hệ: tiếp tục Sonnet 5.5 hay dùng model mã nguồn mở qua 9Router để khớp đề cương?
- Văn bản nào thay thế NĐ 12/2022/NĐ-CP, và có đưa vào corpus v3 không?

## 6. Thử nghiệm nhỏ giai đoạn 1 (11/11/2026, offline, chưa gọi model)

Mục tiêu: xem mở rộng theo chuỗi pháp lý có đưa thêm đơn vị đáp án vào ngữ cảnh không, trước khi tốn lượt gọi model cho câu trả lời.
Đây là chạy thăm dò trên hai bộ chạy thử (nhãn do model đề xuất, chưa có người duyệt); cấu hình được chọn sau một lượt dò nhỏ trên chính hai bộ này, nên kết quả là lạc quan.

### 6.1 Đã cài đặt

- `src/legal_ai/retrieval/legal_chain.py` (`legal-chain-v1`):
  - loại `sanction` suy ra không cần model: quan hệ có đúng một đầu thuộc văn bản xử phạt vi phạm hành chính (NĐ 12/2022) được đổi thành chế tài, giữ loại gốc của model trong `llm_type`; 182 quan hệ;
  - neo mỗi quan hệ vào đơn vị chứa trích dẫn nguyên văn của nó thay vì cả Điều: 1.772/2.130 đầu nguồn và 1.470/2.130 đầu đích neo được tới Khoản hoặc Điểm, phần còn lại giữ mức Điều;
  - vai trò láng giềng: ngoại lệ, chế tài, quy định gốc (chỉ khi đơn vị tìm được là chế tài, hướng dẫn hoặc ngoại lệ của nó), hướng dẫn chi tiết, điều kiện, thủ tục, hệ quả, dẫn chiếu;
  - không dùng điều kiện khớp từ khóa; láng giềng được chọn theo độ gần với câu hỏi bằng BGE-M3 trên toàn bộ index (trong top 300), mỗi Điều láng giềng chỉ lấy một đơn vị.
- `retrieval_run`: chế độ `graph.chain`; cấu hình `configs/experiments/corpus-v2/dk{3,4}-chain.json` (3 kết quả tìm kiếm đầu, mỗi kết quả thêm 1 láng giềng).
- `answer_run`: tùy chọn `relations_in_context` đưa quan hệ giữa các đoạn vào request ("E02 là chế tài đối với E01, E03"), prompt `prompts/answer-v3.md`, cấu hình `configs/experiments/answer-chain-haiku.json`.
- Test: `tests/test_legal_chain.py` (8 test) và một test trong `tests/test_answer_run.py`; toàn bộ 250 test offline đạt.

### 6.2 Kết quả truy xuất

Chênh lệch theo cặp câu hỏi, KTC bootstrap 95%, thắng/thua; T@n là recall trong n token ngữ cảnh.

| So sánh | Bộ | R@5 | T@1000 | T@2000 |
|---|---|---|---|---|
| ĐK3-chain so với ĐK3 | Xung đột (25) | +0,008 [-0,024; +0,040] | +0,016 [-0,016; +0,048] | +0,018 [0,000; +0,046], 2/0 |
| ĐK3-chain so với ĐK3 | Tình huống (44) | -0,008 [-0,043; +0,028] | +0,020 [-0,014; +0,055] | +0,027 [-0,018; +0,072], 12/6 |
| ĐK3-chain so với ĐK2 | Xung đột | -0,022 [-0,080; +0,034] | -0,072 [-0,130; -0,012] | +0,010 [-0,032; +0,052] |
| ĐK3-chain so với ĐK2 | Tình huống | +0,040 [-0,008; +0,085] | -0,011 [-0,059; +0,037] | +0,024 [-0,033; +0,080] |
| ĐK4-chain so với ĐK4 | Xung đột | +0,024 [-0,008; +0,056] | +0,016 [-0,016; +0,048] | +0,010 [-0,016; +0,042] |
| ĐK4-chain so với ĐK4 | Tình huống | -0,017 [-0,053; +0,021] | +0,030 [-0,001; +0,064] | +0,016 [-0,024; +0,055] |

Thiếu hụt T@1000 so với ĐK2 có từ trước: bản ghi ĐK3 dài hơn vì có dòng quy phạm (ĐK3 so với ĐK2 là -0,088 trên bộ xung đột).

Những gì học được qua các lần thử:

- Bản đầu theo đúng đề xuất (luôn kéo theo vai trò, không xét câu hỏi) làm truy xuất kém đi rõ rệt: ĐK3-chain so với ĐK2 R@5 -0,074 [-0,120; -0,028] trên bộ xung đột.
  Láng giềng được thêm chỉ trúng đơn vị đáp án khoảng 6%, trong khi kết quả tìm kiếm trúng khoảng 17-22%, nên mỗi láng giềng đẩy ra một kết quả tốt hơn nó.
- Nguyên nhân chính: mỗi Điều có trung bình vài láng giềng mà chỉ lấy được 1-2; thứ tự vai trò không biết láng giềng nào liên quan tới vụ việc.
  Vai trò "quy định gốc" theo chiều ngược của điều kiện và thủ tục còn kéo vào mọi Điều dùng chung một định nghĩa.
- Chọn láng giềng theo độ gần với câu hỏi và chỉ mở rộng vài kết quả đầu đưa chênh lệch về mức trung tính đến hơi dương, nhưng không có chênh lệch nào vượt khỏi khoảng tin cậy một cách thuyết phục.
- Đồ thị có nối các đơn vị đáp án với nhau: 67-68% Điều đáp án có quan hệ trực tiếp với một Điều đáp án khác của cùng câu hỏi; vậy giới hạn nằm ở việc chọn láng giềng, không phải ở chỗ đồ thị thiếu cạnh.
- Ví dụ tốt (câu x20, nghĩa vụ và chế tài): kết quả tìm kiếm số 1 là Luật ATVSLĐ Đ64 k1 điểm c, chuỗi kéo ngay NĐ 12/2022 Đ31 k2 (chế tài, đúng đơn vị đáp án) lên vị trí 2.

### 6.3 Quan hệ trong ngữ cảnh câu trả lời (xem trước, chưa gọi model)

- Với ngân sách 3.000 token, 24/25 ngữ cảnh bộ xung đột và 44/44 ngữ cảnh bộ tình huống có ít nhất một quan hệ; trung bình khoảng 60-70 token cho các dòng quan hệ, nằm ngoài ngân sách ngữ cảnh.
- Ví dụ câu x20: "E02 là chế tài đối với E01, E03, E09, E11, E13, E17", "E06 là hướng dẫn chi tiết của E12".
- Điểm yếu thấy được: quan hệ neo ở mức Điều hoặc Khoản lan ra mọi Điểm bên dưới, nên một chế tài được gắn cho nhiều Điểm mà có thể chỉ đúng với một vài Điểm.

### 6.4 Nhận định

- Ở tầng truy xuất, đồ thị theo chuỗi pháp lý không làm thay đổi đáng kể lượng đơn vị đáp án vào ngữ cảnh; đây là kết quả âm cần báo cáo, phù hợp với kết quả 10/11.
- Giá trị còn lại cần kiểm tra là ở tầng câu trả lời: model có dùng được thông tin "đoạn nào là chế tài, ngoại lệ, hướng dẫn của đoạn nào" để giải quyết thêm vấn đề hay không; phép thử này cần gọi model.
- Phép thử đề xuất (cần duyệt): cùng lượt truy xuất ĐK3-chain trên hai bộ (69 câu), sinh câu trả lời bằng Claude Haiku 5.5 hai lần, một lần có `relations` và prompt `answer-v3`, một lần không (prompt `answer-v2`), rồi chấm bằng giám khảo Sonnet 5.5 (`judge-v2`); khoảng 138 lượt Haiku và 138 lượt Sonnet qua Claude Code.
  So sánh hai lần này tách được tác dụng của việc đưa quan hệ vào ngữ cảnh khỏi tác dụng của truy xuất.

## 7. Thử nghiệm LLM chọn láng giềng (11/11/2026)

Câu hỏi: nếu một model đọc câu hỏi và các láng giềng trên đồ thị rồi chọn láng giềng cần thiết, thay cho quy tắc ở mục 6, thì ngữ cảnh có chứa nhiều đơn vị đáp án hơn không, và có làm hỏng câu hỏi đơn giản không.

### 7.1 Thiết lập

- `src/legal_ai/evaluation/neighbor_select.py` (`neighbor-select-v1`), lệnh `cli neighbor-select`, prompt `prompts/neighbor-select-v1.md`.
- Gốc: ĐK3 không mở rộng đồ thị (`configs/experiments/corpus-v2/dk3-compact-nograph.json`), truy xuất hybrid.
- Ứng viên: láng giềng trên đồ thị `legal-chain-v1` của 5 kết quả đầu, mỗi Điều láng giềng một đơn vị, bỏ những đơn vị đã nằm trong 10 kết quả đầu, tối đa 30 (trung bình 10-13 mỗi câu).
- Model nhận câu hỏi (và các vấn đề đã tách, ở bộ tình huống), 5 đoạn đã tìm được, các ứng viên kèm nhãn quan hệ ("chế tài đối với S1"), và chọn tối đa 4 ứng viên hoặc không chọn gì.
- Đoạn được chọn chuyển lên ngay sau đoạn đã kéo nó vào; độ dài danh sách và ngân sách token giữ nguyên như mọi ĐK.
- Model: Claude Haiku 5.5 (effort medium) qua Claude Code, 127 lượt, 0 lỗi; được người dùng duyệt ngày 11/11/2026.
- Bộ câu hỏi trộn `experiments/runs/mixed-select-v1/questions.json`, bản theo dõi trong Git ở `experiments/question-drafts-mixed-v1/` (85 câu, xáo trộn): 25 câu tra cứu đơn giản và 5 câu ngoài phạm vi lấy mẫu từ `dryrun-v1`, 30 câu phức tạp (`dryrun-complex-v1`) và 25 câu xung đột (`dryrun-conflict-v1`); thêm bộ tình huống 44 câu (có tách vấn đề).
- Prompt và tham số được chốt trước khi chạy và chạy một lần, không dò trên kết quả.

### 7.2 Kết quả truy xuất

| So sánh | Bộ | R@5 | T@2000 |
|---|---|---|---|
| Chọn bằng LLM so với ĐK3 không đồ thị | Trộn (80 câu có nhãn) | +0,035 [+0,008; +0,064], 14/4 | +0,066 [+0,039; +0,096], 19/1 |
| Chọn bằng LLM so với ĐK2 | Trộn | +0,049 [+0,014; +0,087], 17/7 | +0,079 [+0,040; +0,122], 21/4 |
| Chọn bằng LLM so với ĐK3-chain (quy tắc, mục 6) | Trộn | +0,038 [+0,009; +0,069], 17/5 | +0,043 [+0,018; +0,071], 15/2 |
| Chọn bằng LLM so với ĐK3 không đồ thị | Tình huống (44) | +0,023 [-0,014; +0,062] | +0,060 [+0,016; +0,107], 15/5 |
| Chọn bằng LLM so với ĐK2 | Tình huống | +0,033 [-0,009; +0,075] | +0,059 [+0,007; +0,114], 17/7 |

Tách theo mức độ câu hỏi (bộ trộn, T@2000):

| Mức | Số câu | ĐK3 không đồ thị | Chọn bằng LLM | Không chọn gì | Đơn vị được chọn trúng đáp án |
|---|---|---|---|---|---|
| Phức tạp | 55 | 0,564 | 0,660 | 16/55 | 22/81 (27%) |
| Đơn giản | 25 | 0,960 | 0,960 | 18/25 | 0/9 |
| Ngoài phạm vi | 5 | không có nhãn | không có nhãn | 3/5 | không áp dụng |
| Tình huống | 44 | 0,331 | 0,391 | 1/44 | 21/126 (17%) |

### 7.3 Nhận định

- Đây là lần đầu đồ thị cho cải thiện rõ ở tầng truy xuất: +0,06 đến +0,08 recall trong 2.000 token, khoảng tin cậy không chứa 0 trên cả hai bộ, và tốt hơn cả ĐK2 lẫn mở rộng bằng quy tắc.
- Lợi ích tập trung ở câu phức tạp (+0,096 trên 55 câu); câu đơn giản không bị ảnh hưởng vì model thường không chọn gì (18/25) và đoạn được chọn chỉ chen sau đoạn đã đúng.
- So với quy tắc ở mục 6 (trúng khoảng 6-10%), model chọn trúng 17-27%: chỗ nghẽn đúng là việc chọn láng giềng, không phải đồ thị.
- Điểm cần sửa: 2/5 câu ngoài phạm vi vẫn được chọn láng giềng; 7/25 câu đơn giản được chọn thêm đoạn không cần.

### 7.4 Giới hạn

- Nhãn đáp án do model soạn, chưa có người duyệt; nhãn của `dryrun-v1` và `dryrun-complex-v1` soạn trên corpus v1 (94 Điều), nên có thể thiếu các đơn vị chỉ có ở corpus v2 (ví dụ chế tài trong NĐ 12/2022), làm tỉ lệ "trúng" ở mục 7.2 thấp hơn thực tế.
- Recall mới là tầng truy xuất; chưa đo câu trả lời.
- Thêm một lượt gọi model cho mỗi câu (Haiku); cần ghi chi phí và độ trễ khi so sánh.
- Model chọn được thấy văn bản rút gọn của các đoạn; lựa chọn của nó không được người kiểm tra.

### 7.5 Bước tiếp theo đề xuất

1. Đo ở tầng câu trả lời: cùng bộ trộn và bộ tình huống, sinh câu trả lời bằng Haiku cho ĐK3 không đồ thị và cho bản chọn bằng LLM (có `relations`), chấm bằng Sonnet `judge-v2`.
2. Nếu câu trả lời cũng tốt hơn, đưa bước chọn láng giềng thành một điều kiện chính thức (ví dụ ĐK3-graph, ĐK4-graph), chốt prompt và tham số, đo lại trên held-out có nhãn người.

### 7.6 Ngân sách ngữ cảnh

Recall theo ngân sách token (offline trên các lượt ở mục 7.2; danh sách xếp hạng giữ khoảng 7.000-8.000 token nên 6.000 là mức cao nhất đo được):

| Bộ, nhóm | Điều kiện | 1.000 | 2.000 | 3.000 | 4.000 | 6.000 |
|---|---|---|---|---|---|---|
| Trộn, phức tạp (55) | ĐK2 | 0,50 | 0,56 | 0,63 | 0,70 | 0,76 |
| Trộn, phức tạp | ĐK3 không đồ thị | 0,46 | 0,56 | 0,62 | 0,68 | 0,75 |
| Trộn, phức tạp | Chọn bằng LLM | 0,51 | 0,66 | 0,70 | 0,75 | 0,79 |
| Trộn, đơn giản (25) | mọi điều kiện | 0,92 | 0,92-0,96 | 0,96 | 0,96 | 0,96 |
| Tình huống (44) | ĐK2 | 0,25 | 0,33 | 0,42 | 0,47 | 0,53 |
| Tình huống | ĐK3 không đồ thị | 0,22 | 0,33 | 0,41 | 0,46 | 0,52 |
| Tình huống | Chọn bằng LLM | 0,23 | 0,39 | 0,46 | 0,49 | 0,55 |

- Câu phức tạp cần nhiều ngữ cảnh hơn hẳn câu đơn giản; câu đơn giản bão hòa từ 1.000-2.000 token.
- Lợi ích của chọn láng giềng giảm khi ngân sách tăng (khoảng +0,10 ở 2.000 token, +0,03 ở 6.000 token với câu phức tạp): giá trị của đồ thị là đạt cùng lượng căn cứ với ít token hơn (chọn bằng LLM ở 2.000 token ngang ĐK2 ở khoảng 3.000-4.000 token).
- Tăng ngân sách không bù được phần căn cứ nằm ngoài tầm cả tìm kiếm lẫn đồ thị (bộ tình huống chỉ đạt 0,55 ở 6.000 token).
- Trong thí nghiệm chính, mọi điều kiện dùng cùng ngân sách; báo cáo thêm đường cong theo nhiều mức ngân sách.

Ngân sách thích ứng (đã cài, offline): `shared.adaptive_budget` và `context_token_budget` của answer run nhận `{"base", "per_issue", "max"}`; số vấn đề lấy từ lượt tách vấn đề dùng chung, không từ nhãn, nên cùng một quy tắc cho mọi điều kiện.
Thử quy tắc 1.500 + 700 token mỗi vấn đề, tối đa 6.000, trên bộ tình huống (2-4 vấn đề mỗi câu, ngân sách trung bình 3.886 token):

| Điều kiện | Cố định 3.000 | Thích ứng |
|---|---|---|
| ĐK2 | 0,422 | 0,471 |
| ĐK3 không đồ thị | 0,406 | 0,453 |
| Chọn bằng LLM | 0,456 | 0,487 |

Chọn bằng LLM so với ĐK3 không đồ thị ở ngân sách thích ứng: +0,034 [+0,003; +0,065], 11/3; so với ĐK2: +0,017 [-0,028; +0,060].
Phần tăng chung chủ yếu do ngân sách trung bình lớn hơn 3.000; trên bộ tình huống mọi câu đều có 2-4 vấn đề nên quy tắc ít phân biệt.
Bộ trộn chưa có lượt tách vấn đề (cần một lượt gọi model), nên chưa đo được việc quy tắc này cho câu đơn giản ít token hơn.

## 8. Chọn láng giềng theo từng vấn đề và bằng Sonnet (11/11/2026)

### 8.1 Thay đổi

- `neighbor-select-v2` (`cli neighbor-select --grouping issue`, prompt `prompts/neighbor-select-v2.md`): mỗi vấn đề đã tách có đoạn gốc riêng (2 đoạn đầu khi tìm bằng câu tìm kiếm của vấn đề, cùng cách xếp hạng của lượt gốc), ứng viên riêng (tối đa 8, không trùng giữa các vấn đề) và được trình bày theo nhóm V1, V2...; model chọn tối đa 2 đoạn mỗi vấn đề, tổng tối đa 4; vẫn một lượt gọi mỗi câu hỏi.
- Bộ trộn được tách vấn đề bằng Claude Sonnet 5.5 (`experiments/runs/mixed-select-v1/decompose-sonnet`, 85 lượt; `cli decompose-questions --claude-model`), vì trước đó chưa có lượt tách; bộ tình huống giữ lượt tách gpt-oss-120b cũ.
- Lượt gọi (được duyệt ngày 11/11, cho phép dùng Sonnet khi cần): Sonnet tách vấn đề 85; Haiku chọn láng giềng 84 (v1 trên gốc đã tách) + 85 (v2) + 44 (v2 bộ tình huống); Sonnet chọn láng giềng 85 + 44 (v2); 0 lỗi.

### 8.2 Kết quả

Bộ trộn, gốc ĐK3 không đồ thị có tách vấn đề (80 câu có nhãn):

| So sánh | R@5 | T@2000 |
|---|---|---|
| Tách vấn đề so với không tách (ĐK3 không đồ thị) | +0,136 [+0,083; +0,194], 29/4 | +0,182 [+0,129; +0,238], 36/1 |
| Haiku v1 so với gốc đã tách | -0,022 [-0,056; +0,009] | +0,014 [-0,010; +0,041] |
| Haiku v2 so với gốc đã tách | -0,030 [-0,063; -0,002] | +0,017 [-0,008; +0,043] |
| Sonnet v2 so với gốc đã tách | -0,013 [-0,040; +0,010] | +0,012 [-0,008; +0,033] |

Bộ tình huống (44 câu, gốc ĐK3 không đồ thị có tách vấn đề):

| So sánh | R@5 | T@2000 |
|---|---|---|
| Haiku v1 (mục 7) so với gốc | +0,023 [-0,014; +0,062] | +0,060 [+0,016; +0,107], 15/5 |
| Haiku v2 so với gốc | +0,033 [+0,001; +0,064], 10/3 | +0,088 [+0,036; +0,142], 17/3 |
| Sonnet v2 so với gốc | +0,052 [+0,023; +0,082], 12/1 | +0,092 [+0,049; +0,138], 16/1 |
| Haiku v2 so với Haiku v1 | +0,010 [-0,017; +0,035] | +0,028 [-0,011; +0,066], 11/5 |
| Sonnet v2 so với Haiku v2 | +0,019 [+0,005; +0,039], 4/0 | +0,005 [-0,026; +0,035] |

Độ chính xác của lựa chọn (đơn vị được chọn trúng đáp án):

| Bộ | Haiku v1 | Haiku v2 | Sonnet v2 |
|---|---|---|---|
| Tình huống | 22/126 (17%) | 26/123 (21%) | 25/83 (30%) |
| Trộn, câu phức tạp | 15/101 (15%) | 13/101 (13%) | 11/68 (16%) |
| Trộn, câu đơn giản: số câu không chọn gì | 17/25 | 20/25 | 22/25 |

### 8.3 Nhận định

- Tách vấn đề là bước có tác dụng lớn nhất từ trước tới nay trên bộ trộn (+0,18 recall ở 2.000 token).
  Sau khi tách, ngữ cảnh câu phức tạp đã chứa 81% đơn vị đáp án, nên chọn láng giềng gần như không còn chỗ để thêm (+0,01 đến +0,02, không có ý nghĩa thống kê).
- Trên bộ tình huống (vụ việc thật, khó hơn, ngữ cảnh gốc chỉ chứa 33% đáp án), chọn láng giềng vẫn có ích rõ: bản theo từng vấn đề +0,088 (Haiku) và +0,092 (Sonnet), cao hơn bản v1 (+0,060); riêng phần v2 so với v1 (+0,028) chưa có ý nghĩa thống kê.
- Sonnet chọn ít hơn và chính xác hơn (30% so với 21% trên bộ tình huống), tốt hơn ở đầu danh sách (R@5 4/0 câu thắng/thua so với Haiku v2), còn ở 2.000 token thì ngang nhau.
- Câu đơn giản không bị ảnh hưởng ở mọi biến thể; bản v2 và Sonnet ít chọn thừa hơn (20/25 và 22/25 câu không chọn gì).
- Kết luận tạm: đồ thị có giá trị khi tìm kiếm (kể cả sau khi tách vấn đề) còn bỏ sót nhiều, như vụ việc thật; khi tìm kiếm đã gần đủ thì đồ thị chỉ là phần dự phòng rẻ (không làm hại câu đơn giản).

### 8.4 Giới hạn riêng của lượt này

- Câu hỏi bộ xung đột và bộ phức tạp do Claude soạn kèm nhãn; tách vấn đề bằng Sonnet (cùng họ model) có thể khớp với cách soạn nhãn hơn mức thực tế, nên mức +0,18 của bước tách trên bộ trộn có thể bị thổi phồng; bộ tình huống dùng gpt-oss để tách nên không bị ảnh hưởng này.
- Bộ trộn và bộ tình huống dùng hai model tách vấn đề khác nhau; chỉ so sánh trong cùng một bộ.
- Các giới hạn ở mục 7.4 (nhãn chưa duyệt, nhãn soạn trên corpus v1) vẫn áp dụng.

## 9. Đo ở tầng câu trả lời (bộ tình huống, 11/11/2026)

### 9.1 Thiết lập

- Hai lượt trả lời bằng Claude Haiku 5.5 trên 44 câu tình huống, cùng ngân sách 3.000 token:
  - gốc: ĐK3 không đồ thị, có tách vấn đề, prompt `answer-v2` (`experiments/runs/dryrun-cases-v1/answers-haiku-dk3-nograph`);
  - đồ thị: láng giềng do Sonnet chọn theo từng vấn đề (mục 8), kèm dòng quan hệ giữa các đoạn, prompt `answer-v3` (`answers-haiku-select-sonnet-v2`, cấu hình `configs/experiments/answer-chain-haiku.json`).
- Giám khảo Sonnet 5.5 chấm mù theo `judge-v2` (`judge-select/`), không biết đoạn nào thuộc lượt nào.
- Lượt gọi (được duyệt ngày 11/11): 88 Haiku, 88 Sonnet, 0 lỗi.
- Hai lượt khác nhau ở cả ngữ cảnh lẫn prompt (v3 thêm dòng quan hệ và thứ tự xét quy định gốc, ngoại lệ, chế tài); chưa tách riêng tác dụng của prompt.

### 9.2 Kết quả

| Chỉ số | Gốc | Đồ thị | Chênh [KTC 95%] | Thắng/thua |
|---|---|---|---|---|
| Trích dẫn trúng đơn vị đáp án (recall, tự động) | 0,401 | 0,473 | +0,072 [+0,042; +0,104] | 15/0 |
| Trích dẫn theo ký tự (precision, tự động) | 0,238 | 0,251 | +0,013 | |
| Độ đúng (giám khảo) | 0,398 | 0,409 | +0,011 [-0,023; +0,057] | 2/1 |
| Khớp kết luận chuẩn | 0,398 | 0,420 | +0,023 [-0,034; +0,080] | 5/3 |
| Vấn đề giải quyết được | 0,482 | 0,513 | +0,031 [-0,013; +0,075] | 15/10 |
| Tỉ lệ phát biểu sai luật (thấp là tốt) | 0,126 | 0,096 | -0,030 [-0,069; +0,009] | |
| Câu trả lời không có lỗi luật | 0,432 | 0,545 | +0,114 [-0,068; +0,295] | 11/6 |
| Phát biểu có căn cứ đầy đủ | 0,562 | 0,540 | -0,021 [-0,093; +0,053] | |
| Trích dẫn đúng | 0,932 | 0,932 | 0,000 | |

### 9.3 Nhận định

- Phần thêm căn cứ chuyển được vào câu trả lời: câu trả lời trích dẫn trúng nhiều đơn vị đáp án hơn (+7,2 điểm phần trăm, 15 câu tốt hơn, 0 câu kém hơn), khớp với mức tăng ở tầng truy xuất (+8,8 điểm ở 2.000 token).
- Các chỉ số của giám khảo đều nghiêng về phía đồ thị (kết luận, vấn đề giải quyết được, ít lỗi luật hơn) nhưng không chỉ số nào có ý nghĩa thống kê với 44 câu; mức chênh nằm trong dao động đã biết của việc sinh lại và của giám khảo (khoảng ±0,07, mục 2.1).
- Độ đúng tuyệt đối vẫn thấp ở cả hai lượt (khoảng 0,40), như các lần trước: giới hạn chính vẫn là corpus thiếu văn bản tòa đã dùng và nhãn chưa đủ, không phải cách chọn căn cứ.
- Kết luận: hướng tách vấn đề + đồ thị + LLM chọn láng giềng cải thiện chắc chắn ở tầng căn cứ (truy xuất và trích dẫn); ở tầng chất lượng câu trả lời mới có xu hướng tích cực, cần bộ câu lớn hơn có nhãn người (khoảng 150 câu, sinh câu trả lời hai lần mỗi câu) để khẳng định.

## 10. So sánh với ĐK1 và ĐK2 (bộ tình huống)

Cùng lượt tách vấn đề, model trả lời Claude Haiku 5.5, prompt cùng phiên bản trừ cột cuối (`answer-v3`), ngân sách 3.000 token, giám khảo Sonnet `judge-v2`; ĐK1, ĐK2 chấm ngày 09-10/11 (`judge-v2/`), hai cột sau chấm ngày 11/11 (`judge-select/`), cùng prompt giám khảo.

| Chỉ số | ĐK1 (đoạn 384 token) | ĐK2 | ĐK3 không đồ thị | Đồ thị + chọn láng giềng (Sonnet, theo vấn đề) |
|---|---|---|---|---|
| Recall truy xuất trong 2.000 token | 0,423 | 0,331 | 0,331 | 0,423 |
| Câu trả lời trích trúng đơn vị đáp án | 0,485 | 0,417 | 0,401 | 0,473 |
| Trích dẫn theo ký tự (precision) | 0,092 | 0,244 | 0,238 | 0,251 |
| Khớp kết luận chuẩn | 0,352 | 0,398 | 0,398 | 0,420 |
| Vấn đề giải quyết được | 0,522 | 0,477 | 0,482 | 0,513 |
| Tỉ lệ phát biểu sai luật | 0,119 | 0,141 | 0,126 | 0,096 |
| Độ đúng | 0,386 | 0,420 | 0,398 | 0,409 |

Chênh lệch theo cặp của cột cuối:

- So với ĐK2: truy xuất +0,092 [+0,040; +0,144], 20/5; trích trúng đáp án +0,056 [0,000; +0,112], 19/9; phát biểu sai luật -0,046 [-0,084; -0,008], 7/20 (ít lỗi hơn ở 20 câu); kết luận +0,023, vấn đề +0,036, độ đúng -0,011, đều không có ý nghĩa thống kê.
- So với ĐK1: truy xuất 0,000 [-0,078; +0,079]; trích trúng đáp án -0,012 [-0,092; +0,072]; precision trích dẫn theo ký tự 0,251 so với 0,092; kết luận +0,068 [-0,011; +0,148], 9/3; độ đúng +0,023; phát biểu sai luật -0,024; đều không có ý nghĩa thống kê trừ precision.

Nhận định: hướng mới tốt hơn ĐK2 ở tầng căn cứ và ít lỗi luật hơn; so với ĐK1, lượng căn cứ tìm được ngang nhau (đoạn 384 token chạm nhiều đơn vị nên recall theo đơn vị có lợi cho ĐK1) nhưng trích dẫn chính xác gấp khoảng 2,7 lần, đúng yêu cầu truy vết của đề tài; chưa có bằng chứng câu trả lời đúng hơn ĐK1 hay ĐK2.
Hai lượt chấm khác ngày thêm một phần nhiễu; báo cáo chính phải chấm mọi điều kiện trong cùng một lượt, trên bộ câu có nhãn người.

## 11. Hướng tiếp theo

1. Tìm theo đơn vị nhỏ, đưa ngữ cảnh rộng (câu dẫn và các Khoản cùng Điều) để lấy ưu điểm phủ của ĐK1 mà giữ trích dẫn chính xác; offline.
2. Bổ sung văn bản còn thiếu (văn bản tòa đã dùng, văn bản thay thế NĐ 12/2022) và lọc theo hiệu lực tại thời điểm vụ việc.
3. Bước kiểm tra câu trả lời: model thứ hai đối chiếu từng phát biểu với đoạn được trích, gắn cờ phát biểu không được hỗ trợ hoặc thiếu ngoại lệ, điều kiện.
4. Chọn láng giềng chính xác hơn (toàn văn ứng viên, láng giềng hai bước, reranker cục bộ nếu được duyệt).
5. Bộ khoảng 150 câu có nhãn người, chạy mọi điều kiện trong cùng một lượt chấm, mỗi câu sinh hai lần, đo đồng thuận giám khảo với người; dừng thêm biến thể từ 25/11.
