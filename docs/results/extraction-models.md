# So sánh model trích xuất kho tri thức (ĐK3/ĐK4)

Tệp do `python -m legal_ai.cli kb-compare` sinh ra lúc 2026-11-08T07:47:52+00:00; không sửa tay.
Mọi lượt dùng cùng phạm vi thực nghiệm, cùng prompt `norm-llm-v1` và được kiểm chứng lại bằng cùng một bộ kiểm chứng.

| Model | Nhà cung cấp | Lượt OK / thử | Câu chưa có trả lời | ĐK3 | ĐK4 | Bị loại | Tính quy phạm chưa xác minh | Chi phí niêm yết |
|---|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | claude-code | 95/95 | 0 | 450 | 450 | 0 (0.0%) | 48.7% | 4.00 USD |
| `ollama/nemotron-3-nano:30b` | 9router | 3/8 | 80 | 5 | 3 | 2 (40.0%) | 40.0% | - |
| `ollama/gemma4:31b` | 9router | 93/95 | 37 | 446 | 304 | 142 (31.8%) | 32.3% | - |
| `ollama/gpt-oss:120b` | 9router | 95/95 | 0 | 416 | 385 | 31 (7.5%) | 13.5% | - |
| `ollama/nemotron-3-ultra:cloud` | 9router | 88/95 | 78 | 380 | 325 | 55 (14.5%) | 33.9% | - |
| `ollama/beam` | 9router | 76/95 | 218 | 265 | 247 | 18 (6.8%) | 26.4% | - |
| `ollama/nemotron-3-super` | 9router | 95/95 | 66 | 331 | 308 | 23 (6.9%) | 17.5% | - |

`ollama/nemotron-3-nano:30b` chỉ chạy mẫu 8/95 lượt; số ĐK3/ĐK4 của dòng này không so trực tiếp được với các lượt đầy đủ.

## Lượt gọi, token và thời gian

| Model | Lượt gọi (kể cả thử lại) | Tỉ lệ lượt lỗi | Câu có trả lời | Quy phạm / câu | Token vào | Token ra | Token suy luận | Token ra / quy phạm | Trung vị mỗi lượt | Tổng thời gian gọi |
|---|---|---|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | 95 | 0.0% | 100.0% | 0.78 | 334,129 | 136,506 | 47,365 | 303 | 11.0 s | 23.3 phút |
| `ollama/nemotron-3-nano:30b` | 10 | 70.0% | 29.8% | 0.15 | 41,297 | 153,304 | 0 | 30661 | 56.0 s | 10.6 phút |
| `ollama/gemma4:31b` | 95 | 2.1% | 93.6% | 0.83 | 289,303 | 78,813 | 0 | 177 | 3.0 s | 5.3 phút |
| `ollama/gpt-oss:120b` | 95 | 0.0% | 100.0% | 0.72 | 296,509 | 193,725 | 0 | 466 | 5.0 s | 8.7 phút |
| `ollama/nemotron-3-ultra:cloud` | 132 | 33.3% | 86.5% | 0.76 | 286,697 | 269,321 | 0 | 709 | 53.7 s | 163.8 phút |
| `ollama/beam` | 126 | 39.7% | 62.2% | 0.74 | 223,882 | 306,444 | 0 | 1156 | 57.4 s | 154.9 phút |
| `ollama/nemotron-3-super` | 103 | 7.8% | 88.6% | 0.65 | 294,052 | 296,367 | 0 | 895 | 18.2 s | 46.7 phút |

Thời gian mỗi lượt lấy từ `duration_ms` khi có; với lượt cũ là khoảng cách tới lượt kế tiếp trong cùng phiên (ước tính).
Token do nhà cung cấp báo về; token suy luận chỉ có khi model báo riêng.


## Lý do bị loại

- `claude-opus-5-5`: không có. Lượt gọi lỗi (mọi lần thử): không có.
- `ollama/nemotron-3-nano:30b`: hành vi không nguyên văn: 1, định lượng không nguyên văn: 1. Lượt gọi lỗi (mọi lần thử): invalid_output: 7.
- `ollama/gemma4:31b`: hành vi không nguyên văn: 88, từ tình thái bịa: 74, chủ thể không nguyên văn: 68, điều kiện không nguyên văn: 41, kết quả không nguyên văn: 24, đối tượng không nguyên văn: 20, từ tình thái mâu thuẫn: 17, bên nhận không nguyên văn: 12, thời hạn không nguyên văn: 9, định lượng không nguyên văn: 7, ngoại lệ không nguyên văn: 3, bên thụ hưởng không nguyên văn: 1. Lượt gọi lỗi (mọi lần thử): invalid_output: 2.
- `ollama/gpt-oss:120b`: hành vi không nguyên văn: 12, từ tình thái bịa: 10, điều kiện không nguyên văn: 9, từ tình thái mâu thuẫn: 9, bên thụ hưởng không nguyên văn: 1, trùng lặp: 1, đối tượng sai kiểu: 1. Lượt gọi lỗi (mọi lần thử): không có.
- `ollama/nemotron-3-ultra:cloud`: hành vi không nguyên văn: 29, từ tình thái bịa: 24, chủ thể không nguyên văn: 21, điều kiện không nguyên văn: 12, từ tình thái mâu thuẫn: 12, định lượng không nguyên văn: 6, bên nhận không nguyên văn: 3, bên thụ hưởng không nguyên văn: 2, thời hạn không nguyên văn: 2, đối tượng không nguyên văn: 2, kết quả không nguyên văn: 1. Lượt gọi lỗi (mọi lần thử): provider_unavailable: 10, provider_http_error: 28, invalid_output: 6.
- `ollama/beam`: hành vi không nguyên văn: 15, từ tình thái bịa: 15, chủ thể không nguyên văn: 13, điều kiện không nguyên văn: 3, ngoại lệ không nguyên văn: 3, kết quả không nguyên văn: 3, bên nhận không nguyên văn: 3. Lượt gọi lỗi (mọi lần thử): provider_unavailable: 10, provider_http_error: 40.
- `ollama/nemotron-3-super`: hành vi không nguyên văn: 16, chủ thể không nguyên văn: 8, bên thụ hưởng không nguyên văn: 3, điều kiện không nguyên văn: 2, từ tình thái bịa: 1, đối tượng không nguyên văn: 1. Lượt gọi lỗi (mọi lần thử): provider_unavailable: 8.

## Chèn lỗi có chủ đích (RQ2)

- `claude-opus-5-5`: bắt 98.9% lỗi thuộc loại phát hiện được, 1.3% lỗi ngữ nghĩa, loại nhầm 0.0% trên 450 bản ghi sạch (kb-validator-v3).
- `ollama/nemotron-3-nano:30b`: chưa chạy `kb-inject`.
- `ollama/gemma4:31b`: bắt 98.1% lỗi thuộc loại phát hiện được, 0.0% lỗi ngữ nghĩa, loại nhầm 0.0% trên 304 bản ghi sạch (kb-validator-v3).
- `ollama/gpt-oss:120b`: bắt 100.0% lỗi thuộc loại phát hiện được, 1.3% lỗi ngữ nghĩa, loại nhầm 0.0% trên 385 bản ghi sạch (kb-validator-v3).
- `ollama/nemotron-3-ultra:cloud`: bắt 97.4% lỗi thuộc loại phát hiện được, 0.0% lỗi ngữ nghĩa, loại nhầm 0.0% trên 325 bản ghi sạch (kb-validator-v3).
- `ollama/beam`: bắt 98.9% lỗi thuộc loại phát hiện được, 0.0% lỗi ngữ nghĩa, loại nhầm 0.0% trên 247 bản ghi sạch (kb-validator-v3).
- `ollama/nemotron-3-super`: bắt 98.0% lỗi thuộc loại phát hiện được, 1.3% lỗi ngữ nghĩa, loại nhầm 0.0% trên 308 bản ghi sạch (kb-validator-v3).

Chi phí chỉ có với Claude Code (giá niêm yết, trừ vào hạn mức gói); lượt qua 9Router không báo chi phí.
