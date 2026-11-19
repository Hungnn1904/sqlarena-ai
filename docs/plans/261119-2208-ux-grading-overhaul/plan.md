# Plan: SQLArena AI v2.4 — 9-Point Admin/Learner UX, ORDER BY Sync, Multi-Test-Case Grading & 80% Scale

- **Mode**: `SOLO-INDIE`
- **Purpose**: `learning` (PTIT Capstone Evaluation & Live Team Delivery)
- **Approval Brief**: `./approval-brief.md`
- **Active Phase / Resume From Here**: `COMPLETED (All Phases 01..04 Verified)`

## 1. Objective & Scope (`Các-lỗi-cần-sửa_p2.docx`)
Implement all 9 team review requirements end-to-end across PostgreSQL 17, FastAPI, AI prompt pipeline, and Next.js 16 without breaking existing Warm Paper (`#F5EDDC`) / Editorial Sage (`#4D6F61`) tokens or RBAC laws:
1. **Admin User Profile Modal**: Click any account in `Người dùng` -> inspect profile, stats, recent submissions, and role/status actions via `GET /api/v1/admin/users/{user_id}`.
2. **Pure Manual Review Tab (`Duyệt đề`)**: Remove AI `review.approval_mode` toggle bar from `Duyệt đề` (keep AI controls strictly in `Sinh đề AI` / `Cấu hình`).
3. **Weekly Shelf Tabs (`Bộ đề tuần`)**: Remove `Tất cả Approved`; keep `Chưa có trên kệ` and add `Đã có trên kệ` statistical breakdown (`Tổng`, `Dễ`, `Trung bình`, `Khó` + live items).
4. **Clean Draft Group Item Actions**: Remove `↑` / `↓` reorder arrow buttons on group composer items, keeping `Gỡ` + drag-and-drop.
5. **Draft-Only Top Group Selector**: Show only `status === 'draft'` groups in the top composer bar; once published, move immediately to `Danh sách Bộ đề tuần` below.
6. **Streamlined Learner Workbench (`Làm bài`)**: Remove `Chèn tên cột vào SELECT`; embed `Sơ đồ bảng dữ liệu` inside the left problem card; remove `Trợ lý học tập` bar (`AI Coach` + `EXPLAIN`); display per-case verdicts (`Test case 1: Đúng/Sai`, `Test case 2: Đúng/Sai`, `Test case 3: Đúng/Sai`) on `Nộp bài` and auto-scroll smoothly to the submission result box.
7. **Failed Attempt Badge**: Show `"Chưa làm được"` (instead of `"Đang thử"`) when `!q.solved && attempt_count > 0`.
8. **Explicit `ORDER BY` Synchronization**: Parse `reference_sql` top-level `ORDER BY` into explicit Vietnamese sorting instructions in every question prompt (newly promoted/generated + backfilled DB rows), and normalize `compare_mode = 'unordered'` when `reference_sql` has no `ORDER BY`.
9. **Global 80% Visual Scale**: Set root `html { font-size: 80%; }` (`1rem = 12.8px`) with explicit pixel `fontSize`/`lineHeight` isolation on Monaco Editor so 100% browser zoom renders at compact 80% density with zero cursor hitbox drift.

## 2. Phases
| Phase | Spec File | Status | Verify Command |
| :--- | :--- | :---: | :--- |
| Phase 01 | `phase-01-backend-user-detail-order-spec-and-testcases.md` | `[x]` | `(cd backend && ../.venv/bin/pytest -q) && (cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)` |
| Phase 02 | `phase-02-admin-users-drafts-and-weekly-composer-ux.md` | `[x]` | `(cd frontend && npm run build)` |
| Phase 03 | `phase-03-learner-workbench-schema-grading-and-status.md` | `[x]` | `(cd frontend && npm run build)` |
| Phase 04 | `phase-04-global-80pct-scale-live-browser-and-review-gate.md` | `[x]` | `node ~/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app` |

## 3. Execution Log (`YYYY-MM-DD HH:mm`)
- `2026-11-19 22:12` — Completed `/mykit:retro` staging (`3` lessons staged, `memory-check.mjs` active) and locked `/mykit:plan` specs (`docs/LAW.md`, `docs/WBS.md`, `docs/api/OPENAPI_V1.md`, `plan.md`, `phase-01..04`).
- `2026-11-19 22:23` — Completed `Phase 01` (`Red -> Green`): `67 passed` in `pytest` and `104 passed` in `ai` `unittest` covering `GET /api/v1/admin/users/{user_id}`, `order_spec.py` `ORDER BY` prompt/mode synchronization + `ensure_runtime_schema()` backfill, and 3-checkpoint `test_cases` grading.
- `2026-11-19 22:29` — Completed `Phase 02` (`AdminPortal.tsx` + `api.ts`): User Detail Modal, pure-admin `Duyệt đề`, `Chưa có trên kệ` + `Đã có trên kệ` stats tab, draft-only top group selector, and arrow removal (`npm run build` exited `0`).
- `2026-11-19 22:32` — Completed `Phase 03` (`LearnerWorkbench.tsx`): `"Chưa làm được"` badge, inline `Sơ đồ bảng dữ liệu` inside problem card, removed `Chèn tên cột vào SELECT` + `Trợ lý học tập` / `AI Coach` / `EXPLAIN`, and added `Test case 1..3: Đúng / Sai` verdicts + smooth `scrollIntoView` on `Nộp bài` (`npm run build` exited `0`).
- `2026-11-19 22:56` — Completed `Phase 04`: Global `80%` `rem` scaling (`12.8px`), `9/9` live Docker browser verification (`0` console errors, Desktop + `375px` mobile), resolved `11/11` Round-1 `code-reviewer` findings with Round-2 `ZERO BLOCKING FINDINGS` sign-off (`68 passed` in `pytest`, `104 passed` in `ai` `unittest`, `fe-gate` & `spec-gate` `0 FAIL`).
