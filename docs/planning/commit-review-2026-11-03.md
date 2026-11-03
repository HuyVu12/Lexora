# Bản bàn giao commit ngày 03/11/2026

Các thay đổi được chia thành ba commit local; chưa push GitHub.

| Commit | Phạm vi |
|---|---|
| `6e72ad1` | Snapshot/parser VBPL, source map, schema và evidence validator, BM25, provider boundary, fixtures và offline tests |
| `ea01272` | Candidate quy phạm, graph JSON/SQLite, dẫn chiếu, viewer thực thể/quan hệ và CLI |
| Commit chứa tài liệu này | Hướng dẫn chạy, báo cáo kiểm chứng và kế hoạch demo upload → review/confirm → chat |

## Kiểm chứng

Chạy tại workspace Lexora, Python 3.14.8 và Node 24.21:

```powershell
python -m unittest discover -s tests -v
node scripts/check_entity_graph_viewer.cjs data/kb/entity-relation-review/index.html
node scripts/check_graph_viewer.cjs data/kb/entity-relation-review/structure.html
```

Kết quả: 56 unittest đạt; cả hai DOM smoke đạt. DOM smoke không thay thế kiểm tra trực quan trên trình duyệt; browser host hiện không khả dụng.

Artifact local `data/kb/entity-relation-review` có 169 node, 227 edge, 8 candidate semantic và 4 fallback. Tất cả candidate cần người dùng review; đây chưa phải KB đã confirm. Dữ liệu nguồn, graph sinh ra, `.env` và các bản export Jira được loại khỏi Git. Xem [hướng dẫn tái tạo và review](local-pilot-review-2026-11-02.md).

## Phần còn thiếu của demo

Chưa có luồng upload PDF/TXT qua ứng dụng, job/KB ownership, lưu quyết định review và published revision, model transport thực tế, hoặc chat end-to-end. Provider hiện là boundary có cache/timeout; kiểm tra catalog 9Router không chứng minh quota hay inference hoạt động.

Xem [kế hoạch tuần và ngân sách đề xuất](demo-upload-review-chat-2026-11-03.md). Việc commit không đồng nghĩa nghiệm thu task Jira; cập nhật tiến độ phải giữ rõ phần đã làm và còn thiếu.
