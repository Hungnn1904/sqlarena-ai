# Architectural Decision Records (`docs/DECISIONS.md`)

> SISF Trusted Control Surface — Ghi nhận các quyết định thiết kế trọng yếu và sự đánh đổi kỹ thuật của đồ án **SQLArena AI**.

## ADR-001: Tách Biệt Kho Đề Đã Duyệt (`Ready Staging Pool`) Khỏi Kệ Đang Mở (`Live Shelf`)
- **Bối cảnh**: Phiên bản cũ tự động chèn từng câu vừa `approved` trong `promotion.promote()` thẳng vào bộ đề đang mở, làm lộ đề lẻ tẻ ra màn hình học viên và chiếm mất `UNIQUE(question_id)` khiến bộ đề mới bị thiếu câu hỏi.
- **Quyết định**: Ngắt auto-insert tại `promotion.promote()`. Bổ sung `live.question_groups` + `live.question_group_items` (`0004_question_groups.sql`) để Giảng viên gom nhóm bằng kéo thả / tick hàng loạt rồi mới phát hành nguyên khối (`append_active` hoặc `new_weekly_set`).
- **Đánh đổi**: Thêm 2 bảng nhẹ nhưng bảo toàn 100% cả 18 bài kiểm thử `weekly_sets` gốc và trao quyền kiểm soát tuyệt đối thời điểm phát hành đề cho Giảng viên.

## ADR-002: Kiểm Duyệt Hiệu Chỉnh Hai Chế Độ (`Calibrated` vs `Strict`)
- **Bối cảnh**: Kiểm định tự động bị nghẽn bởi các quy tắc hình thức (bắt khớp alias tiếng Anh ẩn của Model A khi đề tiếng Việt không nêu, đánh rớt cả câu khi `2/3` mẫu đúng nhưng 1 mẫu vấp cú pháp JSON, cắt `max_tokens = 500` trên Gateway).
- **Quyết định**: Giữ mặc định `calibrated=False` ở hàm lõi `ai/review.py` (bảo toàn 104 unit tests gốc), kích hoạt `review.approval_mode = "calibrated"` ở tầng ứng dụng Backend:
  - **Chốt chặn bất khả xâm phạm**: `pglast` AST chỉ đọc, thực thi thật trên `enterprise_db` (`row_count > 0`, khớp hash khi chạy lại), `0` mẫu hợp lệ bất đồng kết quả, bắt buộc `ORDER BY` khi đề yêu cầu, và chặn trùng lặp `>= 0.72`.
  - **Gỡ bỏ rớt oan**: Chấp nhận `>= 2/3` mẫu hợp lệ đồng thuận 100%, linh hoạt alias không nêu trong đề, tự bù khóa ngoại `FK` thiếu cho Model A, bật lại `REVIEW_REPAIR_ROUNDS=1` và nâng `max_tokens` (`1500/1200`).

## ADR-003: Định Tuyến Same-Origin Qua Nginx Reverse Proxy Cho VPS Không Có Domain
- **Bối cảnh**: Next.js `output: 'export'` đóng cứng biến `NEXT_PUBLIC_API_URL` lúc build. Nếu để `http://127.0.0.1:8000`, người dùng từ máy khác mở `http://<VPS_IP>:3000` sẽ gọi nhầm về máy cá nhân của họ (`ERR_CONNECTION_REFUSED`).
- **Quyết định**: Cấu hình `frontend/nginx.conf` chuyển tiếp `location /api/` sang `http://backend:8000` nội bộ Docker, kết hợp `resolveApiBase()` dùng đường dẫn tương đối `''` trên bản production và khóa cổng PostgreSQL vào `127.0.0.1`.

## ADR-004: Quản Lý Khóa `apithat.dev` Theo Cơ Chế Secret-Blind & Tự Động Khám Phá Model
- **Bối cảnh**: Các khóa tạo trên `https://apithat.dev/keys` có thể thuộc nhiều nhóm kênh khác nhau (`auto`, `GPT-pro`, `GPT-max`, `claude-kiro`...) và không được phép lộ trong lịch sử chat hay Git.
- **Quyết định**: Triển khai `probe_apithat_key()` tự động lấy danh sách model khả dụng từ `/v1/models` (ưu tiên `gpt-5.6-sol`, `gpt-6.1-terra`, `gpt-6-sol`, `gpt-6-astra`, `claude-sonnet-5-5`) và cung cấp 2 kênh nạp khóa ẩn (`./scripts/set-apithat-key.sh` + ô nhập `password` tại trang Quản trị chỉ lưu bản che `sk-a...xxxx` trong nhật ký kiểm toán).
