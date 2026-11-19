# Phase 01 — Failing Reproduction Test (`Red`) & Canonical Cell Normalization (`Green`)

- **Status**: `Completed` (`2026-11-20 00:43`)
- **Evaluator**: `pytest` + `ai` `unittest`
- **Tasks**:
  - [x] Add deterministic `Red` reproduction test in `backend/tests/test_team_feedback_regressions.py` covering `COUNT(e.employee_id)` + `SUM(e.current_salary)` on AI-promoted `live.test_cases`, `float8` (`12.0` vs `12`), `interval` (`timedelta`), and leading-zero string preservation (`"00123"` != `"123"`).
  - [x] Implement `_canonical_cell` / `_canonical_row` and harden `json_value` in `backend/app/services/submissions.py`, plus align `rv.norm_rows` in `questions.py` and `drafts.py`.
  - [x] Run full `pytest` (`69 passed`) and `ai` `unittest` (`104 tests OK`) (`exit 0`).
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)`
- **Resume From Here**: Phase 01 complete (`2026-11-20 00:43`). Proceed to Phase 02 Two-Axis Review.
