# SQLArena AI — Universal Agent Entrypoint (`AGENTS.md` / `CLAUDE.md`)

> **MyKit v3.15 Polyrepo Standard (`Chung vs Riêng`)**: Automatically loaded by Antigravity, Claude Code (`CLAUDE.md`), OpenAI Codex, Cursor, and Windsurf. Keep `<100` lines; detailed specs live inside `docs/` and `frontend/DESIGN.md`.

## 1. Project Identity & Stack
- **Project**: `SQLArena AI` — Dual-Model PostgreSQL 17 Question Synthesis, Calibrated Verification, Group Publishing & Automated SQL Grading Platform (PTIT Capstone).
- **Dual-Portal Surfaces**:
  - **`http://<HOST>:3000`** — Dedicated **Learner Web** (`Làm bài`, `Tiến độ`, `Xếp hạng`; zero Admin controls).
  - **`http://<HOST>:4000`** — Dedicated **Admin Web** (`Người dùng` default first tab, `Sinh đề AI` per-skill counts, `Duyệt đề`, `Bộ đề tuần` + Approved Pool, `Ngân hàng đề`, `Cấu hình`).
- **AI Gateway**: `https://apithat.dev/v1` (`gpt-5.6-sol` / `gpt-6.1-terra` / `gpt-6-sol` auto-discovery & Secret-Blind Vault).

## 2. Exact Commands (Run Scoped — Never Guess)
- **Configure `apithat.dev` Key (Secret-Blind)**: `./scripts/set-apithat-key.sh`
- **Deploy Full Docker Stack (`:3000` Learner + `:4000` Admin)**: `./scripts/deploy-vps.sh`
- **Run Backend Pytest Suite (Real PostgreSQL 17)**: `(cd backend && ../.venv/bin/pytest -q)`
- **Run AI Engine Unittest Suite**: `(cd ai && AI_PROVIDER=ollama ../.venv/bin/python -m unittest discover -s . -p "test_*.py" -q)`
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
| `docs/ARCHITECTURE.md` | SVG + Dark-Mode-safe Mermaid architecture (`:3000`/`:4000` Nginx proxy, `apithat.dev`, edge cases) |
| `docs/WBS.md` | Scope boundary, Multi-Senior phased WBS (`Agent + Skill + Gate`), and Acceptance Criteria |
| `docs/DECISIONS.md` | SISF Architectural Decision Records (`ADR-001`..`ADR-004`) |
| `docs/REVIEW.md` | Independent `Hunter != Verifier` Gate Matrix & Zero-Knowledge UX Audit Ledger |
| `docs/api/OPENAPI_V1.md` | Single-source-of-truth REST API contract shared across `backend/` and `frontend/` |
| `frontend/DESIGN.md` | Co-located visual design tokens (`linear.app` `dense-workspace` preset) |

## 4. Hard Boundaries & Project Learnings
- **Reversible Live Approval**: Drafts reaching `approved` (via AI calibrated gate or Admin `Phê duyệt`) publish onto the active `published` weekly set immediately; reverting (`POST /admin/drafts/{id}/return-needs-human` or `/reject`) atomically detaches the question from the Learner Web and re-indexes positions.
- **Surface Isolation & Secret-Blind Law**: Learner Web (`:3000`) never exposes Admin tabs; `/api/*` routes same-origin via Nginx on both `:3000` and `:4000`; never expose raw `APITHAT_API_KEY` or `"expected*"` test-case rows.
