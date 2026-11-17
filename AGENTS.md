# SQLArena AI — Universal Agent Entrypoint (`AGENTS.md` / `CLAUDE.md`)

> **MyKit v3.15 Polyrepo Standard (`Chung vs Riêng`)**: Automatically loaded by Antigravity, Claude Code (`CLAUDE.md`), OpenAI Codex, Cursor, and Windsurf. Keep `<100` lines; detailed specs live inside `docs/` and `frontend/DESIGN.md`.

## 1. Project Identity & Stack
- **Project**: `SQLArena AI` — Dual-Model PostgreSQL 17 Question Synthesis, Calibrated Verification, Batch Group Publishing & Automated SQL Grading Platform (PTIT Capstone).
- **Topology**: Full-Stack Polyrepo (`backend/` FastAPI + SQLAlchemy 2.x Core + Alembic · `ai/` Dual-Model Generator/Blind Solver · `frontend/` Next.js 16 Static Export + Nginx `/api/` Reverse Proxy · `postgre/` PostgreSQL 17 Enterprise Dataset).
- **AI Gateway**: `https://apithat.dev/v1` (`gpt-5.6-sol` / `gpt-6.1-terra` / `gpt-6-sol` auto-discovery & Secret-Blind Vault) with local Ollama fallback.
- **UI Archetype**: `dense-workspace` (`Operate` mode, `frontend/DESIGN.md`, Be Vietnam Pro + Monospace `tabular-nums`, WCAG >= 4.5:1 in Light & Dark modes).

## 2. Exact Commands (Run Scoped — Never Guess)
- **Configure `apithat.dev` Key (Secret-Blind)**: `./scripts/set-apithat-key.sh` (or via Admin UI Step 1 Vault)
- **Deploy Full Docker Stack (Local or `http://<VPS_IP>:3000`)**: `./scripts/deploy-vps.sh`
- **Run Backend Pytest Suite (56 Tests on Real PostgreSQL 17)**: `(cd backend && ../.venv/bin/pytest -q)`
- **Run AI Engine Unittest Suite (104 Tests)**: `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`
- **Build Frontend Static Export (`frontend/dist`)**: `(cd frontend && npm run build)`
- **Run MyKit Verification Gates (`Must Exit 0`)**:
  - `node ~/.gemini/config/skills/spec-discovery/scripts/spec-gate.mjs . --strict`
  - `node ~/.gemini/config/skills/tdd-red-green/scripts/test-driven-development-verify.cjs .`
  - `node ~/.gemini/config/skills/backend-clean-arch/scripts/clean-arch-gate.cjs .`
  - `node ~/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app`
  - `node ~/.gemini/config/skills/devops-deploy/scripts/devops-gate.mjs`
  - `node ~/.gemini/config/skills/verification-gate/scripts/verification-before-completion-verify.cjs`

## 3. Canonical Documentation Map (Zero Markdown Sprawl)
| Path | Role |
| :--- | :--- |
| `docs/LAW.md` | Non-negotiable domain invariants, read-only SQL safety, calibrated approval floor & hygiene laws |
| `docs/ARCHITECTURE.md` | SVG + Dark-Mode-safe Mermaid runtime architecture, `apithat.dev` gateway, VPS proxy & edge cases |
| `docs/WBS.md` | Scope boundary, Multi-Senior phased WBS (`Agent + Skill + Gate`), and Acceptance Criteria |
| `docs/DECISIONS.md` | SISF Architectural Decision Records (`ADR-001`..`ADR-004`) |
| `docs/REVIEW.md` | Independent `Hunter != Verifier` Gate Matrix & Zero-Knowledge First-Time User UX Audit |
| `docs/api/OPENAPI_V1.md` | Single-source-of-truth REST API contract shared across `backend/` and `frontend/` |
| `frontend/DESIGN.md` | Co-located visual design tokens (`linear.app` `dense-workspace` preset) |

## 4. Hard Boundaries & Project Learnings
- **Staging Pool Isolation**: `promotion.promote()` writes to `live.questions (status='ready')` ONLY — never auto-insert into `live.weekly_set_items`. Questions go live exclusively via **Question Group Batch Publish** (`POST /api/v1/admin/question-groups/{id}/publish`) or **Weekly Set Publish**.
- **Calibrated Approval Floor**: Relax bureaucratic metadata/alias false negatives (`review.approval_mode="calibrated"`), never relax read-only `pglast` AST safety, real PostgreSQL 17 execution (`row_count > 0`), unanimous agreement across valid runs, or mandatory `ORDER BY` contracts.
- **Domainless VPS & Secret-Blind Law**: Route `/api/*` same-origin through `frontend/nginx.conf` -> `http://backend:8000` (never hardcode `127.0.0.1:8000` in static bundles), and never expose raw `APITHAT_API_KEY` or `"expected*"` test-case rows in API responses or logs.
