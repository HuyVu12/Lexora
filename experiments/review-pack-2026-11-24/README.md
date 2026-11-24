# Gói duyệt nhãn 24/11/2026

Trang duyệt cho Vũ: agent Claude soạn sẵn kết luận, Vũ chỉ đọc, chọn và sửa khi cần.
Kha làm cùng nội dung ở chế độ không gợi ý (`?blind=1`) hoặc trên máy chủ gán nhãn.
Quyết định và hệ quả phương pháp: dòng ngày 24/11/2026 của `docs/decisions.md`.
Mọi gợi ý là của model, không phải kết luận pháp lý; Vũ là người quyết định.

## Định dạng dữ liệu

Mỗi việc là một tệp `data/<việc>.json`:

```json
{
  "task": "validity | link | amendment | audit",
  "title": "Tên việc hiển thị",
  "instructions": "Hướng dẫn ngắn bằng tiếng Việt, mỗi câu một dòng",
  "drafted_by": "claude-opus-5-5 (agent trong phiên, 24/11/2026)",
  "options": [{"value": "dong_y", "label": "Đồng ý", "hint": "giải thích ngắn"}],
  "items": [
    {
      "id": "mã dòng duy nhất, khớp bảng gốc",
      "group": "nhóm để lọc (ví dụ mã câu hỏi hoặc loại liên kết)",
      "heading": "tiêu đề ngắn của mục",
      "question": "câu hỏi kiểm cần trả lời cho mục này",
      "fields": [{"label": "Nguyên văn đơn vị A", "text": "...", "highlight": ["cụm cần chú ý"]}],
      "suggestion": {"value": "một value trong options", "reason": "lý do ngắn, chỉ dựa trên nguyên văn", "confidence": "cao | vừa | thấp",
                     "quotes": [{"label": "Điều 21 khoản 1 BLLĐ", "text": "trích nguyên văn"}]},
      "export": {"cột gốc": "giá trị để xuất lại đúng định dạng bảng gốc"}
    }
  ]
}
```

Việc gold là `data/gold.json`, cùng khung nhưng mỗi mục có:

```json
{
  "id": "row_key của câu trong bộ gold g5c82c09634e2",
  "group": "mã Điều",
  "heading": "tên đơn vị",
  "sentence": "nguyên văn câu",
  "context": "câu dẫn của đơn vị cha nếu có",
  "draft": [{"modality": "...", "cue": "...", "slots": {"actor": "...", "action": "..."}}],
  "reason": "lý do ngắn",
  "confidence": "cao | vừa | thấp"
}
```

`draft` dùng đúng dạng `norms` mà `src/legal_ai/research/gold.py` (`_clean`) nhận; `[]` nghĩa là câu không có quy phạm.
Mọi giá trị ô phải là chuỗi con nguyên văn của câu.

## Kết quả duyệt

Trang lưu tự động trong trình duyệt và xuất `review-<việc>-<người>.json`:
`{"task", "reviewer", "mode": "suggestions | blind", "exported_at", "items": [{"id", "value", "note", "changed_from_suggestion", "edited_norms"?}]}`.
`scripts/review_pack/` chuyển tệp này về định dạng của Lexora (tệp nhãn gold `lexora-gold-labels-v1`, CSV của bảng gốc, nhãn kiểm tra quy phạm bị loại).
