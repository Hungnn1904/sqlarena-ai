# 🇬🇧 Plan: Per-Question SQL Discussion & 1-Level Threaded Comments (`261127-2013`)  
🇻🇳 *(Kế hoạch: Khu vực Thảo luận / Bình luận 1 cấp độc lập theo từng bài SQL)*

## 1. 🇬🇧 Scope & Isolation Invariants  
*(🇻🇳 1. Phạm vi & Các bất biến tách biệt hệ thống)*

- 🇬🇧 **Strict Separation from Error Reports (`live.question_reports`)**: `live.question_comments` is a dedicated public learning discussion table; posting or deleting comments never mutates `live.question_reports`, `live.question_votes`, or `live.questions.is_flagged`.  
  🇻🇳 *(Tách biệt hoàn toàn với Báo lỗi / Góp ý: `live.question_comments` là bảng thảo luận học tập độc lập; đăng/xóa bình luận không bao giờ tác động tới bảng báo lỗi hay cờ `is_flagged`.)*

- 🇬🇧 **Participation & Reputation Badges**: Logged-in users can read all comments on published questions; posting/replying requires `live.submissions >= 1` (`409 SUBMISSION_REQUIRED` if `0` attempts) except `role == 'admin'` (always unlocked); badges resolve automatically to `Quản trị viên`, `Đã giải đúng`, or `Đã thử làm`.  
  🇻🇳 *(Điều kiện tham gia & Nhãn uy tín tự động: Mọi tài khoản đăng nhập đều đọc được bình luận; viết bình luận/trả lời yêu cầu nộp bài ít nhất 1 lần trừ `admin`; nhãn uy tín tự động gắn `Quản trị viên`, `Đã giải đúng`, hoặc `Đã thử làm`.)*

---

## 2. 🇬🇧 Phases  
*(🇻🇳 2. Các giai đoạn thực thi)*

- [x] 🇬🇧 **Phase 01 — PostgreSQL Migration `0007`, TDD Suite & Comments REST APIs (`phase-01-backend-comments-and-tdd.md`)** (`2026-11-27 20:18`)  
  🇻🇳 *(Giai đoạn 01 — Migration PostgreSQL `0007`, Bộ kiểm thử TDD và 3 REST API Thảo luận)*

- [x] 🇬🇧 **Phase 02 — Bottom Independent `Thảo luận (N)` Card, Reviewer Sign-Off & `main`/`production` Sync (`phase-02-frontend-discussion-card-and-sync.md`)** (`2026-11-27 20:32`)  
  🇻🇳 *(Giai đoạn 02 — Khối Card độc lập `Thảo luận (N)` cuối trang Làm bài, Kiểm toán độc lập và Đồng bộ nhánh `main`/`production`)*

---

## 3. 🇬🇧 Resume From Here  
*(🇻🇳 3. Điểm tiếp tục công việc)*

- 🇬🇧 Active Phase: `Completed` (`2026-11-27 20:32` — Round-2 `code-reviewer` signed off `ZERO BLOCKING FINDINGS`; synchronized `origin/main` and `origin/production`).  
  🇻🇳 *(Giai đoạn hiện tại: Đã hoàn tất lúc `2026-11-27 20:32` — `code-reviewer` vòng 2 xác nhận `0` lỗi chặn; đã đồng bộ cả hai nhánh `origin/main` và `origin/production`.)*
