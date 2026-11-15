# research

Dữ liệu nghiên cứu cho ĐK1-ĐK4, lưu trong tệp SQLite của workspace.

- `corpus.py` `CorpusStore` (`corpus-store-v1`): văn bản bất biến (bản gốc, văn bản chuẩn hóa, đơn vị, cảnh báo parser), khóa phiên bản có mã băm, xuất bundle cho `run-retrieval`, chuyển phiên bản sang máy khác.
  Trên máy chủ chỉ có dòng lệnh, `cli corpus-version-export` ghi một phiên bản đã khóa (hàng văn bản, bản gốc, mã băm) ra một tệp JSON và `cli corpus-version-import` thêm nó vào store khác với cùng mã phiên bản và mã băm bundle (`--expect-version` để từ chối tệp nhầm); nhập lại lần nữa không đổi gì.
- `questions.py` `QuestionStore` (`questions-store-v1`): bộ câu hỏi trên phiên bản đã khóa, nhãn của từng người, gói câu hỏi và tệp nhãn, kappa và Dice, chốt nhãn cuối, khóa và chia dev/held-out.
- `proposals.py`: đề xuất nhãn (ứng viên BM25, schema chỉ cho chọn đơn vị ứng viên) và soạn nháp câu hỏi; prompt ở `prompts/`.

- `enumeration.py` (`enumeration-draft-v1`, `cli enum-drafts`): bộ liệt kê nháp suy ra từ gold trích xuất đã đối soát, kèm bảng kiểm lại cho hai người.

Hướng dẫn: `docs/features/question-annotation.md`, `docs/annotation-guidelines.md`. Test: `tests/test_corpus.py`, `tests/test_questions.py`, `tests/test_proposals.py`.
