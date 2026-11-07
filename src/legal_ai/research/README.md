# research

Dữ liệu nghiên cứu cho ĐK1-ĐK4, lưu trong tệp SQLite của workspace.

- `corpus.py` `CorpusStore` (`corpus-store-v1`): văn bản bất biến (bản gốc, văn bản chuẩn hóa, đơn vị, cảnh báo parser), khóa phiên bản có mã băm, xuất bundle cho `run-retrieval`, chuyển phiên bản sang máy khác.
- `questions.py` `QuestionStore` (`questions-store-v1`): bộ câu hỏi trên phiên bản đã khóa, nhãn của từng người, gói câu hỏi và tệp nhãn, kappa và Dice, chốt nhãn cuối, khóa và chia dev/held-out.
- `proposals.py`: đề xuất nhãn (ứng viên BM25, schema chỉ cho chọn đơn vị ứng viên) và soạn nháp câu hỏi; prompt ở `prompts/`.

Hướng dẫn: `docs/features/question-annotation.md`, `docs/annotation-guidelines.md`. Test: `tests/test_corpus.py`, `tests/test_questions.py`, `tests/test_proposals.py`.
