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
