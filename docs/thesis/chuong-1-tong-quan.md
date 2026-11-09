# Chương 1. Tổng quan

> Bản nháp ngày 09/11/2026, viết từ đề cương, nhật ký quyết định và tài liệu tổng quan của dự án.
> Các chỗ đánh dấu **[cập nhật]** chờ số liệu thực nghiệm hoặc ý kiến của giảng viên hướng dẫn.

Tên đề tài: **Nghiên cứu và xây dựng hệ thống hỏi đáp pháp luật dựa trên RAG với Legal Knowledge Base có cấu trúc và kiểm chứng**.

Tên tiếng Anh: **Research and Development of a Legal Question Answering System Based on RAG with a Structured and Verifiable Legal Knowledge Base**.

Chương này trình bày lý do chọn đề tài, bài toán cần giải quyết, mục tiêu, câu hỏi nghiên cứu và giả thuyết, đối tượng và phạm vi, đóng góp chính và cấu trúc của đồ án.

## 1.1. Lý do chọn đề tài

Quá trình số hóa văn bản pháp luật giúp việc tra cứu thuận tiện hơn, nhưng người dùng vẫn phải làm việc với một khối lượng văn bản lớn, có cấu trúc phân cấp, nhiều dẫn chiếu và thay đổi theo thời gian.
Trong lĩnh vực lao động, một vấn đề cụ thể thường không nằm gọn trong một văn bản: Bộ luật Lao động nêu nguyên tắc, nghị định hướng dẫn chi tiết, thông tư quy định biểu mẫu, và các văn bản sửa đổi, bổ sung làm thay đổi nội dung theo từng thời điểm.

Người dùng mà đề tài hướng tới là nhân viên pháp chế và nhân sự trong doanh nghiệp.
Họ cần câu trả lời nhanh cho những câu hỏi thường ngày như thời gian thử việc tối đa, thời hạn báo trước khi chấm dứt hợp đồng, hay cách tính tiền lương làm thêm giờ.
Điều họ cần không chỉ là một câu trả lời, mà là câu trả lời **có căn cứ**: chỉ ra đúng Điều, Khoản, Điểm và nguyên văn của quy định để tự kiểm tra lại trước khi áp dụng.

Các mô hình ngôn ngữ lớn (LLM) có thể trả lời câu hỏi bằng ngôn ngữ tự nhiên, nhưng khi không có nguồn đối chiếu chúng dễ trả lời thiếu căn cứ, nhầm điều khoản hoặc dẫn nguồn không tồn tại.
Kiến trúc Retrieval-Augmented Generation (RAG) giảm bớt vấn đề này bằng cách cho mô hình đọc các đoạn văn bản tìm được trước khi trả lời.
Tuy nhiên, chất lượng của RAG vẫn phụ thuộc nhiều vào cách dữ liệu pháp lý được tổ chức và biểu diễn: một đoạn văn bản bị cắt ngang giữa hai Điều, hay một quy định bị tách khỏi câu dẫn chứa điều kiện áp dụng, đều có thể dẫn tới câu trả lời sai mà vẫn có vẻ "có nguồn".

Xuất phát từ thực tế đó, đề tài nghiên cứu việc xây dựng một kho tri thức pháp luật (Legal Knowledge Base) **có cấu trúc, có bằng chứng nguyên văn và có cơ chế kiểm chứng**, rồi khai thác kho này trong hệ thống RAG để hỏi đáp pháp luật lao động tiếng Việt.

## 1.2. Phát biểu bài toán

Đầu vào của hệ thống là một câu hỏi bằng tiếng Việt về pháp luật lao động và một tập văn bản pháp luật đã được thu thập, chuẩn hóa và khóa phiên bản.
Đầu ra là một câu trả lời gồm các phát biểu, mỗi phát biểu kèm trích dẫn tới đoạn nguyên văn trong văn bản gốc; khi các đoạn tìm được không đủ căn cứ, hệ thống phải nói rõ là không đủ căn cứ thay vì suy đoán.

Bài toán được chia thành ba phần gắn với ba câu hỏi nghiên cứu:

- **Trích xuất tri thức**: biến câu luật thành các bản ghi có cấu trúc (quy phạm: chủ thể, hành vi, tính quy phạm, điều kiện, hệ quả...), mỗi thông tin là một đoạn chép nguyên văn kèm vị trí ký tự trong văn bản.
- **Kiểm chứng tri thức**: tự động phát hiện và loại các bản ghi sai lược đồ, tham chiếu không tồn tại, trích dẫn không khớp văn bản gốc hoặc từ tình thái mâu thuẫn, trước khi đưa vào kho.
- **Truy xuất và sinh câu trả lời**: tìm các bản ghi liên quan tới câu hỏi và sinh câu trả lời có trích dẫn, trong đó mọi trích dẫn đều phải thuộc tập đoạn đã cung cấp cho mô hình.

Một ràng buộc xuyên suốt là **khả năng truy vết**: mọi thông tin trong kho và mọi trích dẫn trong câu trả lời đều phải truy được về một đoạn trích chính xác, với vị trí ký tự Unicode và mã băm SHA-256 của văn bản đã chuẩn hóa.
Tri thức do máy tạo ra luôn ở trạng thái chờ duyệt cho tới khi người duyệt quyết định, và không được trình bày như sự thật pháp lý đã xác minh.

## 1.3. Mục tiêu

**Mục tiêu tổng quát.**
Nghiên cứu và xây dựng hệ thống hỏi đáp pháp luật dựa trên RAG, trong đó kho tri thức pháp luật được tổ chức có cấu trúc và có cơ chế kiểm chứng, nhằm cung cấp câu trả lời có căn cứ và kèm nguồn bằng chứng.

**Mục tiêu cụ thể.**

1. Thu thập, chuẩn hóa và tách cấu trúc (Chương, Mục, Điều, Khoản, Điểm) một tập văn bản pháp luật lao động, lưu kèm nguồn, ngày truy cập, trạng thái hiệu lực và mã băm để tái lập được.
2. Thiết kế lược đồ tri thức lấy quy phạm làm trung tâm, ánh xạ được sang thực thể và quan hệ như đề cương yêu cầu.
3. Xây dựng pipeline trích xuất tri thức bằng quy tắc (baseline) và bằng LLM với đầu ra có cấu trúc.
4. Xây dựng bộ kiểm chứng tự động dựa trên bằng chứng và các ràng buộc về lược đồ, tham chiếu, từ tình thái và trùng lặp.
5. Xây dựng hệ thống truy xuất và sinh câu trả lời có trích dẫn, cùng ứng dụng web cho người duyệt và người tra cứu.
6. Xây dựng bộ câu hỏi đánh giá và gold set, rồi đo ảnh hưởng của cách tổ chức và kiểm chứng tri thức tới chất lượng hệ thống qua bốn điều kiện đối chứng ĐK1-ĐK4.

## 1.4. Câu hỏi nghiên cứu và giả thuyết

| Mã | Câu hỏi nghiên cứu | Thiết lập so sánh |
|---|---|---|
| RQ1 | AI có thể trích xuất và cấu trúc hóa thực thể và quan hệ pháp lý theo lược đồ với độ chính xác ở mức nào? | Baseline theo quy tắc so với LLM có đầu ra cấu trúc, trên cùng gold set |
| RQ2 | Các cơ chế kiểm chứng dựa trên bằng chứng và tính nhất quán phát hiện và loại được bao nhiêu lỗi trong tri thức do AI tạo ra, và còn sót lại ở mức nào? | Kho chưa kiểm chứng (ĐK3) so với kho đã kiểm chứng tự động (ĐK4); chèn lỗi có chủ đích |
| RQ3 | Chất lượng của kho tri thức ảnh hưởng như thế nào tới khả năng truy xuất và chất lượng câu trả lời của hệ thống RAG? | ĐK1-ĐK4 trên cùng bộ câu hỏi đã khóa, gồm cả tập held-out |

Giả thuyết nghiên cứu của đề tài là: kho tri thức pháp luật được tổ chức có cấu trúc và qua kiểm chứng giúp **giảm lỗi trích dẫn và tăng mức độ bám nguồn** của câu trả lời so với RAG trên văn bản thô.
Thực nghiệm nhằm kiểm tra giả thuyết này, và kết quả được báo cáo trung thực kể cả khi không ủng hộ giả thuyết.

Bốn điều kiện đối chứng được thiết kế để mỗi bậc chỉ thay đổi một yếu tố:

| Điều kiện | Nguồn tri thức cho RAG | Mục đích so sánh |
|---|---|---|
| ĐK1 | Văn bản gốc, chia đoạn theo độ dài cố định | Baseline |
| ĐK2 | Văn bản chia theo cấu trúc Chương, Điều, Khoản, Điểm, kèm thông tin nguồn | Tác động của việc tôn trọng cấu trúc văn bản |
| ĐK3 | Kho tri thức do LLM trích xuất theo lược đồ, chưa kiểm chứng | Tác động của biểu diễn tri thức có cấu trúc |
| ĐK4 | Kho tri thức sau kiểm chứng tự động | Tác động của kiểm chứng tri thức (so với ĐK3) |

Cách biểu diễn cụ thể của bản ghi ĐK3 và ĐK4 khi truy xuất là một mục còn mở, được trình bày ở Chương 4 **[cập nhật]**.

## 1.5. Đối tượng và phạm vi

**Đối tượng nghiên cứu.**
Các phương pháp AI, NLP và LLM hỗ trợ xây dựng kho tri thức pháp luật và hệ thống hỏi đáp pháp luật dựa trên RAG.

**Phạm vi dữ liệu.**
Pháp luật lao động Việt Nam, lấy từ Cơ sở dữ liệu quốc gia về văn bản pháp luật (vbpl.vn).
Phạm vi thực nghiệm gồm 5 văn bản và 94 Điều thuộc các nhóm chủ đề cốt lõi:

| Văn bản | Chủ đề chính trong phạm vi |
|---|---|
| Bộ luật Lao động 45/2019/QH14 | Định nghĩa, hợp đồng, thử việc, chấm dứt hợp đồng, tiền lương, thời giờ làm việc và nghỉ ngơi, kỷ luật, hiệu lực |
| Nghị định 145/2020/NĐ-CP | Hướng dẫn hợp đồng, tiền lương làm thêm giờ, kỷ luật |
| Nghị định 293/2025/NĐ-CP | Lương tối thiểu vùng |
| Thông tư 10/2020/TT-BLĐTBXH | Nội dung hợp đồng lao động |
| Nghị định 12/2022/NĐ-CP | Xử phạt vi phạm về thử việc và tiền lương |

Phạm vi này có 617 đơn vị (287 khoản, 213 điểm) và được khóa thành một phiên bản corpus duy nhất dùng chung cho bộ câu hỏi, gold set và mọi lượt chạy.
Đề cương dự kiến 8-12 văn bản với 60-100 điều khoản; số Điều nằm trong khoảng dự kiến, còn số văn bản được thu hẹp để vừa sức gán nhãn của hai thành viên.
Điều chỉnh này được ghi trong nhật ký quyết định của dự án.

**Phạm vi chức năng.**
Xây dựng và kiểm chứng tri thức; truy xuất tri thức; hỏi đáp có trích dẫn; ứng dụng web có phân vai trò (người tra cứu, người duyệt, quản trị, giám sát) và các công cụ gán nhãn phục vụ nghiên cứu.

**Ngoài phạm vi.**

- Pháp luật nước ngoài, dữ liệu mật hoặc nội bộ, và tư vấn pháp lý toàn diện; hệ thống không thay thế tư vấn pháp lý chuyên nghiệp.
- Suy luận tổng quát theo thời điểm áp dụng: trạng thái hiệu lực được lưu như thuộc tính của văn bản, và hệ thống không tự suy ra hiệu lực hiện hành.
- Phát hiện mâu thuẫn ngữ nghĩa giữa các văn bản: bộ kiểm chứng hiện chỉ kiểm lược đồ, toàn vẹn, nguyên văn, từ tình thái và trùng lặp.

## 1.6. Đóng góp chính

1. **Một lược đồ tri thức pháp luật có bằng chứng tới từng ô**: mỗi quy phạm gồm tính quy phạm và các ô (chủ thể, hành vi, đối tượng, điều kiện, ngoại lệ, thời hạn, định lượng, hệ quả...), mỗi ô là một đoạn chép nguyên văn từ câu luật kèm vị trí ký tự, nên máy kiểm tra được chữ nào không có thật.
2. **Một pipeline trích xuất và kiểm chứng tái lập được**: dữ liệu khóa phiên bản, cấu hình và câu trả lời thô của mô hình được lưu theo từng lượt chạy, kho ĐK3 và ĐK4 được dựng lại tất định từ đầu ra đã lưu.
3. **Một thiết kế thực nghiệm bốn bậc có kiểm tra công bằng tự động**: công cụ `preflight` xác nhận các điều kiện dùng chung corpus, bộ câu hỏi, cấu hình truy xuất và cấu hình sinh câu trả lời trước khi báo cáo.
4. **Bộ dữ liệu đánh giá cho pháp luật lao động tiếng Việt**: bộ câu hỏi v1 (152 câu, có nhóm diễn đạt lại và câu ngoài phạm vi), gold set trích xuất trên 40 Điều, bảng kiểm tra quy phạm bị loại, tất cả do hai thành viên gán nhãn độc lập và đối soát.
5. **Một ứng dụng web cho người dùng thật**: người duyệt nhập văn bản, duyệt từng quy phạm và công bố kho theo phiên bản bất biến; người tra cứu hỏi đáp trên các kho đã công bố, và chỉ bằng chứng của quy phạm đã được duyệt mới được dùng để trả lời.

## 1.7. Cấu trúc đồ án

| Chương | Nội dung |
|---|---|
| Chương 1 | Tổng quan: lý do chọn đề tài, bài toán, mục tiêu, câu hỏi nghiên cứu, phạm vi và đóng góp |
| Chương 2 | Cơ sở lý thuyết và nghiên cứu liên quan: RAG, truy xuất từ khóa và ngữ nghĩa, trích xuất thông tin bằng LLM, cấu trúc quy phạm pháp luật, kho tri thức, các phương pháp đánh giá |
| Chương 3 | Phân tích và xây dựng hệ thống: dữ liệu, lược đồ tri thức, công nghệ, trích xuất, kiểm chứng, kho tri thức, truy xuất và sinh câu trả lời, ứng dụng web |
| Chương 4 | Thực nghiệm và đánh giá: bộ câu hỏi và gold set, độ tin cậy của nhãn, các điều kiện ĐK1-ĐK4, kết quả RQ1-RQ3, phân tích lỗi và các mối đe dọa tới tính hợp lệ |
| Chương 5 | Kết luận, hạn chế và hướng phát triển |

## Tóm tắt chương

Đề tài giải quyết bài toán hỏi đáp pháp luật lao động tiếng Việt có căn cứ, bằng cách tổ chức văn bản luật thành kho quy phạm có cấu trúc, có bằng chứng nguyên văn và được kiểm chứng trước khi dùng cho RAG.
Ba câu hỏi nghiên cứu đo lần lượt chất lượng trích xuất, hiệu quả kiểm chứng và ảnh hưởng của kho tri thức tới truy xuất và câu trả lời, qua bốn điều kiện đối chứng chỉ khác nhau ở cách tổ chức tri thức.
Chương 2 trình bày cơ sở lý thuyết cho các thành phần này.
