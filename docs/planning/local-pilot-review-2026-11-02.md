# Gói triển khai local để review — 02/11/2026

Đã triển khai phần độc lập với model và chạy được trên hai snapshot thật từ VBPL: tải nguồn → tách toàn văn → chuẩn hóa/source map → parser → schema/evidence validation → tra cứu BM25. Phần này đủ để review dữ liệu và nền tảng pipeline; chưa phải demo RAG hoàn chỉnh hoặc task cha đã Done trên Jira.

## 1. Review nhanh

Từ workspace Lexora, PowerShell, Python 3.11+ (đã chạy trên 3.14.8). Không cần cài thư viện hoặc tài khoản dịch vụ:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m legal_ai.cli validate tests/fixtures/contract-v1 --output data/interim/fixture-validation.jsonl
python -m legal_ai.cli validate data/normalized/pilot-v2 --output data/interim/pilot-validation.jsonl
python -m legal_ai.cli search data/normalized/pilot-v2 'Tiền lương thử việc ít nhất bao nhiêu phần trăm?' --top-k 2
```

Kết quả dự kiến: 26 test pass; fixture có một claim needs_review; bundle thật chưa có claim nên báo cả ba số quyết định bằng 0. Điều này không có nghĩa đã validate ngữ nghĩa toàn bộ văn bản. Lệnh search trả đúng đoạn Điều 26 và citations/source context, `generated_answer=false`.

Lệnh search hiện trả đoạn nguồn; chưa có answer generator, xác minh hiệu lực hoặc bộ phân loại ngoài phạm vi. Không sử dụng score BM25 làm xác suất đúng hay ngưỡng từ chối.

## 2. Đầu ra theo task

Các trạng thái dưới là tiến độ local để review; chưa ghi Jira/GitHub, chưa commit/push.

| Task/subtask theo backlog đã đọc | Đầu ra đã làm | Còn thiếu trước nghiệm thu đầy đủ |
|---|---|---|
| T01.1 / SCRUM-33 | Chốt pilot hợp đồng/thử việc với người dùng, ghi nguồn/phạm vi trong `pilot-resources.md` | Danh mục mở rộng 8–12 văn bản và câu hỏi đã review |
| T01.2–3 / SCRUM-34–35 | Phương án CPU/stdlib, ghi rõ unknown và phân công hiện có | Quota Lightning/model, giờ làm từng người và CPU/RAM/GPU chưa xác nhận |
| T02.1–2 / SCRUM-36–37 | Hai snapshot VBPL, manifest UTC/MIME/hash/URL; kiểm tra đúng legal body; giữ bản cũ | Kha/Vũ review source và metadata trước khi đóng T02 |
| T02.3 / SCRUM-38 | Tên/mã nguồn được đối chiếu với trang đã tải; giữ hiệu lực unknown | Chưa kiểm tra đầy đủ sửa đổi/hợp nhất, provenance hiệu lực |
| T03.1 / SCRUM-39 | NFC/newlines, mapping từng code point → span raw và map paragraph HTML | Chưa hỗ trợ PDF/page/bounding box |
| T03.2 / SCRUM-40 | Parser Chương/Mục/Điều/Khoản/Điểm, audit orphan/gap/duplicate; không xóa text chưa gán | Ngoài phạm vi pilot còn audit, đặc biệt phụ lục; chưa đủ general-purpose parser |
| T03.3 / SCRUM-41 | Kiểm tra 14 target units và source spans; báo cáo audit; 0 parser audit trong lát cắt | Review thủ công độc lập của hai thành viên; không suy full corpus đúng từ pilot |
| T04.1–3 / SCRUM-42–44 | Contract Python v1 pilot, fixture JSONL, version IDs, exact evidence và migration note | NormClaim định lượng/AND-OR hoàn chỉnh, views entity/graph và xác nhận liên module bởi Kha/Vũ |
| T05.1 / SCRUM-45 | Callable provider boundary, explicit model/revision/config hash, timeout, cache và lỗi có cấu trúc; test transport giả lập | Chưa nối provider thật, chưa có raw/error run logs hoặc số đo model |
| T06.1–2 / SCRUM-48–49 | Guideline pilot và 12 câu nháp, expected status/relevant units | Chưa đủ 150 câu, chưa gán độc lập/gold hoặc freeze split T06.3 |
| T08.2–3 / SCRUM-55–56 | BM25 CPU, leaf retrieval + parent evidence, deterministic tie-break; pilot retrieval smoke | Chưa dense/RRF, fixed-token windows ĐK1, index manifests đầy đủ hoặc benchmark độc lập |
| T09.1 / SCRUM-57 | Checks schema/ID/parent/hash/offset/quote; unknown chuyển review; kiểm tra evidence cả khi chưa có claim | Chưa đủ validator V1–V7, references/temporal/duplicate policies và false-rejection evaluation |

T07 LLM/rule extractor, T10 generator/citation gate cho answer và T11 release demo hoàn chỉnh chưa triển khai. Fixture claim được viết rõ là tổng hợp và không phải output extraction thật. BM25 nguồn không được coi là đã hoàn thành ĐK1–ĐK4.

## 3. Nguồn đã lưu

| Văn bản | Nguồn chính thống | SHA-256 bytes snapshot | Phần pilot |
|---|---|---|---|
| 45/2019/QH14 | [VBPL — 139264](https://vbpl.vn/van-ban/chi-tiet/139264) | `1dc5b362a39e8a1a5765a73c953bb224accbe3056195c737ac0e96fc3e1f2fcb` | Điều 24–27, tổng 13 target nodes |
| 145/2020/NĐ-CP | [VBPL — 152668](https://vbpl.vn/van-ban/chi-tiet/152668) | `118dbe704bd463c0c182b193f536991939cfb3d51fa90944471e6109b5a1c445` | Điều 6, một target node về hợp đồng giám đốc doanh nghiệp có vốn nhà nước |

Hai nguồn tải lúc 10:20 UTC ngày 02/11/2026, timestamp chính xác trong manifest từng snapshot. URL cũ dạng `TW/Pages/vbpq-toanvan.aspx` chuyển về trang chủ; loader đã từ chối trang chủ. URL mới có toàn văn trong Next.js Flight stream; extractor đọc UTF-8 byte length và yêu cầu đúng một body pháp luật.

Điều 6 Nghị định là ví dụ hợp đồng đặc thù có dẫn chiếu Điều 21 ngoài lát cắt; chưa đủ căn cứ trả lời tổng quát cho mọi hợp đồng. Hai snapshot chưa được xác nhận là bản hợp nhất hoặc corpus hiện hành. Tất cả metadata hiệu lực giữ unknown.

## 4. Artifact để mở kiểm tra

- [`manifest.json`](../../data/normalized/pilot-v2/manifest.json): 2 documents, 14 target units, 4 context units, 11 leaves, 0 claims.
- [`units.jsonl`](../../data/normalized/pilot-v2/units.jsonl): ID/version/source span và own text của từng node.
- [`parser-report.json`](../../data/normalized/pilot-v2/parser-report.json): audit toàn văn và lát cắt. Toàn văn Bộ luật có 17 audit, Nghị định có 56; lát cắt được chọn có 0 audit cú pháp, không phải xác nhận đúng ngữ nghĩa.
- [`Bộ luật — content.html`](../../data/normalized/pilot-v2/bll-45-2019/content.html), [`Nghị định — content.html`](../../data/normalized/pilot-v2/nd-145-2020/content.html): toàn văn trích từ snapshot để đối chiếu.
- `normalized.json` và `paragraphs.json` trong thư mục từng văn bản: mapping nội dung chuẩn hóa về đoạn HTML nguồn.
- [`fixture contract v1`](../../tests/fixtures/contract-v1/): dữ liệu tổng hợp versioned trong Git; một claim cố ý giữ completeness/conditions unknown nên needs_review.
- [`kết quả retrieval smoke`](../report/pilot-retrieval-smoke-2026-11-02.json): mười câu có gold nháp đều Recall@5=1.0; hai câu không gold loại khỏi mẫu số. Chưa đánh giá abstention, correctness, grounding hoặc held-out.

Raw và normalized data bị `.gitignore` loại khỏi Git theo chính sách repo; chúng hiện có trong workspace này. Clone mới sẽ không có snapshot chỉ nhờ checkout code. Bản backup local hai snapshot: `data/raw/pilot-snapshots-v1.zip`, gồm nguyên HTML và metadata.

## 5. Tái lập không cần mạng

Build luôn yêu cầu output mới/rỗng để không ghi đè artifact. Chọn tên thư mục khác nếu đã chạy lệnh dưới:

```powershell
$env:PYTHONPATH = 'src'
python scripts/build_fixture.py
python -m legal_ai.cli build-pilot --output data/normalized/pilot-review-rebuild
python scripts/evaluate_pilot.py data/normalized/pilot-v2 --output docs/report/pilot-retrieval-smoke-2026-11-02.json
```

Đã build lại vào `data/normalized/pilot-repro-check` và đối chiếu toàn bộ manifest/artifact hashes: giống `pilot-v2`. Hash bao gồm source HTML, source text, paragraph/source maps, schema data và parser report.

Đã kiểm tra CRC archive, giải nén vào `data/raw/pilot-restore-check`, build với raw root đó vào `data/normalized/pilot-restore-check` và so toàn bộ manifest/hash: giống `pilot-v2`. Đây là restore artifact local; chưa phải cài từ môi trường sạch hoặc hoàn thành T11.

Snapshot command có mạng chỉ được chạy khi đã duyệt scope external. Tải lại trang mới có thể cho hash HTML khác; không âm thầm sửa config pin cũ. Phải review rồi tạo config/build version mới hoặc phục hồi archive pinned.

## 6. Các giới hạn cần review

- Contract v1 pilot chưa biểu diễn đủ quantities/basis/trigger và AND/OR theo thiết kế; xem [migration note](schema-v1-migration.md).
- accepted hiện chỉ nghĩa vượt các kiểm tra kỹ thuật đã triển khai, không xác nhận phát biểu pháp lý đúng. Claim có unknown/completeness unknown vẫn needs_review.
- Timeout provider không thể giết callable Python bất kỳ. Transport thật phải có timeout I/O hữu hạn; instance chặn request tiếp khi worker cũ chưa xong và không cache kết quả worker timeout.
- Bộ câu pilot do agent chuẩn bị, chưa gán nhãn độc lập. Không dùng số 1.0 ở đây làm kết quả luận văn hoặc so sánh ĐK1–ĐK4.
- Chưa có UI hoặc generator; chỉ demo được tra cứu nguồn. Để đạt demo RAG 08/11, cần chọn runtime thật, làm extraction/validator còn thiếu, context/answer/citation gate và tích hợp.

## 7. Thông tin còn chờ

Người dùng xác nhận tài nguyên model/provider miễn phí hoặc Lightning có thể dùng, cùng giờ làm Vũ/Kha tuần này. Không gửi API key qua chat. Chưa có dữ liệu này thì giữ model/revision chưa chọn, không tự thuê tài nguyên.

Các thay đổi lần này chỉ nằm trong workspace Lexora. Không cập nhật Jira, GitHub hoặc tài nguyên dự án khác.
