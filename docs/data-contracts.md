# Hợp đồng dữ liệu v0 — dự thảo cần chốt 03/11

Bản dưới giữ làm tham chiếu thiết kế v0. Code local hiện thực thi `1.0.0-pilot`; xem [schema v1 và migration](planning/schema-v1-migration.md) cùng `tests/fixtures/contract-v1/` trước khi trao đổi JSONL. Chưa có tự động migration dữ liệu v0 thật hoặc contract nghiên cứu hoàn chỉnh.

| Đối tượng | Trường tối thiểu | Ràng buộc |
|---|---|---|
| Document | document_id, title, source_url, accessed_at, source_sha256, effective_from, effective_to, legal_status | ID ổn định; ngày ISO; không biết thì null, không tự đoán |
| LegalUnit | unit_id, document_id, parent_id, unit_type, label, text, normalized_sha256 | unit_type: chapter/article/clause/point; parent tồn tại khi có; ID không dùng số thứ tự dòng |
| Entity | entity_id, entity_type, name, unit_id, evidence | enum loại thực thể chốt sau pilot |
| Relation/Claim | claim_id, subject_id, predicate, object_id, evidence, extraction_run_id | quan hệ thuộc schema; giữ raw response riêng |
| Evidence | document_id, unit_id, quote, start, end, normalized_sha256 | offset ký tự Unicode, [start,end); quote == unit.text[start:end] |
| Validation | claim_id, schema_version, checks, decision, reasons | decision: accepted/rejected/needs_review; chỉ accepted vào ĐK4 |
| Question | question_id, category, question, relevant_unit_ids, reference_answer, split | split dev/held_out; không đưa đáp án vào context |
| Answer | question_id, condition, answer, citations, abstained, reason, run_id | citation trỏ đến unit và evidence cụ thể |

## Quy tắc evidence
Evidence neo vào bản chuẩn hóa bất biến, giữ snapshot gốc và mapping về trang/đường dẫn nguồn để người đọc kiểm tra. Mọi chỉnh sửa normalization tạo phiên bản mới; không giữ offset cũ. Trích dẫn sai offset/hash phải bị chặn, kể cả câu trả lời trông hợp lý.

## Dẫn chiếu và hiệu lực
Phân biệt tham chiếu tồn tại trong corpus với tham chiếu ngoài corpus chưa thu thập. Giữ pending/external trong báo cáo; không tự tạo đích tham chiếu. Validation ngày/trạng thái kiểm tra tính hợp lệ dữ liệu, không xác nhận kết luận pháp lý. Quan hệ sửa đổi/thay thế/hướng dẫn cần evidence.

## Phiên bản
Mỗi snapshot KB ghi schema_version, corpus_hash, extraction_config_hash và validation_config_hash. Khi thay schema, ghi migration và chạy lại validation/index. Không sửa trực tiếp dữ liệu held-out để cải thiện điểm.
