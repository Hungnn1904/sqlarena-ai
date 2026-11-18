# Changelog — SQLArena AI

## [2.3.0] — 2026-11-18 (Gộp 1 Cổng Đăng Nhập Thống Nhất, Phân Chia Path Theo Role `RBAC` & Seed Data Thật 100%)

### Changed
- **Gộp 1 Khung Đăng Nhập/Đăng Ký Duy Nhất & Chia Đường Dẫn Theo Role (`/` · `/progress` · `/leaderboard` · `/admin`)**: Không còn tách rời form đăng nhập Học viên và Quản trị viên; người dùng không cần truy cập `/admin` trước để đăng nhập Admin. Sau khi xác thực, tài khoản `learner` được định tuyến vào `/`, `/progress`, `/leaderboard` (tự chuyển hướng khỏi `/admin`), còn tài khoản `admin` có đầy đủ cả 3 đường dẫn làm bài của người dùng cộng thêm `/admin`.
- **Xóa Bỏ Mật Khẩu Mặc Định Cứng & Chuẩn Hóa Seed Data Thực Tế (`auth.py`, `seed.py`, `README.md`)**: Gỡ bỏ hoàn toàn nhánh fallback mật khẩu chuỗi cứng trong `auth.verify_password()` (bắt buộc băm `PBKDF2-HMAC-SHA256`); toàn bộ câu hỏi, bản nháp và lịch sử nộp bài trong `seed.py` đều thực thi trực tiếp trên `enterprise_db` thật của PostgreSQL 17; cập nhật `README.md` rõ ràng cho người mới `git clone`.

---

## [2.2.0] — 2026-11-18 (Vá Phản Hồi Đồng Đội Đạt & Hưng: Bảng Màu Gốc, Tìm Kiếm Chính Xác Mã Bài & Phân Quyền Admin)

### Fixed
- **Tìm kiếm chính xác mã bài (`SQL1`, `SQL2`, `#2`, `2`)**: Loại bỏ so khớp tiền tố `.startsWith()` và `question_id` ẩn ở cả `LearnerWorkbench.tsx` lẫn `backend/app/services/weekly.py`, đảm bảo gõ `SQL2` hoặc `SQL1` chỉ trả về đúng bài ở vị trí tương ứng (không lôi theo `SQL20`, `SQL22` hay câu có `question_id = 12..15`), đồng thời đưa sắp xếp mặc định về đúng thứ tự bộ đề (`SQL1..SQLN`).
- **Màn hình chưa đăng nhập tối giản**: Gỡ bỏ toàn bộ khối Hero quảng cáo và bảng truy vấn mẫu giả lập trên `home-client.tsx`, chỉ giữ thanh tiêu đề `SQLArena` và thẻ `Đăng nhập / Đăng ký` gọn ở trung tâm.
- **Đăng nhập Admin trên `:3000` & Hiển thị đúng vai trò**: Khắc phục lỗi gắn cứng nhãn `"Học viên"` dưới tên tài khoản Admin trong `AuthBar.tsx`; tài khoản `role=admin` khi đăng nhập ở `:3000` tự mở trang `Quản trị` và có tab `Quản trị` trên thanh điều hướng (trong khi tài khoản Học viên `role=learner` vẫn ẩn 100% nút Quản trị). Bổ sung sẵn tài khoản mẫu `hocvien / hocvien123` trong `seed.py`.
- **Khôi phục Bảng màu gốc của nhóm (`Editorial Sage & Warm Paper`)**: Khôi phục hệ token màu giấy ấm `#F5EDDC` / `#FBF7EC`, xanh xô thơm `#4D6F61` / `#7DA796` (đạt chuẩn tương phản WCAG AA trên cả Sáng/Tối) và lưới nền 48px trong `globals.css` & `frontend/DESIGN.md`.
- **Đồng bộ đáp án chấm điểm & Nhóm đề tuần mới**: Cập nhật `ON CONFLICT DO UPDATE` cho `live.test_cases` trong `promotion.py` khi duyệt lại bản nháp đã sửa `custom_sql`, tháo xung đột `409 QUESTION_ALREADY_USED` khi phát hành nhóm đề sang tuần mới trong `groups.py`, sửa hiển thị nhãn `"Đang thử"` (`attempt_count`), và chia sẻ khóa `apithat.dev` qua volume `.runtime` giữa `backend` và `worker`.

---

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
