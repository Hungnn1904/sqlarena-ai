# Plan: Grading Canonical Type Normalization (`261120-0038`)

## Context & Confirmed Root Cause
- **Symptom (`OBSERVED`)**: Queries returning integer columns such as `COUNT(e.employee_id)` on AI-promoted questions fail submission with `1/3 test case` (`Test case 1: Đúng`, `Test case 2: Sai`, `Test case 3: Sai` — `VALUE_MISMATCH`), even when submitting the exact `reference_sql`.
- **Root Cause (`OBSERVED`)**:
  1. `ai/review.py:norm_value()` (`lines 108–116`) normalizes `int`, `Decimal`, and `float` to canonical strings (e.g., `COUNT(...) -> "13"`), which `promotion.promote()` stores into `live.test_cases.expected_result`.
  2. `backend/app/services/submissions.py:json_value()` (`line 94`) keeps `int` as Python `int` (`13`), while `Decimal` becomes `str` (`"423000000"`), `float` falls through to `str(value)` (`"12.0"`), and `timedelta`/`bytes` fall through to `str(value)`.
  3. `compare_result()` and `diagnose_mismatch()` compare `stable_json(row)` directly, causing `{"count_employee": 13} != {"count_employee": "13"}`. Queries with only `VARCHAR` + `SUM(numeric)` passed because both sides serialized `Decimal` to `str`.

## Phases
- [x] **Phase 01 — Failing Reproduction Test (`Red`) & Canonical Cell Normalization (`Green`) (`phase-01-root-cause-and-fix.md`)** (`2026-11-20 00:43`)
- [x] **Phase 02 — Two-Axis Review (`/mykit:review`) & Full Gate Verification (`phase-02-two-axis-review-and-gates.md`)** (`2026-11-20 00:50`)

## Resume From Here
- Active Phase: Completed (`2026-11-20 00:50` — all tests & gates green).
