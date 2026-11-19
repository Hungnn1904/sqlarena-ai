# Phase 01 — Backend Unassigned Promotion & Neutral Settings

- **Status**: `Completed` (`2026-11-20 00:24`)
- **Evaluator**: `pytest` + `code-reviewer`
- **Tasks**:
  - [x] Write failing regression tests (`Red`) in `backend/tests/test_groups_and_calibrated_review.py` and `backend/tests/test_team_feedback_regressions.py`.
  - [x] Remove auto-insert into `live.weekly_set_items` from `backend/app/services/promotion.py`.
  - [x] Neutralize `review.approval_mode` description and refresh `ensure_defaults()` in `backend/app/services/settings_registry.py`.
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)` -> `68 passed` (`exit 0`).
- **Resume From Here**: Phase 01 complete (`2026-11-20 00:24`).
