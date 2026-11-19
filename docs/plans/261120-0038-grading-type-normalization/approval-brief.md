# Approval Brief — Grading Canonical Type Normalization (`261120-0038`)

- **Purpose**: `commercial` (PTIT Capstone grading accuracy).
- **Mode**: `fix` + `review` (`/mykit:fix` + `/mykit:review`).
- **Scope**:
  - Canonicalize cell values in `backend/app/services/submissions.py` (`_canonical_cell`, `_canonical_row`, `json_value` for `float`/`timedelta`/`bytes`/non-finite `Decimal`) so both existing AI-string `live.test_cases` and int-based seed/manual `live.test_cases` compare identically without wiping DB data, while preserving leading-zero strings (`"00123"`, `"0912345678"`).
  - Align `expected_rows` normalization in `backend/app/services/questions.py` and `backend/app/services/drafts.py` with `rv.norm_rows`.
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)` + `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`
