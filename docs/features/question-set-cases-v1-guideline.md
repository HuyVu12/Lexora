# Hướng dẫn gán nhãn bộ tình huống v1

Bộ tình huống gắn với corpus "Phạm vi thực nghiệm v2" (`ve5261858b8f3`, toàn văn 9 văn bản lao động, bảo hiểm và an toàn lao động, 711 Điều).
Đây là bộ đánh giá chính của RQ3 cho loại câu hỏi mà người làm pháp chế và nhân sự thực sự gặp: một tình huống có nhiều vấn đề pháp lý cùng lúc.
Kết quả được báo cáo riêng, không gộp với bộ câu hỏi v1 (chủ yếu tra cứu một quy định) hay bộ phức tạp v1.

## Nguồn tình huống

44 câu (38 câu gốc và 6 câu diễn đạt lại) do model soạn nháp từ 38 vụ việc thật trong `experiments/case-research-v1/cases.json`.
Các vụ việc lấy từ bản án đã công bố trên trang công bố bản án của Tòa án nhân dân, án lệ, và báo chí đưa tin tranh chấp lao động.
Mọi tình tiết đã được ẩn danh: không có tên người, tên doanh nghiệp, số giấy tờ; chỉ giữ số bản án hoặc tên bài báo làm nguồn.
Mỗi câu ghi `case_id`, `source_ref`, danh sách vấn đề (`issues`) và kết quả tham chiếu (`reference_outcome`): tòa đã quyết định thế nào, hoặc báo chí đưa tin thế nào.
Kết quả tham chiếu chỉ để đối chiếu khi chấm, không phải đáp án bắt buộc, vì câu hỏi đã được đặt lại theo luật hiện hành.

## Cách đặt câu hỏi

Câu hỏi được viết như người làm nhân sự hoặc pháp chế hỏi khi vụ việc đang diễn ra: công ty có được làm không, phải làm thủ tục gì, phải trả những khoản gì, rủi ro là gì.
Vụ việc xảy ra khi Bộ luật Lao động 2012 hoặc Luật Bảo hiểm xã hội 2014 còn hiệu lực đã được đặt lại như xảy ra hôm nay; kết quả tham chiếu của những vụ này có ghi "(theo luật cũ)".
Tám vụ không dùng: vấn đề chính thuộc tố tụng hoặc luật không có trong corpus (trọng tài thương mại, thời hiệu và phạm vi xét xử), hoặc trùng gần như hoàn toàn với một vụ khác đã dùng.

## Cách gán nhãn

Các trường và quy tắc giống hướng dẫn bộ v1 (`question-set-v1-guideline.md`), với những điểm sau:

- Chọn **đủ** các đơn vị cần cho **mọi** vấn đề của câu hỏi, mỗi đơn vị là điểm hoặc khoản nhỏ nhất chứa căn cứ; thường 3 đến 6 đơn vị, có thể ở nhiều văn bản.
- Căn cứ theo văn bản trong corpus v2, kể cả khi bản án gốc viện dẫn điều luật cũ; ví dụ vụ năm 2017 về sa thải lao động nữ mang thai thì chọn Điều 122, Điều 137 Bộ luật Lao động 2019 và Điều 70 Nghị định 145/2020.
- Nếu một vấn đề cần văn bản không có trong corpus (Bộ luật Dân sự, Bộ luật Tố tụng dân sự, Luật Công đoàn, Luật Doanh nghiệp), vẫn gán `answer` cho phần có căn cứ và ghi chú phần thiếu.
- Nghị định 12/2022 đã hết hiệu lực từ 10/09/2026; đơn vị của nghị định này chỉ dùng khi câu hỏi hỏi về hành vi xảy ra lúc nghị định còn hiệu lực, và ghi chú điều đó.
- Nếu bản án tự viện dẫn sai điểm, khoản (ví dụ tự ý bỏ việc 05 ngày ghi điểm c thay vì điểm e khoản 1 Điều 36), chọn đơn vị đúng và ghi chú.

## Đo gì trên bộ này

- Recall@K, Recall theo ngân sách token và tỉ lệ câu tìm đủ mọi đơn vị đáp án, như bộ phức tạp v1.
- So sánh ĐK1-ĐK4 có và không có bước tách vấn đề (`decompose-v1`), dùng chung một lượt tách cho mọi điều kiện.
- Chấm câu trả lời theo cùng phiếu chấm mù như bộ v1; câu trả lời bỏ sót một vấn đề trong `issues` thì không được điểm đúng tối đa.
