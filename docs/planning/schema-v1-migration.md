# Schema v1 pilot và migration từ v0

Ngày: 02/11/2026. Phiên bản thực thi: `1.0.0-pilot` trong `src/legal_ai/schemas/contract.py`. Đầu ra để review; chưa đóng toàn bộ T04.

Bổ sung ngày 03/11: contract chấp nhận tùy chọn `modality_evidence_ids` và slot `recipient` cho [graph thực thể–quy phạm](../features/entity-relation-graph.md). Claim cũ vẫn đọc được bằng runtime mới; runtime cũ cần nâng cấp trước khi đọc field/slot mới. Graph export mới dùng `evidence-graph-v2`, không đổi các artifact v1 đã tạo.

## Hợp đồng thực thi

- Document: thêm `schema_version`, `document_version_id`, `snapshot_id`, `synthetic`. Chỉ nhận `legal_status=unknown` trong pilot này; metadata đã xác minh cần mở rộng provenance trước khi cho trạng thái khác.
- LegalUnit: thêm `unit_version_id`, `document_version_id`, `source_start/end`, `source_locator`; hỗ trợ section/Mục. `text` là phần riêng của node, dừng trước node tiếp theo, không cộng lại toàn bộ nội dung con. Cần dựng context từ cây.
- Evidence: thêm `evidence_id`, `unit_version_id`; offset theo Unicode code point, `[start,end)`, tương đối với `LegalUnit.text`. Chuỗi quote phải tồn tại đúng một lần khi align; trường hợp trùng bị báo mơ hồ.
- Claim: thay triple v0 bằng `modality`, `slots`, `source_unit_version_ids`, `evidence_ids`, `extraction_run_id`, `extraction_scope`, `completeness`. Slot gồm `state`, `text`, `evidence_ids`; state là `present`, `unknown`, `not_present`.
- Validation: `claim_id`, `schema_version`, `decision`, `reasons`. Hiện mới kiểm tra tính toàn vẹn kỹ thuật; chưa có tất cả check V1–V7, temporal/reference/duplicate semantics hoặc đánh giá false rejection.

Enum modality: obligation, permission, prohibition, entitlement, definition, procedure, unknown. Slot hỗ trợ actor, beneficiary, counterparty, action, object, outcome, conditions, exceptions, scope, quantities, deadlines, references.

Quantities/deadlines hiện giữ nguyên text có evidence. Kiểu số/comparator/basis/trigger và cấu trúc AND/OR chưa triển khai; không coi schema pilot đã hoàn tất toàn bộ thiết kế NormClaim. Entity/graph views, Question và Answer contract hoàn chỉnh vẫn chờ phần tiếp theo.

## Định danh và source map

`source_sha256` và `snapshot_id` dùng SHA-256 bytes HTML tải về. `document_version_id` dùng hash text toàn văn chuẩn hóa; một HTML trang đổi navigation không tự tạo phiên bản nội dung pháp lý khác nếu text không đổi. Đây là version kỹ thuật, chưa xác nhận phiên bản pháp lý.

`normalized_sha256` = SHA-256 của JSON canonical gồm `normalization_version=nfc-newlines-v1` và `text`. `unit_version_id` = hash của document version, logical unit ID và text hash. `evidence_id` = hash của unit version, start và quote.

`source_start/end` neo vào text toàn văn chuẩn hóa. `normalized.json` lưu mỗi code point chuẩn hóa → span ký tự ở `source.txt` trước NFC. `paragraphs.json` ánh xạ span đó về số thứ tự thẻ p trong `content.html`, kèm HTML id/class nếu có. `p:nth-of-document(n)` là locator nội bộ, không phải CSS selector. Mapping nhiều-một bảo toàn cả cụm dấu; có thể trả span bao rộng cả cụm. Chưa có mapping PDF/trang/bounding box.

## Migration

1. Giữ snapshot v0 nguyên trạng. Không đổi nhãn schema rồi tái sử dụng offsets/hash cũ.
2. Trích toàn văn từ snapshot, chuẩn hóa lại và chạy parser để cấp phiên bản cùng source spans.
3. Với quote v0, align exact vào unit mới. Quote không tồn tại hoặc trùng vị trí phải review, không fuzzy accept.
4. Chuyển triple thành claim chỉ khi các slot có evidence rõ ràng. Thiếu thông tin để unknown và completeness unknown; không suy điều kiện/ngoại lệ từ triple đơn giản.
5. Chạy validator toàn bundle; dựng lại index từ artifact mới. Không trộn v0 và v1 trong cùng run.

Hiện repo chưa có dữ liệu v0 thật nên chưa có bản chuyển đổi v0 đã kiểm chứng. Fixture tại `tests/fixtures/contract-v1/` chứng minh JSONL roundtrip; đó là dữ liệu tổng hợp có nhãn, không phải kết quả LLM hoặc gold pháp lý.
