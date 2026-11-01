# Guideline gán nhãn v0

Chọn 5 điều khoản pilot để thống nhất entity types, relation labels, đơn vị matching và quy tắc evidence. Dẫn chiếu rõ ràng ghi theo văn bản; thông tin không có nguồn ghi unknown. Không suy diễn quan hệ từ kiến thức ngoài corpus.

Sau khi chốt guideline, Kha và Vũ gán độc lập cùng mẫu 40–60 điều khoản; mỗi nhãn có unit_id, loại nhãn, evidence offsets và ghi chú. Không xem nhãn của nhau trước khi hoàn thành vòng độc lập. Lưu bất đồng và quyết định adjudication; tính kappa trên các đơn vị/nhãn đã căn chỉnh và F1 span/relation riêng. Ghi người chấm, ngày và guideline version.

Câu hỏi RAG cần reference answer, relevant unit IDs, loại câu và expected abstention. Mọi tình huống nhân tạo phải được ghi là giả định. Dùng dev để điều chỉnh pipeline; không dùng held-out làm ví dụ few-shot.
