# Phase 01 — Backend Real-Time Telemetry & 5-Block Dossier Payload
*(Giai đoạn 01 — Backend cung cấp tiến trình thời gian thực & Hồ sơ nghiệm thu 5 khối)*

- **Status**: `Completed` (`2026-11-23 16:18`)
  *(Trạng thái: Đã hoàn tất lúc `2026-11-23 16:18`.)*
- **Evaluator**: `pytest` + `clean-arch-gate.cjs`
  *(Bộ kiểm định: `pytest` và `clean-arch-gate.cjs`.)*
- **Tasks**:
  - [x] Write failing TDD `Red` test in `backend/tests/test_ux_and_grading_v24.py` asserting `live_progress` on `GET /api/v1/admin/drafts` and all 5 blocks of `acceptance_dossier` (`verdict`, `originality`, `consensus`, `checklist`, `repair_and_traps`) on `GET /api/v1/admin/drafts/{id}`.
    *(Đã viết bài test `Red -> Green` trong `test_ux_and_grading_v24.py` kiểm tra `live_progress` và đủ 5 khối `acceptance_dossier`.)*
  - [x] Implement sample/repair tracking in `backend/app/pipeline/review.py`, pedagogical trap derivation in `backend/app/pipeline/generation.py`, and batch `live_progress` + `acceptance_dossier` in `backend/app/services/draft_dossier.py`, `backend/app/services/drafts.py` & `backend/app/routers/admin.py`.
    *(Đã cài đặt theo dõi mẫu giải/vòng sửa lỗi, trích xuất bẫy nghiệp vụ và tổng hợp `live_progress` + `acceptance_dossier`.)*
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)`
  *(Kiểm chứng: chạy `pytest -q` đạt `exit 0`.)*
- **Resume From Here**: Phase 01 complete (`2026-11-23 16:18`).
  *(Điểm tiếp nối: Đã hoàn thành Phase 01.)*
