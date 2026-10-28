# SQLArena AI — Living Feature Index & Clean Architecture Blueprint

> **Single Source of Truth (`docs/FEATURE_INDEX.md`)**: Tệp này được hook `ck-agy-adapter.cjs` tự động nạp vào bộ nhớ mỗi phiên làm việc để giữ chuẩn Clean Architecture của dự án **SQLArena AI (PTIT)**.

## 1. Hệ thống Database (100% PostgreSQL 17 — Không dùng SQLite)
- **Engine**: PostgreSQL 17 (chạy ngầm qua Homebrew service `postgresql@17` trên macOS ở cổng `5432` lúc dev, hoặc qua container `postgres:17-alpine` trong `docker-compose.yml` khi deploy).
- **Lý do bắt buộc dùng PostgreSQL**:
  - Cần parser AST chuẩn PostgreSQL (`pglast`) và chạy thực tế các hàm Window Function, CTE đệ quy (`WITH RECURSIVE`), `DATE_TRUNC`, `JSONB`.
  - Cần cơ chế hàng đợi phân tán `FOR UPDATE SKIP LOCKED` cho AI Generation/Review Worker.
  - Cần cơ chế Sandbox cô lập quyền mức Database Role: `sqlarena_ai_ro` (`default_transaction_read_only = on`, gỡ quyền `CREATE/TEMP`, `statement_timeout = 10s`).
- **Sơ đồ Database**:
  1. `enterprise_db`: Chứa 17 bảng dữ liệu nghiệp vụ thương mại điện tử/doanh nghiệp (>13,400 bản ghi) + role chỉ đọc `sqlarena_ai_ro` để chạy câu lệnh `SELECT/WITH` của học viên và AI Model B.
  2. `sqlarena_app` (hoặc gộp thống nhất với `sqlarena_db`):
     - Schema `core`: `worlds`, `skills` (S1–S6), `templates`, `prompt_templates`, `system_settings`, `source_questions` (50 câu gốc `ENT-001`..`ENT-050`).
     - Schema `draft`: `generation_jobs`, `question_drafts`, `review_logs`, `self_solve_runs`, `llm_call_ledger`.
     - Schema `live`: `roles`, `users`, `questions`, `test_cases`, `weekly_sets`, `weekly_set_items`, `submissions`, `admin_overrides`, `audit_logs`.

---

## 2. Kiến trúc Clean Architecture (3-Gear Modular Monolith)

```text
sqlarena-ai/
├── ai/                             # [Domain Engine] Core AI Pipeline (Model A sinh đề + Model B giải & kiểm duyệt)
│   ├── main.py                     # Model A generator & blueprint planner
│   ├── review.py                   # Model B multi-sample solver, consensus & semantic auditor
│   ├── validator.py                # AST SQL validator (pglast) & read-only guard
│   └── context_policy.py           # Token & schema context limiter
├── backend/                        # [Application & Infrastructure] Unified FastAPI Server
│   ├── alembic/                    # Database migrations (0001_baseline, 0002_weekly_sets, 0003_submissions_auth)
│   ├── app/
│   │   ├── main.py                 # Composition Root: FastAPI app, CORS, Error Handlers, Router mounting
│   │   ├── config.py               # Environment & Pydantic Settings
│   │   ├── db.py                   # Database connection pool & transaction context manager
│   │   ├── domain.py               # Pure Domain Enums, Value Objects & Constants
│   │   ├── schemas.py              # Pydantic Request/Response Contracts (DTOs)
│   │   ├── security.py             # JWT Authentication (HS256), Password Hashing & Role Guards (learner/admin)
│   │   ├── worker.py               # Background Worker (SKIP LOCKED lease + fencing token)
│   │   ├── pipeline/               # [Adapters -> AI Engine]
│   │   │   ├── catalog.py          # Enterprise DB schema & fingerprint verifier
│   │   │   ├── engine.py           # Wrapper connecting FastAPI/Worker to ../ai/
│   │   │   ├── generation.py       # Model A job runner
│   │   │   ├── review.py           # Model B review gate & mandatory checks
│   │   │   ├── leases.py           # Distributed lease & heartbeat manager
│   │   │   └── ledger.py           # Daily LLM token/call budget guard
│   │   ├── services/               # [Use Cases / Application Services]
│   │   │   ├── auth.py             # Register, Login, Profile, User Management (Nguyên)
│   │   │   ├── sandbox.py          # Read-only SQL execution & deterministic result comparator (Đạt)
│   │   │   ├── submissions.py      # Grading, submission history, skill progress & weekly/monthly leaderboards (Đạt + Nguyên)
│   │   │   ├── jobs.py             # Generation job orchestration (Hưng)
│   │   │   ├── drafts.py           # Draft review, admin approve/reject/edit (Hưng)
│   │   │   ├── promotion.py        # Atomic promotion draft -> live.questions + live.test_cases (Hưng)
│   │   │   ├── questions.py        # Published question catalog & retire/restore (Hưng)
│   │   │   ├── weekly.py           # Weekly set lifecycle: draft -> published -> closed (Hưng)
│   │   │   ├── settings_registry.py# Runtime system settings validation (Hưng)
│   │   │   └── audit.py            # Audit log recorder
│   │   └── routers/                # [Presentation / HTTP Controllers]
│   │       ├── auth.py             # POST /api/v1/auth/register, /login, GET/PUT /me, Admin user management
│   │       ├── learner.py          # GET /api/v1/weekly/*, /questions/*, POST /run, /submissions, GET /leaderboard/*, /progress/*
│   │       ├── admin.py            # /api/v1/admin/* (jobs, drafts, questions, weekly-sets, settings, llm-usage, users)
│   │       └── health.py           # GET /api/v1/health & /health
│   ├── sql_run_api.py              # Legacy compatibility router (/api/*) cho learner.html hiện tại
│   └── tests/                      # Automated Pytest Suite (46+ integration & contract tests)
├── postgre/                        # Canonical SQL DDL & Enterprise Seed Data
│   ├── enterprise_db/              # Schema, constraints, 13,400+ seed rows, read-only role
│   ├── sqlarena_db/                # Core 50 source questions & review pipeline tables
│   └── app_db/                     # App tables & expected_result populator
├── frontend/                       # [Web UI] Giao diện người dùng (Learner, Auth, Admin Dashboard)
├── docs/                           # Tài liệu kiến trúc, API, vận hành & FEATURE_INDEX.md
└── docker-compose.yml              # Full-stack deployment (Postgres + Backend API + Worker + Frontend)
```

---

## 3. Feature Cards (`[FEAT-XX]`)

### [FEAT-01] AI Question Generation & Review Pipeline (Hưng)
- **Keywords**: `generation-jobs`, `drafts`, `model_a`, `model_b`, `review`, `worker`, `llm-usage`, `promote`
- **Canonical Workflow**: Admin tạo Job -> Worker claim (`SKIP LOCKED`) -> Model A sinh câu hỏi -> Blueprint Gate (`pglast`) -> Lưu `draft.question_drafts` -> Model B giải độc lập `k` lần trên `enterprise_db` -> Đồng thuận + Semantic Audit -> Tự động promote sang `live.questions` + `live.test_cases` (hoặc `needs_human` để Admin duyệt).
- **Files**: `backend/app/pipeline/*`, `backend/app/services/jobs.py`, `backend/app/services/drafts.py`, `backend/app/services/promotion.py`, `backend/app/routers/admin.py`.

### [FEAT-02] SQL Read-Only Sandbox, Grading & Leaderboards (Đạt)
- **Keywords**: `sandbox`, `run`, `submissions`, `grading`, `expected_result`, `leaderboard`, `weekly`, `monthly`, `progress`, `skills`
- **Canonical Workflow**: Học viên gửi câu lệnh `SELECT/WITH` -> `guard_select` chặn DDL/DML/comment/multi-statement -> Thực thi bằng role `sqlarena_ai_ro` trên `enterprise_db` (`READ ONLY`, timeout `10s`) -> So khớp kết quả (`ordered` hoặc `unordered` Counter JSON) với `expected_result` -> Lưu `live.submissions` -> Tính tiến độ kỹ năng (`S1`–`S6`) và BXH Tuần/Tháng theo số câu đúng + thời gian đạt sớm nhất.
- **Files**: `backend/app/services/submissions.py`, `backend/app/routers/learner.py`, `backend/db/0003_submissions_and_leaderboard.sql`, `backend/sql_run_api.py`.

### [FEAT-03] Authentication, User Management, Unified Next.js 16 Frontend & Docker Deployment (Nguyên)
- **Keywords**: `auth`, `login`, `register`, `jwt`, `profile`, `users`, `frontend`, `nextjs`, `monaco`, `admin`, `docker-compose`, `deploy`
- **Canonical Workflow**: Đăng ký / Đăng nhập cấp JWT (`HS256`, `sub = user_id`, mật khẩu `PBKDF2-HMAC-SHA256`) -> Phân quyền `learner` vs `admin` từ `live.users` -> Học viên làm bài bộ đề tuần trên Monaco SQL Workbench (`http://127.0.0.1:3000`), xem tiến độ, BXH, cập nhật hồ sơ -> Admin quản lý sinh đề AI, duyệt đề `needs_human`, lập & phát hành Bộ đề tuần, quản lý tài khoản -> Đóng gói toàn bộ qua `docker-compose.yml` & bộ 48 bài test tích hợp (`tests/test_auth_and_submissions.py`).
- **Files**: `backend/app/services/auth.py`, `backend/app/routers/auth.py`, `backend/app/seed.py`, `frontend/src/lib/api.ts`, `frontend/src/components/AuthBar.tsx`, `frontend/src/components/LearnerWorkbench.tsx`, `frontend/src/components/ProgressAndLeaderboard.tsx`, `frontend/src/components/AdminPortal.tsx`, `docker-compose.yml`, `README.md`.
