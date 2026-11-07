# So sánh model trích xuất kho tri thức (ĐK3/ĐK4)

Tệp do `python -m legal_ai.cli kb-compare` sinh ra lúc 2026-11-07T18:29:56+00:00; không sửa tay.
Mọi lượt dùng cùng phạm vi thực nghiệm, cùng prompt `norm-llm-v1` và được kiểm chứng lại bằng cùng một bộ kiểm chứng.

| Model | Nhà cung cấp | Lượt OK / thử | Câu chưa có trả lời | ĐK3 | ĐK4 | Bị loại | Tính quy phạm chưa xác minh | Chi phí niêm yết |
|---|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | claude-code | 95/95 | 0 | 450 | 450 | 0 (0.0%) | 48.7% | 4.00 USD |
| `ollama/nemotron-3-nano:30b` | 9router | 3/8 | 80 | 5 | 3 | 2 (40.0%) | 40.0% | - |
| `ollama/gemma4:31b` | 9router | 93/95 | 37 | 446 | 304 | 142 (31.8%) | 32.3% | - |
| `ollama/gpt-oss:120b` | 9router | 95/95 | 0 | 416 | 385 | 31 (7.5%) | 13.5% | - |

`ollama/nemotron-3-nano:30b` chỉ chạy mẫu 8/95 lượt; số ĐK3/ĐK4 của dòng này không so trực tiếp được với các lượt đầy đủ.

## Lý do bị loại

- `claude-opus-5-5`: không có. Lượt lỗi: không có.
- `ollama/nemotron-3-nano:30b`: hành vi không nguyên văn: 1, định lượng không nguyên văn: 1. Lượt lỗi: invalid_output: 5.
- `ollama/gemma4:31b`: hành vi không nguyên văn: 88, từ tình thái bịa: 74, chủ thể không nguyên văn: 68, điều kiện không nguyên văn: 41, kết quả không nguyên văn: 24, đối tượng không nguyên văn: 20, từ tình thái mâu thuẫn: 17, bên nhận không nguyên văn: 12, thời hạn không nguyên văn: 9, định lượng không nguyên văn: 7, ngoại lệ không nguyên văn: 3, bên thụ hưởng không nguyên văn: 1. Lượt lỗi: invalid_output: 2.
- `ollama/gpt-oss:120b`: hành vi không nguyên văn: 12, từ tình thái bịa: 10, điều kiện không nguyên văn: 9, từ tình thái mâu thuẫn: 9, bên thụ hưởng không nguyên văn: 1, trùng lặp: 1, đối tượng sai kiểu: 1. Lượt lỗi: không có.

## Chèn lỗi có chủ đích (RQ2)

- `claude-opus-5-5`: bắt 98.9% lỗi thuộc loại phát hiện được, 1.3% lỗi ngữ nghĩa, loại nhầm 0.0% trên 450 bản ghi sạch (kb-validator-v3).
- `ollama/nemotron-3-nano:30b`: chưa chạy `kb-inject`.
- `ollama/gemma4:31b`: bắt 98.1% lỗi thuộc loại phát hiện được, 0.0% lỗi ngữ nghĩa, loại nhầm 0.0% trên 304 bản ghi sạch (kb-validator-v3).
- `ollama/gpt-oss:120b`: bắt 100.0% lỗi thuộc loại phát hiện được, 1.3% lỗi ngữ nghĩa, loại nhầm 0.0% trên 385 bản ghi sạch (kb-validator-v3).

Chi phí chỉ có với Claude Code (giá niêm yết, trừ vào hạn mức gói); lượt qua 9Router không báo chi phí.
