# 🇬🇧 Phase 01 — PostgreSQL Migration `0007`, TDD Suite & Comments REST APIs  
🇻🇳 *(Giai đoạn 01 — Migration PostgreSQL `0007`, Bộ kiểm thử TDD & Hệ thống API Thảo luận)*

- 🇬🇧 **Status**: `Completed` (`2026-11-27 20:18`)  
  🇻🇳 *(Trạng thái: Đã hoàn tất lúc `2026-11-27 20:18`.)*

- 🇬🇧 **Evaluator**: `pytest` on PostgreSQL 17 + `clean-arch-gate.cjs`  
  🇻🇳 *(Bộ kiểm định: `pytest` trên PostgreSQL 17 thật và `clean-arch-gate.cjs`.)*

- 🇬🇧 **Tasks**:  
  🇻🇳 *(Danh sách đầu việc:)*

  - [x] 🇬🇧 Write failing PostgreSQL 17 TDD suite `backend/tests/test_question_comments.py` covering read access, `409 SUBMISSION_REQUIRED` gate, admin bypass, reputation badges (`solved` / `attempted` / `admin`), 1-level reply enforcement, cross-question IDOR protection, and owner/admin deletion.  
    🇻🇳 *(Viết bộ test TDD `test_question_comments.py` kiểm tra quyền đọc, khóa `409 SUBMISSION_REQUIRED`, quyền đặc cách admin, nhãn uy tín tự động, ràng buộc reply 1 cấp, chống IDOR chéo câu hỏi và quyền xóa bình luận.)*

  - [x] 🇬🇧 Add `backend/db/0007_question_comments.sql`, `backend/alembic/versions/0007_question_comments.py`, and `COMMENTS_SCHEMA_DDL` in `backend/app/db.py` (`ensure_runtime_schema`).  
    🇻🇳 *(Tạo migration `0007_question_comments.sql`, `0007_question_comments.py` và cơ chế tự khởi tạo bảng trong `ensure_runtime_schema`.)*

  - [x] 🇬🇧 Implement `backend/app/services/comments.py` (`<250` LOC) and wire `GET /api/v1/questions/{id}/comments`, `POST /api/v1/questions/{id}/comments`, and `DELETE /api/v1/questions/{id}/comments/{comment_id}`.  
    🇻🇳 *(Xây dựng module `backend/app/services/comments.py` dưới 250 dòng và kết nối đầy đủ 3 endpoint thảo luận.)*

- 🇬🇧 **Verify**: `(cd backend && ../.venv/bin/pytest -q)`  
  🇻🇳 *(Lệnh kiểm chứng: chạy toàn bộ `pytest` trên PostgreSQL 17.)*

- 🇬🇧 **Resume From Here**: Run failing `pytest tests/test_question_comments.py` first (`TDD Red`).  
  🇻🇳 *(Điểm tiếp nối: Chạy `pytest tests/test_question_comments.py` quan sát trạng thái Đỏ trước khi viết code.)*
