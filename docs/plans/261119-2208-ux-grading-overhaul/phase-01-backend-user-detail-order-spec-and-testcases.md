# Phase 01: Backend User Detail API, `ORDER BY` Prompt Sync & Multi-Test-Case Grading

- **Evaluator**: `pytest` + `unittest` (`backend-architect` / `tdd-red-green`)
- **Verify**: `(cd backend && ../.venv/bin/pytest -q) && (cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`

## Tasks & Done Means
- [x] Write failing TDD suite `backend/tests/test_ux_and_grading_v24.py` (`Red`) covering `GET /api/v1/admin/users/{user_id}`, `ORDER BY` synchronization (`compare_mode` + Vietnamese prompt clause), and `>= 3` `test_cases` checkpoints on `POST /api/v1/submissions`.
- [x] Implement `auth.admin_get_user_detail(conn, user_id)` + `GET /api/v1/admin/users/{user_id}` returning profile, `stats`, and `recent_submissions`.
- [x] Implement `backend/app/services/order_spec.py` (`extract_top_level_order_by`, `sync_question_order_contract`) + wire into `promotion.py`, `questions.py`, `db.ensure_runtime_schema()`, and `ai/main.py`.
- [x] Enhance `submissions.submit_query()` (with active published-set BOLA guard + zero `"expected*"` leak) so every submission returns `>= 3` labeled `test_cases` (`Test case 1`, `Test case 2`, `Test case 3`, ...) with `passed: bool` and Vietnamese diagnostic hints.
- [x] Watch full `pytest` and `ai` `unittest` suites exit `0` (`Green`).
