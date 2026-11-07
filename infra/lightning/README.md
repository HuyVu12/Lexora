# Vận hành Lightning AI: kế hoạch, chưa dùng

> Cập nhật 07/11/2026: mô hình ngôn ngữ cho ĐK3/ĐK4 và sinh câu trả lời đã chốt là Opus 5.5 qua Claude Code (xem `docs/decisions.md`), nên chưa cần GPU cho phần này.
> GPU Lightning chỉ còn dự kiến cho embedding, reranker hoặc model mã nguồn mở nếu nhóm đo và chọn chúng ở bước truy xuất; các nguyên tắc dưới đây vẫn áp dụng khi đó.

Người dùng dự định dùng Lightning AI và tài nguyên miễn phí; chưa duyệt ngân sách. Không dựa vào giả định GPU miễn phí liên tục.

Kiểm tra nguồn chính thức ngày 31/10/2026: https://lightning.ai/pricing và https://support.lightning.ai/docs/platform/overview/faq/billing/ . Trang giá phân biệt free Studio và credit GPU; quota/điều kiện có thể thay đổi. Kiểm tra quota thực trong tài khoản trước khi chốt model, không coi con số quảng bá là tài nguyên nhóm chắc chắn có.

1. Chuẩn bị dữ liệu, dependencies và kiểm thử CPU trước khi bật GPU.
2. Pilot 10–15 điều khoản và một tập câu hỏi nhỏ; đo VRAM, thời gian extraction/embedding/generation, số retry.
3. Ước lượng tổng chi phí theo thời gian đo × số batch; 600 lượt sinh chính thức là mức tối thiểu cho 150 câu × 4 điều kiện.
4. Cache bằng hash(input + model revision + prompt + config). Chia batch nhỏ, ghi checkpoint sau mỗi batch, resume không chạy lại kết quả đã có.
5. Lưu bản sao manifest, dữ liệu và kết quả ngoài phiên chạy; kiểm tra khôi phục trước thực nghiệm.
6. Tắt GPU sau batch. Không ghi token trong notebook hoặc Git. Không tự động fallback sang API trả phí.

Model ID/revision, thư viện và lockfile phải được chốt sau pilot. Nếu dùng free API, kiểm tra quota, model version, điều kiện sử dụng và khả năng tái lập; lưu raw output. Không trộn backend giữa các điều kiện mà không báo cáo thành thí nghiệm riêng.
