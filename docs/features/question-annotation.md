# Corpus nghiên cứu và gán nhãn bộ câu hỏi

Ngày: 07/11/2026.
Trạng thái: đã triển khai bản đầu (code, test, E2E trên trình duyệt thật); chưa có bộ câu hỏi thật.

## Mục tiêu

Dựng bộ câu hỏi có nhãn chuẩn cho thực nghiệm ĐK1-ĐK4 theo `docs/evaluation-protocol.md`.
Nhãn do hai người (Vũ, Kha) gán độc lập rồi đối soát; model chỉ đề xuất, người quyết định.
Mọi đơn vị liên quan trỏ tới một phiên bản corpus đã khóa, nên kết quả tái lập được.

## Quy trình

1. Dựng danh mục văn bản một lần (cần phần `catalog` của `.venv`):
   `python -m legal_ai.cli catalog-build --output data/catalog/catalog-v1.sqlite` (đọc `data/catalog/raw/`, xem mục Nguồn).
2. Chạy app; thêm `--allow-vbpl` nếu muốn lấy văn bản từ vbpl.vn, thêm `--proposal-model claude-opus-5-5 --approve-claude` nếu muốn model đề xuất:
   `.venv\Scripts\python -m legal_ai.web --store <store.sqlite> --allow-vbpl --proposal-model claude-opus-5-5 --approve-claude --proposal-max-calls 40`
3. Nghiên cứu > Corpus: tạo corpus, thêm văn bản bằng một trong ba cách: tìm trong danh mục cục bộ, dán link vbpl.vn, tải tệp TXT/HTML/DOCX/PDF có lớp chữ.
   Mỗi lần lấy từ vbpl.vn phải xác nhận trong hộp thoại.
4. Xem cảnh báo parser của từng văn bản, rồi khóa phiên bản corpus.
5. Nghiên cứu > Bộ câu hỏi: tạo bộ trên phiên bản đã khóa, viết câu hỏi hoặc soạn nháp bằng model từ các Điều đã chọn.
6. Mỗi người chọn một lần: tự gán hay xem đề xuất của model; sau đó gán loại câu, hành vi mong đợi (trả lời/từ chối), các đơn vị liên quan và ghi chú.
7. Trao đổi: người tạo bộ tải "gói câu hỏi" (chứa phiên bản corpus và câu hỏi) gửi người kia; người kia nhập gói, gán nhãn, tải "tệp nhãn" gửi lại.
8. Đối soát: nhập tệp nhãn của người kia, xem kappa và Dice, chốt nhãn cuối từng câu, khóa bộ câu hỏi.
9. Tải tệp bộ câu hỏi đã khóa và chạy thực nghiệm:
   `python -m legal_ai.cli corpus-export --store <store.sqlite> --version <mã phiên bản> --output <thư mục mới>`
   `python -m legal_ai.cli run-retrieval <thư mục đó> --condition configs/experiments/dk2.json --questions <tệp đã khóa> --output experiments/runs/<mới>`

## Nhãn

| Trường | Giá trị |
|---|---|
| Loại câu | `lookup` (tra cứu), `synthesis` (tổng hợp), `temporal` (hiệu lực, sửa đổi), `out_of_scope` (ngoài phạm vi) |
| Hành vi mong đợi | `answer` (corpus có đủ căn cứ nguyên văn) hoặc `refuse` |
| Đơn vị liên quan | `unit_id` của phiên bản corpus; bắt buộc khi `answer`, chọn đơn vị nhỏ nhất chứa căn cứ |
| Ghi chú | Tùy chọn |

Câu cùng ý khác cách hỏi thuộc cùng "nhóm diễn đạt" và luôn nằm chung tập dev hoặc held-out.

## Lưu ý phương pháp

- Đề xuất của model chỉ hiện với người đã chọn "xem đề xuất"; mỗi trường ghi lại là giữ hay đã sửa đề xuất.
  Nếu cả hai người cùng xem đề xuất, độ đồng thuận đo được là đồng thuận khi duyệt đề xuất, thường cao hơn gán độc lập; trang đối soát nhắc điều này và tệp đã khóa ghi chế độ của từng người.
  Khuyên ít nhất một người tự gán.
- Câu hỏi do model soạn nháp được ghi nguồn `model` (kèm mã lần gọi và cờ đã sửa câu chữ); báo cáo nên tách kết quả theo nguồn câu hỏi.
- Kappa dùng cho loại câu và hành vi; tập đơn vị dùng Dice và tỉ lệ khớp hoàn toàn.
  Đây là đồng thuận giữa hai sinh viên, không phải xác nhận của chuyên gia pháp lý.
- Chia dev/held-out theo nhóm diễn đạt, phân tầng theo loại câu, thứ tự nhóm theo SHA-256 của `seed:family_id`; seed và tỉ lệ được ghi trong tệp đã khóa.
  Không dùng held-out để chọn model, prompt hay tham số.

## Model

- Gọi `claude -p` của Claude Code trên máy, bằng đăng nhập Claude của người dùng (`src/legal_ai/providers/claude_code.py`): prompt hệ thống riêng của Lexora, không công cụ, JSON schema, không lưu phiên, `--safe-mode` (bỏ CLAUDE.md, hook, plugin, MCP của người dùng), chạy trong thư mục trống.
- Mỗi lần chạy app cố định một model và mức effort, có ngân sách gọi, không thử lại, không đổi model dự phòng.
- Đề xuất nhãn gửi câu hỏi và tối đa 8 đơn vị ứng viên tìm bằng BM25 trên bản ghi ĐK2 của phiên bản corpus; schema chỉ cho chọn trong các `unit_id` ứng viên.
  Soạn nháp gửi nguyên văn các Điều người duyệt chọn.
- Prompt nằm ở `prompts/question-label-v1.md` và `prompts/question-draft-v1.md`; mỗi lần gọi ghi tên tệp, SHA-256 prompt, schema, số token và chi phí niêm yết.
- Opus 5.5 không cho đặt temperature hay seed, nên chạy lại không ra đúng kết quả cũ; đề xuất và nhật ký gọi được lưu để tái lập từ bản lưu.
- Đã kiểm tra một lần gọi thật (07/11/2026) với câu hỏi tổng hợp tiếng Việt: Opus 5.5 effort `low` chọn đúng đơn vị, 275 token ra, chi phí niêm yết 0,026 USD.

## Nguồn văn bản

- vbpl.vn: app gọi API công khai mà chính trang vbpl.vn dùng (`vbpl-bientap-gateway.moj.gov.vn/api/qtdc/public/doc/{id}`), mỗi lần một văn bản, cách nhau ít nhất 2 giây.
  API này không có tài liệu chính thức nên có thể đổi; lúc đó vẫn tải tệp lên được.
  Trang tìm kiếm của vbpl.vn có lớp chống bot và không được tự động hóa.
- Danh mục cục bộ dựng từ hai bộ dữ liệu mở có mã văn bản vbpl.vn: `th1nhng0/vietnamese-legal-documents` (CC BY 4.0, revision `8977887f17be2defae4c5171d55562e1cde7d695`) và `undertheseanlp/UTS_VLC` (MIT, revision `decbf8d7c0e1f18bdf1d4dcb429ff0fc322d4231`).
  Trạng thái hiệu lực trong danh mục là của bộ dữ liệu, có thể đã cũ; khi lấy văn bản, Lexora lưu trạng thái do vbpl.vn trả về.
  Tệp tải về đặt ở `data/catalog/raw/` (ngoài Git) cùng `revisions.json`.

## Giới hạn

- PDF scan cần OCR; PDF có lớp chữ có thể ngắt dòng giữa câu, cần xem cảnh báo parser.
- Parser còn cảnh báo ở các điều sửa đổi luật khác có trích dẫn lồng nhau; cần người xem trước khi khóa corpus.
- App chạy trên một máy (loopback); hai người trao đổi bằng tệp, không đồng bộ trực tuyến.
- Chưa có đánh giá câu trả lời (citation, grounding, correctness) và chưa có ĐK3/ĐK4.
