# Kế hoạch triển khai đến 20/12/2026

## Thiết kế kỹ thuật bổ sung — 01/11/2026

Xem [kế hoạch kiến trúc và kỹ thuật chi tiết](technical-design-plan.md) cho kiến trúc Mermaid, schema quy phạm, thuật toán extraction/validation/retrieval, luồng hỏi đáp, lựa chọn model, vận hành Lightning Free, đánh giá và backlog kỹ thuật. Người dùng xác nhận ưu tiên chất lượng demo, giữ hai thành viên và hạn 20/12; có thể mở rộng chủ đề theo năng lực dữ liệu. Cấu hình DEMO tối ưu riêng; ĐK1–ĐK4 tiếp tục giữ phép so sánh theo giao thức thực nghiệm. Reranker và mở rộng dẫn chiếu được ưu tiên thử cho DEMO sau khi luồng cốt lõi ổn định, không tự thêm vào riêng ĐK4.

## Hiện trạng và cam kết
Ngày lập: 31/10/2026. Người dùng xác nhận chưa có code/dữ liệu/pilot; giữ lịch và phân công đề cương. Hạ tầng dự kiến Lightning AI, chưa có ngân sách GPU, ưu tiên API miễn phí nếu khả dụng. Không giả định giai đoạn 1–2 trong đề cương đã hoàn thành. Đây là lịch phục hồi gấp; cần báo tiến độ thực tế với giảng viên.

Kha: schema, extraction, validation, KB (RQ1/RQ2). Vũ: retrieval, RAG, ĐK1–ĐK2 (RQ3). Cả hai: corpus, annotation chéo, evaluation, tích hợp và báo cáo. Mỗi ngày cập nhật việc xong/vướng/tiếp theo; kiểm tra tích hợp ít nhất hai lần mỗi tuần.

## Giai đoạn phục hồi: 31/10–08/11
| Hạn | Công việc và người phụ trách | Đầu ra / điều kiện hoàn thành |
|---|---|---|
| 01/11 | Cả hai chốt phạm vi; kiểm tra Lightning, nguồn chính thống và tài nguyên | Danh mục dự kiến 8–12 văn bản, 60–100 điều khoản; quyền truy cập GPU thực tế; ghi unknown thay vì đoán hiệu lực |
| 02/11 | Kha schema v0; Vũ snapshot và parser pilot | 2 văn bản, 10–15 điều khoản; nguồn/ngày truy cập/hash; đối chiếu thủ công parser |
| 03/11 | Cả hai pilot model/embedding và gán nhãn thử; Vũ khung 150 câu | Bảng chất lượng/latency/tài nguyên; chọn cấu hình khả thi, sửa guideline; chưa tinh chỉnh theo held-out |
| 04/11 | Cả hai chốt schema/guideline và bộ câu hỏi | Khóa split 105/45 dự kiến bằng hash; nếu thiếu thì ghi quy mô thực và lý do, không khai đủ 150 |
| 05/11 | Kha extraction rule-based + LLM; Vũ ĐK1/ĐK2 | JSONL có nguồn; retrieval trả unit IDs; cache model output có config hash |
| 06/11 | Kha validator schema/ref/evidence; Vũ context/answer | Dữ liệu lỗi được phát hiện; citation map được về nguồn; chưa cần UI |
| 07/11 | Hai người tích hợp và sửa lỗi chặn pipeline | Một câu chạy từ snapshot → KB → retrieval → answer; ca thiếu evidence từ chối |
| 08/11 | Kha bàn giao KB sơ bộ; Vũ demo lát cắt | Gói KB có manifest/schema, raw và validated; chạy lại được trên pilot; danh sách thiếu sót |

Mốc 08/11 là lát cắt MVP nhỏ. Nếu GPU không dùng được trước 03/11: tiếp tục parser/rule-based/retrieval và annotation trên CPU, báo rõ extraction LLM chưa hoàn thành; tìm tài nguyên trường hoặc thỏa thuận thu hẹp khối lượng với giảng viên. Không đổi ĐK3 thành rule-based mà vẫn gọi là đối chứng theo đề cương.

## 09/11–27/11: hoàn thành MVP
| Khoảng | Chủ trì | Công việc | Tiêu chí nghiệm thu |
|---|---|---|---|
| 09–12/11 | Cả hai | Mở rộng corpus; hoàn thiện gold 40–60 điều khoản và gán nhãn độc lập | Manifest đủ nguồn, snapshot và scope; annotation độc lập lưu riêng |
| 13–16/11 | Kha | Kiểm tra trùng lặp, ngày/trạng thái, lỗi chèn; adjudication | Báo cáo RQ1/RQ2 sơ bộ; phân biệt reject và needs_review; không quảng cáo kiểm chứng ngữ nghĩa đầy đủ |
| 13–16/11 | Vũ | Adapter index, ĐK3/ĐK4, citation, abstention | Bốn cấu hình nhận cùng input question và trả cùng answer contract |
| 17–20/11 | Cả hai | Chạy dev, phân tích lỗi, sửa prompt/parser/retrieval | Tất cả thay đổi có run ID, model/config hash; không mở held-out |
| 21–24/11 | Vũ + Kha review | Demo mỏng, xem nguồn, lỗi/timeouts; smoke toàn pipeline | Câu tra cứu/tổng hợp/ngoài phạm vi có hành vi rõ ràng; nguồn mở được |
| 25–27/11 | Cả hai | Đóng băng MVP và cấu hình thực nghiệm | Run tái lập, README lệnh thật, dependency lock, backup, tests cốt lõi pass |

## 28/11–09/12: thực nghiệm chính thức
- 28/11: kiểm tra hash split/corpus/config, quota và checkpoint; khóa generator/prompt.
- 29/11–02/12: chạy bốn điều kiện trên bộ câu hỏi khóa; ghi lỗi và retry, không bỏ âm thầm câu thất bại. 150 × 4 = 600 lượt sinh tối thiểu, chưa tính pilot/retry.
- 03–05/12: chấm cùng mẫu phân tầng cho cả bốn điều kiện; tính extraction/validation/retrieval/citation/grounding/correctness/abstention.
- 06–07/12: đối soát điểm, phân tích lỗi theo chủ đề và loại câu; báo cáo thời gian/chi phí.
- 08–09/12: hoàn thành bảng RQ1–RQ3, hạn chế và thảo luận; khóa kết quả. Chỉ chạy lại khi có lỗi phương pháp, ghi rõ phiên bản.

## 10/12–20/12: báo cáo và bảo vệ
- 10–13/12: hoàn thiện 5 chương; mỗi bảng kết quả trỏ được về run manifest.
- 14–16/12: demo, slide, hướng dẫn setup và video dự phòng; cài thử từ môi trường sạch.
- 17–18/12: phản biện thử; kiểm tra trích dẫn, dữ liệu, phân công, hạn chế.
- 19–20/12: dự phòng sửa lỗi và đóng gói bàn giao; không thêm tính năng mới.

Viết chương 1–2 ngay từ tuần đầu, chương 3 song song triển khai; không dồn toàn bộ viết báo cáo vào tháng 12.

## Backlog theo phụ thuộc
1. P0 corpus manifest → parser → schema → fixture hợp đồng (cả hai).
2. P0 rule baseline + LLM extraction → validator → KB bàn giao (Kha).
3. P0 fixed/structural chunking → index → retriever → context/citations (Vũ), chạy song song mục 2.
4. P0 question/gold freeze → metrics/rubric → runner bốn điều kiện (cả hai).
5. P0 tích hợp → kiểm thử → MVP → thực nghiệm → báo cáo.
6. P1 xem nguồn/evidence trong demo, checkpoint/resume, bảng lỗi validation.
7. P2 graph traversal, reranker, semantic conflict và review UI; chỉ sau MVP và khi còn tài nguyên.

## Kiểm thử phải có trước MVP
Parser bảo toàn Điều/Khoản/Điểm; evidence Unicode offsets; ref thiếu; schema sai; version hash thay đổi; ngày không hợp lệ; ĐK4 loại record bị reject; index không lẫn điều kiện; citation không tồn tại; câu ngoài phạm vi; adapter timeout và resume không nhân bản kết quả. Unit tests không gọi mạng; integration dùng fixture tổng hợp ghi rõ không phải văn bản pháp luật thật.

## Rủi ro và xử lý
- Không đủ miễn phí: đo pilot trước, cache extraction/embedding, batch và checkpoint; không tự thuê hoặc dùng API trả phí.
- Chậm gán nhãn: ưu tiên mẫu đại diện, giảm phạm vi có ghi nhận thay vì tạo gold bằng model rồi tự chấm.
- Nguồn hiệu lực phức tạp: lưu metadata nguồn và unknown; tránh tuyên bố suy luận pháp luật theo thời điểm.
- Không đủ thời gian: cắt P2, giữ bốn điều kiện và evaluation; thay đổi quy mô phải có quyết định ghi lại.
- Không có chuyên gia: nói rõ gán nhãn chéo sinh viên; kappa không xác nhận tính đúng pháp lý.

## Định nghĩa hoàn thành
Corpus có provenance; schema/version và KB raw/validated; pipeline chạy được; câu trả lời có evidence; bốn điều kiện so công bằng; gold/split khóa; báo cáo metric và lỗi; demo và hướng dẫn tái lập; mọi giới hạn và dữ liệu thiếu được công bố.
