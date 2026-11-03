# Review task và kế hoạch demo tuần 02–08/11/2026

Ngày kiểm tra: 02/11/2026. Trạng thái tài liệu: hoàn tất rà soát, đề xuất để review; chưa phải cam kết hoàn thành triển khai.

Đây là ảnh chụp hiện trạng trước khi bắt đầu code. Đầu ra triển khai sau review được ghi riêng tại [gói local 02/11](local-pilot-review-2026-11-02.md); không dùng các nhận xét “chưa có implementation” dưới đây làm hiện trạng sau triển khai.

## 1. Kết luận

Ưu tiên tháo chặn T01 → T02, đồng thời chuẩn bị schema/parser bằng fixture. Sau khi có snapshot thật, tách hai nhánh extraction/validation và retrieval/answer; tích hợp thành pilot ngày 08/11. Phạm vi nên là hai văn bản và 10–15 đơn vị pháp luật, tập trung một chủ đề để giảm rủi ro.

Không đủ cơ sở khẳng định demo chắc chắn kịp: chưa biết giờ làm khả dụng của hai người và quota model. Mốc cần bảo vệ là một câu chạy xuyên suốt trước cuối 06/11, để còn 07–08/11 kiểm thử và đóng gói.

## 2. Bằng chứng hiện trạng

- Jira project SCRUM trên [vku-lexora](https://vku-lexora.atlassian.net/jira/software/projects/SCRUM/summary): truy vấn `project = SCRUM ORDER BY key ASC`, nhận đủ 94 work item, `isLast=true`: 6 epic, 22 task, 66 subtask. Tất cả có trạng thái To Do.
- Không thấy lệch trạng thái cha/con trong 94 work item này. Trạng thái Jira chỉ phản ánh dữ liệu đang ghi, không chứng minh chưa có công việc ngoài repo.
- [GitHub main](https://github.com/HuyVu12/Lexora/tree/main): cây đầy đủ tại SHA `80b0f4066fd4b050b28375f70ee663ae703c3d9b`, không bị cắt; chưa có Python implementation, dependency manifest hoặc test thực thi. Các module và demo chỉ có README.
- Truy vấn issue và PR trong `HuyVu12/Lexora` trả danh sách rỗng. Không suy rộng kết luận sang code local của thành viên khác hay nhánh chưa kiểm tra.
- Bình luận tại SCRUM-11, SCRUM-14, SCRUM-21 đều có tổng 0. Chưa rà toàn bộ bình luận của 94 work item, chưa kiểm tra board/sprint bằng API riêng; không kết luận sprint hiện tại.
- Các task Kha đang Unassigned theo yêu cầu ghi trong mô tả, chờ thêm tài khoản. Đây là cấu hình có chủ ý; tên Kha trong kế hoạch là người phụ trách theo mô tả.
- T01 có hạn 01/11, đã qua ngày theo kế hoạch mà vẫn To Do; cần xác nhận đầu ra, không tự coi hoàn thành.
- Local `AGENTS.md` mô tả cấu trúc cũ (chỉ có tài liệu PDF, chưa có Git). README và cây file phản ánh skeleton mới hơn; vẫn tuân thủ quy định xin phép external của AGENTS.md.

## 3. Việc có thể tiến hành

“Chuẩn bị ngay” chỉ áp dụng phần độc lập; không bỏ dependency trên Jira hoặc coi task cha đã được nghiệm thu.

| Mức sẵn sàng | Task/subtask | Việc cụ thể | Điều kiện nghiệm thu |
|---|---|---|---|
| Làm ngay | T01 / SCRUM-33, 34, 35 | Chốt chủ đề, nguồn dự kiến, resource sheet và giờ làm khả dụng | Có quyết định phạm vi; tài nguyên chưa biết ghi unknown |
| Chuẩn bị ngay | T04 / SCRUM-42, 43, 44 | Schema Document/LegalUnit/Evidence/Claim; fixture tổng hợp và migration note | T04 bị T02 chặn: phải kiểm chứng bằng snapshot thật trước khi đóng |
| Chuẩn bị ngay | T03 / SCRUM-39, 40 | Code normalization và parser state machine, fixture Unicode/heading | T02 có snapshot; SCRUM-41 đối chiếu thủ công 10–15 units thật |
| Chuẩn bị ngay | T05 / SCRUM-45 | Provider adapter, timeout, cache và cấu trúc bảng benchmark | Benchmark/chọn model cần dữ liệu pilot, tài nguyên và revision cụ thể |
| Chuẩn bị ngay | T06 / SCRUM-48, 49 | Guideline, rubric, cấu trúc question/support sets | T01 chốt scope; đáp án dựa nguồn thật, freeze sau rà leakage |
| Sau T01 | T02 / SCRUM-36, 37, 38 | Hai snapshot, manifest, checksum và metadata nguồn | Bytes nguồn thật, URL/MIME/hash/thời gian tải; hiệu lực chưa rõ giữ unknown |
| Sau T03/T04/T05 | T07 / SCRUM-51–53 | Rule extraction, LLM extraction, quote alignment/cache | Lưu raw responses, qualifiers và evidence; không fuzzy accept |
| Sau T03/T04/T05 | T08 / SCRUM-54–56 | Fixed/structural representations, BM25/dense/RRF, đo retrieval | Canonical IDs/quotes/source mapping; config/index tách biệt |
| Sau T07 | T09 / SCRUM-57–59 | Validator, policy reference/ngày/trùng và lỗi chèn | accepted/rejected/needs_review có reason; đo cả false rejection |
| Sau T08/T04 | T10 / SCRUM-60–62 | Context, generator, citation gate và thiếu căn cứ | Citation nằm trong bundle, quote/offset/hash đúng; lỗi runtime tách riêng |
| Sau T09/T10 | T11 / SCRUM-63–65 | KB handoff, tích hợp pilot, đóng gói và restore | Pipeline chạy lại được, release note ghi thiếu sót thật |

Có thể viết nền tảng báo cáo ở SCRUM-93 ngay theo mô tả task, nhưng giới hạn công sức để ưu tiên demo. T20 chỉ chặn chương kết quả, không chặn chương 1–2.

## 4. Kế hoạch bàn giao trong tuần

Phân công giữ theo mô tả Jira. Các mốc dưới là đề xuất điều phối; không sửa deadline/status Jira.

| Ngày | Vũ | Kha | Đầu ra để review |
|---|---|---|---|
| 02/11 | T01; thu hai snapshot, manifest; khởi tạo parser | T01.3; rà metadata; schema và fixture nháp | Phạm vi demo, nguồn/hash, fixture giao tiếp |
| 03/11 | Parser 10–15 units; adapter/pilot model | Review parser; schema/evidence; tham gia chọn cấu hình | Units có source map; bảng pilot và quyết định model hoặc blocker cụ thể |
| 04/11 | T06 question/split; bắt đầu representations | Chốt schema/migration; bắt đầu rule/LLM extraction | Schema hai bên load được; split/hash và quy mô thực được ghi |
| 05/11 | T08 retrieval/index; nguồn và quotes | T07 extraction/alignment/cache | Nhánh retrieval chạy và KB raw có provenance |
| 06/11 | T10 context/generator, nối một câu xuyên suốt | T09 schema/evidence checks; bàn giao phần KB đạt kiểm tra | Một câu thật có câu trả lời và citation mở đúng nguồn |
| 07/11 | Citation gate, xử lý timeout/thiếu nguồn; sửa tích hợp | Reference/temporal/duplicate policies; lỗi chèn và rà qualifier | Smoke cases có kết quả; danh sách lỗi chặn release |
| 08/11 | T11 tích hợp, runbook, đóng gói/restore, video dự phòng | Raw/validated KB, manifest và review cuối | Gói demo nhỏ chạy lại được cùng danh sách hạn chế |

T01–T06 tập trung quá nhiều việc cho Vũ trong 02–04/11. Nếu thiếu giờ hoặc model không sẵn sàng, cần ghi blocker và điều chỉnh quy mô rõ ràng; không khai đủ benchmark, 150 câu hoặc task hoàn thành khi mới có bản nháp.

## 5. Phạm vi demo để review

### Bắt buộc

1. Corpus pilot: hai snapshot thật, 10–15 units đã đối chiếu, manifest có nguồn/hash.
2. Một luồng snapshot → normalization/parser → KB → retrieval → answer.
3. Câu trả lời có citation, xem được nguyên văn và đường dẫn Điều/Khoản/Điểm.
4. Câu thiếu căn cứ hoặc ngoài corpus trả trạng thái rõ ràng.
5. KB raw/validated có version; không trộn fixture tổng hợp với dữ liệu thật.
6. Có lệnh cài/chạy đã kiểm chứng, dependency được khóa cho bản pilot, kiểm thử cốt lõi và thử restore.

### Đề xuất trình diễn

- Một câu tra cứu trực tiếp.
- Một câu tổng hợp có đủ support trong corpus.
- Một câu thiếu dữ kiện cần làm rõ.
- Một câu ngoài phạm vi hoặc thiếu căn cứ.
- Một lần model không khả dụng để kiểm tra thông báo lỗi.

Chỉ lấy câu pilot/dev để chỉnh hệ thống; không mở held-out để chuẩn bị màn trình diễn. Video/replay phải gắn nhãn kết quả lưu sẵn.

UI/source viewer tối thiểu nằm trong lát cắt T08/T11. UI đầy đủ, clarification flow và debug panel của T17 vẫn giữ giai đoạn 21–24/11; không coi T17 hoàn thành từ demo pilot.

## 6. Tiêu chí nghiệm thu và bằng chứng

| Hạng mục | Bằng chứng cần bàn giao | Không đạt khi |
|---|---|---|
| Nguồn | Snapshot, manifest và kiểm tra SHA-256 | Trang lỗi/login, không truy nguyên được nguồn |
| Parser | Báo cáo đối chiếu 10–15 units và fixture hồi quy | Mất số/phủ định/ngoại lệ; heading nhận nhầm dẫn chiếu |
| Schema | Cùng fixture JSONL được cả hai module đọc; version/migration note | ID, parent hoặc evidence không khớp |
| Validator | Báo cáo mẫu sạch/lỗi chèn, decisions/reasons | Citation hoặc evidence sai lọt qua; unknown bị coi là đã xác minh |
| Retrieval | Retrieved canonical IDs/quotes và kết quả dev với mẫu số | Nguồn hiển thị khác nội dung đã truy xuất |
| Answer | Log evidence bundle, checked output và citation mapping | Citation ngoài bundle; summary thêm kết luận không được hỗ trợ |
| Runtime | Kết quả smoke cho thiếu nguồn/timeout/model unavailable | Lỗi dịch vụ hiển thị như kết luận pháp lý |
| Tái lập | README lệnh thật, dependency/config/artifact versions, restore log | Chỉ chạy được nhờ state không có trong hướng dẫn |

Chặn release khi còn lỗi sai citation/offset/hash, mất qualifier trong ca bắt buộc hoặc không restore được. Chưa có số đo nên không tuyên bố đạt Recall@5, grounding hay latency mục tiêu.

## 7. Phương án khi thiếu tài nguyên

- Trước 03/11 chưa có GPU: tiếp tục parser, fixture, annotation, rule extraction và retrieval CPU; ghi rõ LLM extraction chưa hoàn thành.
- Có thể demo tìm đoạn nguồn trên CPU trước. Nếu chưa có generator thật, gọi đúng là demo retrieval; không gọi là đã hoàn thành T10/T11.
- Fixture hoặc output cache chỉ dùng kiểm tra tích hợp/replay có nhãn, không thay cho kết quả inference thật.
- Không tự dùng API trả phí. T05 chưa có số đo thì T07/T08 chưa đủ điều kiện nghiệm thu toàn bộ.
- Cuối 06/11 chưa chạy xuyên suốt: dừng mở rộng chủ đề và tối ưu model, tập trung lỗi của luồng nhỏ.
- Nếu phải giảm quy mô câu hỏi hoặc thay đổi phương pháp nghiên cứu, ghi quyết định và xin chốt phạm vi; giữ tách DEMO và ĐK1–ĐK4.

## 8. Việc giữ sau demo pilot

T12–T22 theo lịch gốc, ngoại trừ chuẩn bị báo cáo nền tảng có thể làm sớm. Chưa kéo reranker, reference expansion, graph, OCR hoặc toàn bộ private KB vào tuần này.

[Đặc tả kho riêng](../features/private-legal-knowledge-base.md) có FKB-01–07 nhưng các mã này là gói thiết kế local, chưa phải Jira issue. Tính năng còn cần auth/scope/upload/review/invalidation; trước khi đưa vào lịch cần chốt phần backlog được thay thế hoặc nguồn lực bổ sung.

## 9. Danh mục task đã kiểm tra

Tất cả task dưới đang To Do tại thời điểm đọc. Cột phụ thuộc chỉ lấy cạnh “is blocked by” từ Jira; không phải danh sách mọi điều kiện kỹ thuật.

| Jira | Task | Hạn Jira | Assignee | Bị chặn bởi |
|---|---|---|---|---|
| [SCRUM-11](https://vku-lexora.atlassian.net/browse/SCRUM-11) | [T01] Chốt 3–4 chủ đề; kiểm tra quota Lightning; ghi resource sheet | 2026-11-01 | Vũ | Không |
| [SCRUM-12](https://vku-lexora.atlassian.net/browse/SCRUM-12) | [T02] Snapshot 2 văn bản + manifest + checksum | 2026-11-02 | Vũ | SCRUM-11 |
| [SCRUM-13](https://vku-lexora.atlassian.net/browse/SCRUM-13) | [T03] Normalize/parser/source map cho 10–15 units | 2026-11-03 | Vũ | SCRUM-12 |
| [SCRUM-14](https://vku-lexora.atlassian.net/browse/SCRUM-14) | [T04] Schema v1 + fixture claims/evidence + migration note | 2026-11-04 | Chưa gán (Kha theo mô tả) | SCRUM-12 |
| [SCRUM-15](https://vku-lexora.atlassian.net/browse/SCRUM-15) | [T05] Pilot 2 generator/2 embedder và tài nguyên | 2026-11-03 | Vũ | SCRUM-12 |
| [SCRUM-16](https://vku-lexora.atlassian.net/browse/SCRUM-16) | [T06] Guideline, câu pilot/dev/test, freeze split | 2026-11-04 | Vũ | SCRUM-11 |
| [SCRUM-17](https://vku-lexora.atlassian.net/browse/SCRUM-17) | [T07] Rule baseline + LLM extraction + quote alignment | 2026-11-05 | Chưa gán (Kha theo mô tả) | SCRUM-13, SCRUM-14, SCRUM-15 |
| [SCRUM-18](https://vku-lexora.atlassian.net/browse/SCRUM-18) | [T08] DK1/DK2 index + BM25/dense/RRF + source viewer tối thiểu | 2026-11-06 | Vũ | SCRUM-13, SCRUM-14, SCRUM-15 |
| [SCRUM-19](https://vku-lexora.atlassian.net/browse/SCRUM-19) | [T09] Validator V1–V7 + lỗi chèn | 2026-11-07 | Chưa gán (Kha theo mô tả) | SCRUM-17 |
| [SCRUM-20](https://vku-lexora.atlassian.net/browse/SCRUM-20) | [T10] Evidence bundle + generator + citation gate | 2026-11-08 | Vũ | SCRUM-18, SCRUM-14 |
| [SCRUM-21](https://vku-lexora.atlassian.net/browse/SCRUM-21) | [T11] Release pilot artifacts + demo nhỏ | 2026-11-08 | Vũ | SCRUM-19, SCRUM-20 |
| [SCRUM-22](https://vku-lexora.atlassian.net/browse/SCRUM-22) | [T12] Corpus/gold mở rộng và gán độc lập | 2026-11-12 | Chưa gán (Kha theo mô tả) | SCRUM-13, SCRUM-14, SCRUM-16 |
| [SCRUM-23](https://vku-lexora.atlassian.net/browse/SCRUM-23) | [T13] Adjudication + RQ1/RQ2 sơ bộ | 2026-11-16 | Chưa gán (Kha theo mô tả) | SCRUM-19, SCRUM-22 |
| [SCRUM-24](https://vku-lexora.atlassian.net/browse/SCRUM-24) | [T14] DK3/DK4 + runner bốn điều kiện | 2026-11-16 | Vũ | SCRUM-19, SCRUM-20 |
| [SCRUM-25](https://vku-lexora.atlassian.net/browse/SCRUM-25) | [T15] DEMO claims+structural, rerank pilot, bounded expansion | 2026-11-20 | Vũ | SCRUM-24 |
| [SCRUM-26](https://vku-lexora.atlassian.net/browse/SCRUM-26) | [T16] Kiểm tra qualifier/citation cho các chủ đề demo | 2026-11-20 | Chưa gán (Kha theo mô tả) | SCRUM-23, SCRUM-24 |
| [SCRUM-27](https://vku-lexora.atlassian.net/browse/SCRUM-27) | [T17] UI, clarification, lỗi/quota, smoke tests | 2026-11-24 | Vũ | SCRUM-21, SCRUM-25, SCRUM-26 |
| [SCRUM-28](https://vku-lexora.atlassian.net/browse/SCRUM-28) | [T18] Freeze MVP, lock dependencies, restore, video pilot | 2026-11-27 | Vũ | SCRUM-27, SCRUM-24, SCRUM-16 |
| [SCRUM-29](https://vku-lexora.atlassian.net/browse/SCRUM-29) | [T19] Preflight và chạy formal eval | 2026-12-02 | Vũ | SCRUM-28, SCRUM-23 |
| [SCRUM-30](https://vku-lexora.atlassian.net/browse/SCRUM-30) | [T20] Chấm, CI, error analysis, khóa bảng RQ | 2026-12-09 | Chưa gán (Kha theo mô tả) | SCRUM-29 |
| [SCRUM-31](https://vku-lexora.atlassian.net/browse/SCRUM-31) | [T21] Báo cáo, slide, demo, hướng dẫn setup | 2026-12-16 | Vũ | SCRUM-28, SCRUM-30 |
| [SCRUM-32](https://vku-lexora.atlassian.net/browse/SCRUM-32) | [T22] Phản biện thử, sửa lỗi, đóng gói | 2026-12-20 | Chưa gán (Kha theo mô tả) | SCRUM-31 |

## 10. Điểm cần người dùng review

- Chấp nhận phạm vi pilot hai văn bản, 10–15 units, một chủ đề và demo 08/11.
- Xác nhận giờ làm khả dụng của Vũ/Kha và khả năng cấp model runtime; hiện chưa có số liệu.
- Chấp nhận chỉ làm UI/source viewer tối thiểu, giữ private KB và UI đầy đủ sau pilot.
- Nếu yêu cầu upload/kho riêng bắt buộc ngay tuần này, cần quyết định phần việc thay thế trước khi triển khai.
- Không cần đồng bộ trạng thái cha/con vì chưa thấy mismatch. Chỉ chuyển review sau khi có artifacts và kết quả nghiệm thu.

## 11. Nguồn và giới hạn

- [Backlog local](technical-design-plan.md), [lịch triển khai](implementation-plan.md), [hợp đồng dữ liệu](../data-contracts.md).
- [T01](https://vku-lexora.atlassian.net/browse/SCRUM-11), [T04](https://vku-lexora.atlassian.net/browse/SCRUM-14), [T11](https://vku-lexora.atlassian.net/browse/SCRUM-21); danh mục đầy đủ ở mục 9.
- [GitHub repository](https://github.com/HuyVu12/Lexora); đã đọc tree main và truy vấn issue/PR, không push/fetch thay đổi vào checkout.
- Chỉ hoàn thành việc rà soát và chuẩn bị kế hoạch trong tác vụ này. Chưa triển khai demo, chưa thay đổi Jira/GitHub, chưa kiểm tra tài khoản Lightning hoặc tải nguồn pháp luật bên ngoài.
