# rag

`review_chat.py` cung cấp chat theo revision, evidence bundle chỉ từ claim được người dùng duyệt, lexical retrieval, generation tùy chọn và citation gate. Chưa có dense retrieval hoặc nghiên cứu ĐK1–ĐK4 hoàn chỉnh.

Python 3.11+, stdlib, không cần cài package. Ứng dụng web gọi vào module này qua `python -m legal_ai.web` (cần `.venv` có extra `web`); hướng dẫn và prerequisite cụ thể tại `docs/features/reviewed-kb-chat.md`. Kiểm thử offline: `python -m unittest discover -s tests -v`. Citation gate kiểm tra nguồn thuộc bundle, không chứng minh tính đúng ngữ nghĩa hoặc hiệu lực pháp luật.
