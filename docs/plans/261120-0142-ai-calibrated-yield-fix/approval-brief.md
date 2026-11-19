# Approval Brief — Calibrated AI Yield & Domain Rotation (`261120-0142`)

- **Purpose**: `commercial` (PTIT Capstone AI Question Synthesis pipeline).
- **Invariants Preserved**:
  - Read-only `SELECT`/`WITH` sandbox guard.
  - Deterministic `row_count > 0` execution on PostgreSQL 17 `enterprise_db`.
  - Zero tolerance (`needs_human`) whenever valid solver samples return conflicting unordered data values (`consensus_disagreement`), violate explicit column names in `question`, or invent unstated string literals.
- **Verify**: `(cd backend && ../.venv/bin/pytest -q)` + `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`
