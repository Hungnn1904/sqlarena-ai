# Engineering Constitution & Immutable Domain Laws (`docs/LAW.md`)

> Binding across `backend/`, `ai/`, `frontend/`, and `postgre/` under **MyKit v3.12**.

## 1. Architectural & Clean Boundaries (`Chung vs Riêng`)
- **SQLAlchemy 2.x Core + Explicit SQL**: All persistence goes through parameterized SQL helpers (`begin()`, `q()`, `q1()`, `ex()`) in `backend/app/db.py` across 3 isolated schemas (`core`, `draft`, `live`).
- **Engine Isolation**: `ai/` implements pure generation, AST validation (`pglast`), and deterministic result comparison; `backend/app/pipeline/` wraps `ai/` with DB persistence, lease heartbeats, and `draft.llm_call_ledger` budget accounting.
- **Single API Contract**: `docs/api/OPENAPI_V1.md` is the canonical contract between `backend/` and `frontend/`. Pydantic request schemas enforce `ConfigDict(extra="forbid")`.

## 2. Six Domain & Concurrency Invariants (SQLArena Correctness Floor)
1. **Read-Only Sandbox Isolation (`sqlarena_ai_ro`)**: Every AI-generated, Admin-tested, or Learner-submitted SQL query executes inside `READ ONLY` transactions with bounded `statement_timeout`, `MAX_RESULT_ROWS`, and `pglast`/keyword DDL-DML blocking (`INSERT/UPDATE/DELETE/DROP/ALTER/COPY/pg_sleep` forbidden; SQL `--` and `/* */` comments safely stripped before execution).
2. **Staging Pool vs. Live Shelf Separation (No Auto-Leak)**: Promoting an approved draft (`promotion.promote()`) writes idempotently (`ON CONFLICT (source_draft_id)`) to `live.questions (status='ready')` + `live.test_cases` ONLY. Questions never leak onto the student shelf until an Admin explicitly publishes a **Question Group** (`live.question_groups`) or **Weekly Set** (`live.weekly_sets`).
3. **Atomic Batch Group Publishing (`SELECT ... FOR UPDATE`)**: Publishing a Question Group (`POST /api/v1/admin/question-groups/{id}/publish`) locks both the group row and target `live.weekly_sets` row inside a single transaction, verifies every question is `ready` with non-stale `live.test_cases`, and assigns contiguous positions `1..N` (or `MAX(position)+1..+N`) atomically.
4. **Calibrated Verification Credibility Floor**: Under `review.approval_mode = "calibrated"`, non-semantic false negatives (unrequested English alias differences, FK table subset optimizations, common enum literals, 2/3 valid unanimous runs when 1 sample hits syntax noise) are tolerated as audit notes — **never** relaxing: (a) zero SQL leak in prompt, (b) `row_count > 0` deterministic execution on `enterprise_db`, (c) `0` conflicting valid solver outputs, (d) mandatory `ORDER BY` when requested, and (e) duplicate protection (`similarity >= 0.72` or full signature match).
5. **Fenced Worker Leases & Budget Cap**: Background workers claim jobs/drafts via `FOR UPDATE SKIP LOCKED` with monotonic `lease_version` fencing tokens and enforce `generation.daily_budget_calls` via `pg_advisory_xact_lock`.
6. **Zero Answer Leakage & BOLA Protection**: Learner endpoints never return `reference_sql` or `"expected*"` test-case payloads (exposing only column names as `output_columns`), and reject access (`404`) to any question outside the currently `published` weekly set.

## 3. Infrastructure, Secret-Blind & Repository Hygiene Law
- **Domainless VPS Readiness (`http://<VPS_IP>:3000`)**: Production frontend uses same-origin `/api/v1/*` proxied by Nginx (`frontend/nginx.conf` -> `http://backend:8000`). PostgreSQL binds to `127.0.0.1` on the host so port `5432` is never exposed to the public internet on a VPS.
- **Secret-Blind Execution**: Never commit `.env`, API keys (`APITHAT_API_KEY`), or hardcoded `/Users/<name>` paths; run Docker runtime processes as non-root UID with `/api/v1/health` healthchecks.
- **Root Hygiene**: Root keeps only `README.md`, `AGENTS.md`, `CLAUDE.md` (symlink), `CHANGELOG.md`, and container orchestration (`Dockerfile`, `docker-compose.yml`, `start.sh`). `DESIGN.md` lives at `frontend/DESIGN.md`.
