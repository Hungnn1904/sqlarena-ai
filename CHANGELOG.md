# Changelog — SQLArena AI

## [2.0.0] — 2026-11-17 (Chuẩn hoá Đồ án MyKit v3.15, Question Groups, Calibrated AI & VPS Docker)

### Added
- **Hệ thống Gom nhóm & Đăng đề hàng loạt (`0004_question_groups`)**: Bổ sung bảng `live.question_groups` + `live.question_group_items`, bộ API `/api/v1/admin/question-groups/*` và giao diện 2 cột hỗ trợ kéo thả (`Drag & Drop`), tick chọn nhiều đề, sắp xếp thứ tự và đăng nguyên nhóm lên kệ trong 1 giao dịch nguyên tử (`append_active` / `new_weekly_set`).
- **Duyệt hàng loạt & Soạn đề thủ công**: Thêm `POST /api/v1/admin/drafts/bulk-approve`, tùy chọn sửa trực tiếp `custom_sql` khi duyệt bản nháp, và `POST /api/v1/admin/questions/manual` kiểm chứng trực tiếp trên PostgreSQL 17.
- **Tích hợp `apithat.dev` Secret-Blind Vault**: Tự động khám phá danh sách model theo nhóm khóa qua `/v1/models` (`gpt-5.6-sol`, `gpt-6.1-terra`, `gpt-6-sol`, `gpt-6-astra`, `claude-*`), bổ sung API `/api/v1/admin/gateway-status`, `/api/v1/admin/gateway-key`, giao diện nhập khóa ẩn trên trang Quản trị và công cụ CLI `./scripts/set-apithat-key.sh`.
- **Triển khai VPS không cần Domain (`scripts/deploy-vps.sh`)**: Định tuyến cùng nguồn `/api/` qua Nginx Reverse Proxy trên cổng `:3000`, tự động phát hiện xung đột cổng, xử lý đường dẫn Unicode cho Docker BuildKit và hỗ trợ `--rollback` về Last-Known-Good SHA.
- **Bộ tài liệu & Sơ đồ chuẩn MyKit v3.15**: Chuẩn hoá `AGENTS.md`, `CLAUDE.md`, `frontend/DESIGN.md`, `docs/{LAW,ARCHITECTURE,WBS,DECISIONS,REVIEW}.md`, `docs/api/OPENAPI_V1.md` và sơ đồ vector `docs/diagrams/*.svg`.

### Changed
- **Chế độ Kiểm duyệt Hiệu chỉnh (`review.approval_mode = "calibrated"`)**: Giữ nguyên 100% chốt chặn an toàn/đồng thuận kết quả trên PostgreSQL 17, đồng thời loại bỏ các lỗi rớt oan hình thức (alias tiếng Anh không nêu trong đề, `>=2/3` mẫu hợp lệ đồng thuận tuyệt đối, chuẩn hoá cột FK thiếu cho Model A, khôi phục `REVIEW_REPAIR_ROUNDS` và nâng `max_tokens` lên `1500/1200`).
- **Ngắt Auto-Leak khi duyệt đề**: `promotion.promote()` chỉ đưa câu hỏi vào kho `live.questions (status='ready')`, không tự chèn lẻ tẻ vào bộ đề đang mở.
- **Đại tu UX góc nhìn Người mới**: Khắc phục lỗi tương phản chữ trên nút nền đậm ở Light Mode, khôi phục font `monospace` (`tabular-nums`), nâng cỡ chữ đề bài lên `16px`, thay auto-login ngầm bằng màn hình chào mừng tường minh, lưu nháp SQL theo bài, hiển thị `PK`/`FK`, `output_columns`, cho phép SQL comment `--` / `/* */` và tích hợp thanh trợ lý `AI Coach` + `EXPLAIN`.

### Removed
- Dọn sạch 25 tệp `.md` nháp lịch sử bị trùng lặp hoặc lỗi thời trong `docs/`, `ai/`, `backend/`, `frontend/`, `seed_create/`, `tai_lieu/` và cấu hình `.ck.json` cũ.

---

## [1.0.0] — 2026-10-29
- Khởi tạo kiến trúc nền tảng SQLArena v7: PostgreSQL 17 (`sqlarena_app` + `enterprise_db` 13 bảng, 50 câu hỏi nguồn `ENT-001..ENT-050`), Dual-Model Pipeline (Model A + Model B), Bộ đề tuần (`weekly_sets`), Sandbox chỉ đọc và hệ thống chấm điểm/xếp hạng.
