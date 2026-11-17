# Engineering Constitution & Immutable Domain Laws (`docs/LAW.md`)

> Binding across `backend/`, `ai/`, `frontend/`, and `postgre/` under **MyKit v3.15**.

## 1. Architectural & Dual-Surface Boundaries (`Chung vs Riêng`)
- **Strict Portal Separation**: Port `:3000` serves the **Learner Portal** exclusively (`Làm bài`, `Tiến độ`, `Xếp hạng` — zero Admin routes or controls). Port `:4000` serves the **Admin Portal** exclusively (opening `Người dùng` by default).
- **SQLAlchemy 2.x Core + Explicit SQL**: All persistence goes through parameterized SQL helpers (`begin()`, `q()`, `q1()`, `ex()`) in `backend/app/db.py` across 3 isolated schemas (`core`, `draft`, `live`).
- **Single API Contract**: `docs/api/OPENAPI_V1.md` is the canonical contract between `backend/` and `frontend/`. Pydantic request schemas enforce `ConfigDict(extra="forbid")`.

## 2. Six Domain & Concurrency Invariants (SQLArena Correctness Floor)
1. **Read-Only Sandbox Isolation (`sqlarena_ai_ro`)**: Every AI-generated, Admin-tested, or Learner-submitted SQL query executes inside `READ ONLY` transactions with bounded `statement_timeout`, `MAX_RESULT_ROWS`, and `pglast`/keyword DDL-DML blocking (`INSERT/UPDATE/DELETE/DROP/ALTER/COPY/pg_sleep` forbidden; SQL `--` and `/* */` comments safely stripped).
2. **Reversible Live Approval (`Approved <-> Needs_Human / Rejected`)**: Promoting an approved draft (`promotion.promote()`) writes idempotently to `live.questions (status='ready')` + `live.test_cases` and attaches to the active `published` weekly set if open. Reverting via `return-needs-human` or `reject` atomically removes the item from `live.weekly_set_items`, re-indexes positions `1..N`, and retires the live question until re-approved.
3. **Atomic Batch Group & Weekly Publishing (`SELECT ... FOR UPDATE`)**: Publishing a Question Group or Weekly Set locks target rows inside a single transaction, verifies every question has valid `live.test_cases` matching `dataset_version`, and assigns contiguous positions atomically.
4. **Calibrated Verification Credibility Floor**: Under `review.approval_mode = "calibrated"`, non-semantic false negatives (unrequested English alias differences, `>=2/3` unanimous valid runs when 1 sample hits syntax noise) are tolerated — **never** relaxing read-only AST safety, `row_count > 0` deterministic execution on `enterprise_db`, `0` conflicting valid solver outputs, mandatory `ORDER BY`, or duplicate protection (`similarity >= 0.72`).
5. **Fenced Worker Leases, Per-Skill Quotas & Budget Cap**: Per-skill generation requests (`skill_quantities`) enqueue exact per-skill quotas guarded by `pg_advisory_xact_lock` on `generation.daily_budget_calls` and `FOR UPDATE SKIP LOCKED` + monotonic `lease_version` fencing tokens.
6. **Zero Answer Leakage & BOLA Protection**: Learner endpoints never return `reference_sql` or `"expected*"` test-case payloads (exposing only column names as `output_columns`), and reject access (`404`) to any question outside the currently `published` weekly set.

## 3. Infrastructure, Secret-Blind & Repository Hygiene Law
- **Domainless VPS Readiness (`:3000` & `:4000`)**: Production Nginx (`frontend/nginx.conf`) proxies `/api/v1/*` same-origin to `http://backend:8000` on both `:3000` and `:4000`. PostgreSQL binds to `127.0.0.1` on the host.
- **Secret-Blind Execution**: Never commit `.env` or raw `APITHAT_API_KEY`; strip internal local-model identifiers from user-facing logs and UI.
- **Root Hygiene**: Root keeps only `README.md`, `AGENTS.md`, `CLAUDE.md` (symlink), `CHANGELOG.md`, and container orchestration (`Dockerfile`, `docker-compose.yml`, `start.sh`). `DESIGN.md` lives at `frontend/DESIGN.md`.
