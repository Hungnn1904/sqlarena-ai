# Approval Brief — Unassigned Approved Pool & Clean UI Copy (`261120-0019`)

- **Purpose**: `commercial` (PTIT Capstone team deployment).
- **Root Causes**:
  1. `backend/app/services/promotion.py` (`lines 56–69`) queried `SELECT set_id FROM live.weekly_sets WHERE status='published'` and auto-inserted newly promoted questions directly onto the active Learner shelf instead of keeping them in `Câu hỏi Approved chưa có trên kệ`.
  2. `frontend/src/components/AdminPortal.tsx` exposed an unrequested `AI duyệt: Thông minh | Khắt khe` toggle on `Sinh đề AI` and conversational examples (`VD: SQL tuần 6`).
- **Verification**:
  - `(cd backend && ../.venv/bin/pytest -q)` -> `exit 0`
  - `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)` -> `exit 0`
  - `(cd frontend && npm run build)` + `fe-gate.mjs frontend/src --app` -> `exit 0`
