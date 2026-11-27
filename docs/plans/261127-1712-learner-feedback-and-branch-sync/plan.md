# 🇬🇧 Plan: Learner Question Voting, Error Flagging & Human-in-the-Loop Resolution (`261127-1712`)  
🇻🇳 *(Kế hoạch: Bình chọn câu hỏi, Báo lỗi / Góp ý của Người học & Quy trình Quản trị viên xử lý Human-in-the-loop)*

## 1. 🇬🇧 Spec Parity Audit (`Part 1` & `Part 2` AI Dossier vs New Learner Feedback Spec)  
*(🇻🇳 1. Đối chiếu độ khớp đặc tả giữa Phần 1/2 AI Dossier và Tính năng Báo lỗi mới của Đạt)*

- 🇬🇧 **Part 1 (Live 5-Step Pipeline Stepper & Sub-Step Telemetry)**: Already implemented on `main` (`42d03c6`) in `backend/app/services/draft_dossier.py`, `backend/app/pipeline/review.py`, and `frontend/src/components/DraftTelemetryViews.tsx`; add explicit queue-wait label (`Đang chờ hàng đợi...`) when a draft is `pending` with zero active calls.  
  🇻🇳 *(Phần 1 — Thanh tiến trình 5 bước & Thông số trực tiếp: Đã có trên `main` (`42d03c6`); bổ sung thêm nhãn `Đang chờ hàng đợi...` rõ ràng khi bản nháp đang chờ worker lấy xử lý.)*

- 🇬🇧 **Part 2A (5-Block Technical Acceptance Dossier in `"Xem đề"`)**: Verified 100% present on `main` (`42d03c6`) covering Block 1 (`Verdict`), Block 2 (`Originality & TF-IDF`), Block 3 (`Model B Consensus Matrix`), Block 4 (`6-Point Semantic Checklist`), and Block 5 (`Repair History & Pedagogical Traps`).  
  🇻🇳 *(Phần 2A — Hồ sơ nghiệm thu kỹ thuật 5 khối trong `"Xem đề"`: Đã khớp đầy đủ cả 5 khối trên nhánh `main` (`42d03c6`).)*

- 🇬🇧 **Part 2B (NEW — Learner Voting, Flagging Comment & Admin 3-Way Resolution)**: Missing in codebase; implemented in this plan and synchronized across both `origin/main` and `origin/production`.  
  🇻🇳 *(Phần 2B — MỚI: Bình chọn 👍/👎, Báo lỗi / Góp ý của Người học và 3 hướng xử lý của Quản trị viên trong Ngân hàng đề: Chưa có trong code; được triển khai trọn vẹn trong kế hoạch này và đồng bộ cả hai nhánh `main` và `production`.)*

---

## 2. 🇬🇧 Phases  
*(🇻🇳 2. Các giai đoạn thực thi)*

- [x] 🇬🇧 **Phase 01 — PostgreSQL Schema (`0006`), TDD Suite & Feedback REST APIs (`phase-01-backend-feedback-and-tdd.md`)** (`2026-11-27 17:23`)  
  🇻🇳 *(Giai đoạn 01 — Lược đồ PostgreSQL `0006`, Bộ kiểm thử TDD và hệ thống REST API Bình chọn / Báo lỗi / Xử lý)*

- [x] 🇬🇧 **Phase 02 — Learner Feedback Bar, Admin Question Bank Resolution UI & `main`/`production` Sync (`phase-02-frontend-feedback-and-branch-sync.md`)** (`2026-11-27 17:46`)  
  🇻🇳 *(Giai đoạn 02 — Thanh Bình chọn / Báo lỗi phía Người học, Giao diện Xử lý góp ý tại Ngân hàng đề Admin và Đồng bộ nhánh `main`/`production`)*

---

## 3. 🇬🇧 Resume From Here  
*(🇻🇳 3. Điểm tiếp tục công việc)*

- 🇬🇧 Active Phase: `Completed` (`2026-11-27 17:46` — Round-2 `code-reviewer` signed off `ZERO BLOCKING FINDINGS`; synchronized `origin/main` and `origin/production`).  
  🇻🇳 *(Giai đoạn hiện tại: Đã hoàn tất lúc `2026-11-27 17:46` — `code-reviewer` vòng 2 xác nhận `0` lỗi chặn; đã đồng bộ hoàn toàn `origin/main` và `origin/production`.)*
