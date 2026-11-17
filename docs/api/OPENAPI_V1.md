# Canonical REST API Contract (`docs/api/OPENAPI_V1.md`)

> Single-Source-of-Truth (`SSOT`) shared between `backend/` (`FastAPI`) and `frontend/` (`Next.js 16`). All request bodies enforce `ConfigDict(extra="forbid")`. Base prefix: `/api/v1`.

## 1. Health & Authentication (`/api/v1/health`, `/api/v1/auth/*`)
| Method | Endpoint | Auth | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | — | `{ status: "ok" }` (`200`) |
| `POST` | `/api/v1/auth/register` | Public | `{ email, username, password, display_name? }` | `{ access_token, token_type, user }` (`201`) |
| `POST` | `/api/v1/auth/login` | Public | `{ identifier, password }` | `{ access_token, token_type, user }` (`200`) |
| `GET` | `/api/v1/auth/me` | Bearer | — | `UserProfile` (`200`) |
| `PUT` | `/api/v1/auth/me` | Bearer | `{ display_name?, bio?, avatar_url? }` | `UserProfile` (`200`) |
| `POST` | `/api/v1/auth/change-password` | Bearer | `{ current_password, new_password }` | `{ status: "ok" }` (`200`) |

## 2. Learner Workbench, Sandbox & Leaderboards (`/api/v1/*`)
| Method | Endpoint | Auth | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/weekly/current` | Bearer | — | Active `published` set summary (`set_id`, `title`, `question_count`, `solved_count`, `ends_at`) |
| `GET` | `/api/v1/weekly/current/questions` | Bearer | `?difficulty&skill_id&solved&q&page&page_size` | Paginated items in the active `published` set |
| `GET` | `/api/v1/questions/{question_id}` | Bearer | — | Question detail + **`output_columns: string[]`** (never leaks `reference_sql` or `"expected*"`) |
| `GET` | `/api/v1/dataset/schema` | Bearer | — | 13 Enterprise tables with `columns: [{ name, type, pk, references? }]` |
| `POST` | `/api/v1/sql/run` | Bearer | `{ question_id, sql }` | Read-only sandbox execution (`columns`, `rows`, `row_count`, `runtime_ms`; strips `--` & `/* */` comments safely) |
| `POST` | `/api/v1/sql/explain` | Bearer | `{ question_id, sql }` | `EXPLAIN` plan analysis (`plan_nodes`, `estimated_cost`) |
| `POST` | `/api/v1/sql/ai-coach` | Bearer | `{ question_id, sql, mode: "review"\|"nl2sql"\|"interview"\|"autofix", prompt?, error_context? }` | Step-by-step SQL guidance & root-cause hints |
| `POST` | `/api/v1/submissions` | Bearer | `{ question_id, sql }` | Deterministic grading (`submission_status: "passed"\|"failed"`, `score`, `runtime_ms`) |
| `GET` | `/api/v1/progress` | Bearer | — | S1–S6 mastery matrix, XP, badges, recent submissions |
| `GET` | `/api/v1/leaderboard/weekly` | Bearer | `?set_id` | Ranked scores for active/selected weekly set |
| `GET` | `/api/v1/leaderboard/monthly` | Bearer | `?year&month` | Ranked scores across monthly & active published sets |

## 3. Admin Generation, Calibrated Review & Manual Authoring (`/api/v1/admin/*`)
| Method | Endpoint | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/admin/generation-jobs` | `{ difficulty, skill_ids?, topic?, quantity?, auto_run? }` | Enqueues Model A + Model B generation job (`202`) |
| `POST` | `/api/v1/admin/generation-jobs/run-worker` | — | Runs synchronous worker cycle until queue idle (`200`) |
| `GET` | `/api/v1/admin/drafts` | `?status&job_id&difficulty&page&page_size` | Paginated `draft.question_drafts` |
| `GET` | `/api/v1/admin/drafts/{draft_id}` | — | Full draft blueprint, `self_solve_runs`, `review_logs`, `promoted_question` |
| `POST` | `/api/v1/admin/drafts/{draft_id}/approve` | `{ selected_run_id?, custom_sql?, note? }` | Verifies mandatory safety gates on `needs_human`/`rejected` draft & promotes to `live.questions(ready)` |
| `POST` | `/api/v1/admin/drafts/bulk-approve` | `{ draft_ids: int[], note? }` | Batch-approves multiple drafts -> `{ approved_count, approved_draft_ids, question_ids, skipped }` |
| `POST` | `/api/v1/admin/questions/manual` | `{ title, question, reference_sql, difficulty, skill_ids, compare_mode? }` | Live-verifies SQL on `enterprise_db` & creates `live.questions(ready)` + `live.test_cases` (`201`) |
| `GET` | `/api/v1/admin/questions` | `?status&difficulty&skill_id&q&unassigned_only&page&page_size` | Lists `live.questions` with `in_weekly_set`, `in_published_set`, `group_ids` |
| `GET` | `/api/v1/admin/gateway-status` | — | Secret-Blind status for `https://apithat.dev/v1` (`configured`, `valid`, `masked_key`, `available_models`) |
| `POST` | `/api/v1/admin/gateway-key` | `{ api_key, base_url?, preferred_model?, persist_env? }` | Probes `/v1/models` on `apithat.dev`, activates runtime key & masks audit trail |
| `PUT` | `/api/v1/admin/settings/{key}` | `{ value }` | Supports `review.approval_mode` (`"calibrated"` \| `"strict"`), `weekly.question_count`, `generation.daily_budget_calls` |

## 4. Admin Question Groups & 1-Click Batch Publishing (`/api/v1/admin/question-groups/*`)
| Method | Endpoint | Payload | Behavior |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/admin/question-groups` | — | Lists all staging/published groups with item counts & preview items |
| `POST` | `/api/v1/admin/question-groups` | `{ name, description?, question_ids?, draft_ids? }` | Creates a group (auto-approving `draft_ids` if provided) and attaches ordered items (`201`) |
| `GET` | `/api/v1/admin/question-groups/{group_id}` | — | Detailed ordered question items in group |
| `PATCH` | `/api/v1/admin/question-groups/{group_id}` | `{ name?, description? }` | Updates metadata of a `draft` group |
| `PUT` | `/api/v1/admin/question-groups/{group_id}/items` | `{ question_ids: int[] }` | Replaces/reorders items (`1..N`, or `[]` to clear) |
| `POST` | `/api/v1/admin/question-groups/{group_id}/add-items` | `{ question_ids?, draft_ids? }` | Appends picked/dragged questions (or newly approved drafts) idempotently |
| `DELETE` | `/api/v1/admin/question-groups/{group_id}` | — | Deletes a `draft` group without deleting underlying `live.questions` |
| `POST` | `/api/v1/admin/question-groups/{group_id}/publish` | `{ mode?: "append_active" \| "new_weekly_set", set_title? }` | Atomically publishes ALL questions in the group onto the live learner shelf at once |
