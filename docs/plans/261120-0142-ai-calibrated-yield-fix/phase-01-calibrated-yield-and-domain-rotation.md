# Phase 01 — TDD `Red -> Green`, Gate Verification & Independent Review

- **Status**: `Completed` (`2026-11-20 01:48`)
- **Evaluator**: `pytest` + `ai` `unittest` + `code-reviewer`
- **Tasks**:
  - [x] Write failing TDD `Red` test in `backend/tests/test_groups_and_calibrated_review.py` reproducing stale `"strict"` healing, multi-job `topic=None` domain rotation, expression `ORDER BY SUM(...)` + `2/3` majority calibrated order agreement, and `consensus_disagreement` hard block.
  - [x] Patch `backend/app/services/settings_registry.py`, `backend/app/db.py`, `backend/app/pipeline/generation.py`, `backend/app/pipeline/engine.py`, and `ai/review.py`.
  - [x] Verify `pytest` (`70 passed`), `ai` `unittest` (`104 passed`), `code-reviewer`, commit, push, and `docker compose down`.
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)`
- **Resume From Here**: Completed (`2026-11-20 01:48`).
