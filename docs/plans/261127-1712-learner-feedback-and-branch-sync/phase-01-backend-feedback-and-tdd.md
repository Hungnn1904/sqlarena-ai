# 🇬🇧 Phase 01 — PostgreSQL Schema (`0006`), TDD Suite & Feedback REST APIs  
🇻🇳 *(Giai đoạn 01 — Lược đồ PostgreSQL `0006`, Bộ kiểm thử TDD & Hệ thống REST API Phản hồi)*

- 🇬🇧 **Status**: `Completed` (`2026-11-27 17:23`)  
  🇻🇳 *(Trạng thái: Đã hoàn tất lúc `2026-11-27 17:23`.)*

- 🇬🇧 **Evaluator**: `pytest` on PostgreSQL 17 + `clean-arch-gate.cjs`  
  🇻🇳 *(Bộ kiểm định: `pytest` trên PostgreSQL 17 thật và `clean-arch-gate.cjs`.)*

- 🇬🇧 **Tasks**:  
  🇻🇳 *(Danh sách đầu việc:)*

  - [x] 🇬🇧 Write failing PostgreSQL 17 TDD suite `backend/tests/test_question_feedback.py` covering submission-gated voting, 1-open-report partial unique constraint, non-auto-locking invariant, and all 3 Admin resolution paths (`rework`, `retire`, `dismiss`).  
    🇻🇳 *(Viết bộ test TDD `backend/tests/test_question_feedback.py` kiểm tra điều kiện bình chọn sau ít nhất 1 lần nộp bài, giới hạn 1 báo lỗi `open`/người/câu, nguyên tắc không tự khóa đề, và cả 3 hướng xử lý của Admin.)*

  - [x] 🇬🇧 Add `backend/db/0006_question_feedback.sql`, `backend/alembic/versions/0006_question_feedback.py`, and idempotent DDL in `backend/app/db.py` (`ensure_runtime_schema`) for `live.question_votes` and `live.question_reports`.  
    🇻🇳 *(Tạo migration `0006_question_feedback.sql`, `0006_question_feedback.py` và cơ chế tự khởi tạo bảng trong `ensure_runtime_schema` cho `live.question_votes` và `live.question_reports`.)*

  - [x] 🇬🇧 Implement `backend/app/services/feedback.py` (`<470` LOC) and wire `POST /api/v1/questions/{id}/vote`, `POST /api/v1/questions/{id}/reports`, `GET /api/v1/admin/questions/feedback`, `POST /api/v1/admin/reports/{report_id}/resolve`, plus `has_reports` & vote/report counters on question endpoints.  
    🇻🇳 *(Xây dựng module `backend/app/services/feedback.py` dưới 470 dòng và kết nối đầy đủ 4 API phản hồi cùng bộ đếm/bộ lọc `has_reports` trên danh sách câu hỏi.)*

- 🇬🇧 **Done means**: `pytest` exits `0` across all existing + new feedback tests with zero N+1 queries and zero BOLA leaks.  
  🇻🇳 *(Tiêu chí hoàn thành: Toàn bộ bộ test `pytest` cũ và mới chạy xanh `exit 0`, không có truy vấn N+1 và không rò rỉ câu hỏi chưa phát hành.)*

- 🇬🇧 **Verify**: `(cd backend && ../.venv/bin/pytest -q)`  
  🇻🇳 *(Lệnh kiểm chứng: chạy toàn bộ `pytest` trong thư mục `backend`.)*

- 🇬🇧 **Resume From Here**: Execute TDD Red -> Green in `backend/tests/test_question_feedback.py` and `backend/app/services/feedback.py`.  
  🇻🇳 *(Điểm tiếp nối: Thực thi chu trình TDD Đỏ -> Xanh tại `test_question_feedback.py` và `feedback.py`.)*
