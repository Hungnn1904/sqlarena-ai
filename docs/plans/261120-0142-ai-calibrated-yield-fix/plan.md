# Plan: Restore High Calibrated AI Approval Yield & Automatic Domain Rotation (`261120-0142`)

## Root Causes Identified (`OBSERVED`)
1. **Stale `"strict"` Mode Stuck in DB (`settings_registry.py` + `db.py`)**: Removing the UI toggle bar left any database where `"Khắt khe"` (`"strict"`) had previously been clicked permanently stuck in `strict` mode because `ensure_defaults()` only updated `description` and did not run inside `ensure_runtime_schema()`.
2. **Domain Rotation Stuck at `index = 0` (`generation.py:160` + `ai/context_policy.py:88-91`)**: With `topic = None` and per-skill 1-question jobs (`skill_quantities`), `index = done` was `0` on every job, forcing `choose_context_group` to pick `'Customer Management'` (`customers`, `customer_addresses`, `orders`) every single time and triggering `suspected_duplicate -> needs_human`.
3. **Compact Gateway Prompt Bugs (`engine.py:290-346`)**:
   - Retry 1+ failed `json.loads(ctx_json_str)` because `PREVIOUS ATTEMPT FAILED` sat between `CONTEXT:` and `OUTPUT OBJECT`, and attempt 0 stripped `goal_to_avoid`.
   - Compact Auditor prompt passed blueprint's internal `required_output_columns` (causing false `semantic_audit_flagged` on natural Vietnamese questions) and omitted `foreign_keys` / `check_constraints`.
4. **Expression `ORDER BY` & 1-of-3 Outlier Sample False Negatives (`ai/review.py:194-224`, `362-369`, `1500-1565`)**:
   - `order_keys` / `actual_order_specs_full` only parsed `ColumnRef` (`ORDER BY alias`), returning `None` for valid `ORDER BY SUM(...)` / `COUNT(...)` expressions or `ORDER BY 1..N` ordinals matching a `SELECT` alias.
   - Under `calibrated=True` (`min_valid = 2`), a single 3rd sample missing `ORDER BY` or a secondary tiebreaker caused `required_order_by_missing` / `order_disagreement -> needs_human` even when `>= 2` valid samples agreed 100% on ordered rows and all samples agreed 100% on unordered data.

## Phases
- [x] **Phase 01 — TDD `Red -> Green`, Gate Verification & Independent Review (`phase-01-calibrated-yield-and-domain-rotation.md`)** (`2026-11-20 01:48`)

## Resume From Here
- Active Phase: Completed (`2026-11-20 01:48`).
