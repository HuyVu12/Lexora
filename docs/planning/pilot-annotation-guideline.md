# Guideline bổ sung cho pilot hợp đồng/thử việc

Phiên bản nháp 02/11/2026, bổ sung [guideline gốc](../annotation-guidelines.md). Chưa thay freeze 150 câu hoặc tập held-out.

## Gán nhãn nguồn

1. Chọn đúng snapshot hash từ `configs/sources-pilot.json`, mở `content.html` và đối chiếu `source.txt`/units. Không mặc định đây là văn bản hợp nhất hoặc nội dung hiện hành.
2. Gán Document/Điều/Khoản/Điểm và source spans trước khi gán claim. Giữ câu dẫn của Điều 25 cùng các khoản; giữ “ngày làm việc”, phủ định, điều kiện và ngoại lệ đúng nguyên văn.
3. Mỗi slot phải có quote, offsets và unit version. Chỉ chấp nhận exact quote; cùng quote có nhiều vị trí phải xử lý mơ hồ.
4. Không thấy thông tin thì `unknown`; `not_present` chỉ dùng khi người gán đã rà phạm vi xác định. Ngoại lệ không trích được không đồng nghĩa không có ngoại lệ trong toàn bộ pháp luật.
5. Dẫn chiếu Điều 21 và văn bản ngoài lát cắt chưa được resolve: ghi cần review, không tự thêm căn cứ hoặc coi đã trả lời đầy đủ.
6. Kha/Vũ lưu bản annotation độc lập, người gán/ngày/phiên bản; không dùng output validator làm gold. Bản AI chuẩn bị chỉ là nháp để hai người review.

## Bộ câu hỏi

`tests/fixtures/pilot-questions.json` có 12 câu nháp: 10 câu tra cứu nguồn, một câu hiệu lực và một câu ngoài phạm vi. Toàn bộ `split=pilot`; chưa có held-out hoặc đáp án chuẩn đã được gán độc lập. Các family hiện khác nhau nhưng cần review quan hệ giữa câu trước khi lập split nghiên cứu.

Script `scripts/evaluate_pilot.py` chỉ đo Recall@5 trên 10 câu có relevant unit. Hai câu không có gold bị loại khỏi mẫu số, không được tính là từ chối đúng. Tra cứu BM25 hiện không có cơ chế kết luận out-of-scope hoặc xác minh hiệu lực.

## Rubric đề xuất để review câu trả lời sau khi có generator

| Điểm | Tiêu chí |
|---|---|
| 0 | Sai nguồn, thêm kết luận không được hỗ trợ, hoặc mất điều kiện làm đổi ý nghĩa |
| 1 | Có phần đúng nhưng thiếu căn cứ/điều kiện quan trọng hoặc chưa đủ ý |
| 2 | Đúng trong phạm vi snapshot, đủ điều kiện quan trọng, có citation thực sự hỗ trợ |

Chấm riêng citation ID/offset/hash, support ngữ nghĩa, completeness và hành vi thiếu dữ kiện/từ chối. Lỗi dịch vụ không phải từ chối pháp lý. Chưa có kết quả chấm correctness/grounding trong lần triển khai này.
