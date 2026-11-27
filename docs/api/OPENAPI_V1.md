# 🇬🇧 Canonical REST API Contract (`docs/api/OPENAPI_V1.md`)  
🇻🇳 *(Hợp đồng REST API chuẩn tập trung — `docs/api/OPENAPI_V1.md`)*

> 🇬🇧 Single-Source-of-Truth (`SSOT`) shared between `backend/` (`FastAPI`) and `frontend/` (`Next.js 16`). All request bodies enforce `ConfigDict(extra="forbid")`. Base prefix: `/api/v1`.  
> 🇻🇳 *(Nguồn chân lý duy nhất dùng chung giữa `backend/` và `frontend/`. Mọi thân yêu cầu đều chặn trường lạ qua `ConfigDict(extra="forbid")`. Tiền tố gốc: `/api/v1`.)*

## 1. 🇬🇧 Health & Authentication (`/api/v1/health`, `/api/v1/auth/*`)  
*(🇻🇳 1. Kiểm tra trạng thái sống & Xác thực người dùng)*
| Method | Endpoint | Auth | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | — | `{ status: "ok" }` (`200`) |
| `POST` | `/api/v1/auth/register` | Public | `{ email, username, password, display_name? }` | `{ access_token, token_type, user }` (`201`) |
| `POST` | `/api/v1/auth/login` | Public | `{ identifier, password }` | `{ access_token, token_type, user }` (`200`) |
| `GET` | `/api/v1/auth/me` | Bearer | — | `UserProfile` (`200`) |
| `PUT` | `/api/v1/auth/me` | Bearer | `{ display_name?, bio?, avatar_url? }` | `UserProfile` (`200`) |
| `POST` | `/api/v1/auth/change-password` | Bearer | `{ current_password, new_password }` | `{ status: "ok" }` (`200`) |

## 2. 🇬🇧 Learner Workbench, Sandbox & Leaderboards (`/api/v1/*`)  
*(🇻🇳 2. Không gian làm bài Học viên, Sandbox thực thi & Bảng xếp hạng)*
| Method | Endpoint | Auth | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/weekly/current` | Bearer | — | Active `published` set summary (`set_id`, `title`, `question_count`, `solved_count`, `ends_at`) |
| `GET` | `/api/v1/weekly/current/questions` | Bearer | `?difficulty&skill_id&solved&q&page&page_size` | Paginated items in the active `published` set |
| `GET` | `/api/v1/questions/{question_id}` | Bearer | — | Question detail + **`output_columns: string[]`** + `feedback: { upvotes, downvotes, my_vote, can_vote, my_open_report }` |
| `POST` | `/api/v1/questions/{question_id}/vote` | Bearer | `{ vote: 1 \| -1 \| 0 }` | Casts/switches/clears learner vote (requires `live.submissions >= 1`, `409 SUBMISSION_REQUIRED`) |
| `POST` | `/api/v1/questions/{question_id}/reports` | Bearer | `{ reason_type, comment }` | Submits Human-in-the-loop feedback (`201`; max 1 `open` report per user/question -> `409 OPEN_REPORT_EXISTS`) |
| `GET` | `/api/v1/questions/{question_id}/comments` | Bearer | — | Lists 1-level threaded discussion comments + `total_count`, `can_comment`, `author_solved`, `author_badge` |
| `POST` | `/api/v1/questions/{question_id}/comments` | Bearer | `{ content, parent_comment_id? }` | Posts root comment or 1-level reply (`201`; blocks `409 SUBMISSION_REQUIRED` unless `role=='admin'`) |
| `DELETE` | `/api/v1/questions/{question_id}/comments/{comment_id}` | Bearer | — | Deletes comment/reply (`200`; allowed only for comment owner or `role=='admin'`) |
| `GET` | `/api/v1/dataset/schema` | Bearer | — | 13 Enterprise tables with `columns: [{ name, type, pk, references? }]` |
| `POST` | `/api/v1/sql/run` | Bearer | `{ question_id, sql }` | Read-only sandbox execution (`columns`, `rows`, `row_count`, `runtime_ms`; strips `--` & `/* */` comments safely) |
| `POST` | `/api/v1/sql/explain` | Bearer | `{ question_id, sql }` | `EXPLAIN` plan analysis (`plan_nodes`, `estimated_cost`) |
| `POST` | `/api/v1/sql/ai-coach` | Bearer | `{ question_id, sql, mode: "review"\|"nl2sql"\|"interview"\|"autofix", prompt?, error_context? }` | Step-by-step SQL guidance & root-cause hints |
| `POST` | `/api/v1/submissions` | Bearer | `{ question_id, sql }` | Deterministic multi-case grading (`submission_status: "passed"\|"failed"\|"error"`, `score`, `runtime_ms`, `test_cases: [{ test_number, label, title, passed, target_rows, actual_rows, diagnostic_hint }]`) |
| `GET` | `/api/v1/progress` | Bearer | — | S1–S6 mastery matrix, XP, badges, recent submissions |
| `GET` | `/api/v1/leaderboard/weekly` | Bearer | `?set_id` | Ranked scores for active/selected weekly set |
| `GET` | `/api/v1/leaderboard/monthly` | Bearer | `?year&month` | Ranked scores across monthly & active published sets |

## 3. 🇬🇧 Admin Generation, Calibrated Review & Manual Authoring (`/api/v1/admin/*`)  
*(🇻🇳 3. Quản trị sinh đề AI, Kiểm duyệt đồng thuận & Soạn đề thủ công)*
| Method | Endpoint | Payload / Query | Response Summary |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/admin/users` | `?q&role&status&page&page_size` | Paginated `live.users` list |
| `GET` | `/api/v1/admin/users/{user_id}` | — | Full user profile (`user_id`, `email`, `username`, `display_name`, `bio`, `role`, `status`, `stats`, `recent_submissions`) |
| `POST` | `/api/v1/admin/generation-jobs` | `{ difficulty, skill_ids?, skill_quantities?, topic?, quantity?, auto_run? }` | Enqueues per-skill or pooled generation job(s) via `apithat.dev` (`202`) |
| `GET` | `/api/v1/admin/generation-jobs` | `?status&page&page_size` | Paginated `draft.generation_jobs` with sanitized `error_message` & nested drafts |
| `POST` | `/api/v1/admin/generation-jobs/run-worker` | — | Runs synchronous worker cycle until queue idle (`200`) |
| `GET` | `/api/v1/admin/drafts` | `?status&job_id&difficulty&page&page_size` | Paginated `draft.question_drafts` enriched with `live_progress` (`step`, `total_steps`, `samples_done`, `samples_total`, `repair_round`, `error_alert`) |
| `GET` | `/api/v1/admin/drafts/{draft_id}` | — | Full draft blueprint, `self_solve_runs`, `review_logs`, `traps`, `acceptance_dossier` (`verdict`, `originality`, `consensus`, `checklist`, `repair_and_traps`), `promoted_question` |
| `POST` | `/api/v1/admin/drafts/{draft_id}/approve` | `{ selected_run_id?, custom_sql?, note? }` | Approves `needs_human`/`rejected` draft into unassigned `live.questions(ready)` pool |
| `POST` | `/api/v1/admin/drafts/{draft_id}/return-needs-human` | `{ note? }` | Reverts `approved` draft back to `needs_human` and detaches from active Learner shelf |
| `POST` | `/api/v1/admin/drafts/{draft_id}/reject` | `{ reason }` | Rejects `needs_human` or `approved` draft (detaching from Learner shelf if live) |
| `POST` | `/api/v1/admin/drafts/bulk-approve` | `{ draft_ids: int[], note? }` | Batch-approves multiple drafts -> `{ approved_count, approved_draft_ids, question_ids, skipped }` |
| `POST` | `/api/v1/admin/questions/manual` | `{ title, question, reference_sql, difficulty, skill_ids, compare_mode? }` | Live-verifies SQL on `enterprise_db` & creates `live.questions(ready)` + `live.test_cases` (`201`) |
| `GET` | `/api/v1/admin/questions` | `?status&difficulty&skill_id&q&unassigned_only&has_reports&page&page_size` | Lists `live.questions` with `in_weekly_set`, `in_published_set`, `group_ids`, `upvotes`, `downvotes`, `open_reports_count` |
| `GET` | `/api/v1/admin/questions/{question_id}` | — | Full question detail + `test_cases` + `feedback: { upvotes, downvotes, open_reports_count, reports }` |
| `GET` | `/api/v1/admin/questions/feedback` | `?status&question_id&page&page_size` | Paginated learner reports across `live.question_reports` with vote & open-report counters |
| `POST` | `/api/v1/admin/reports/{report_id}/resolve` | `{ action: "rework"\|"return_needs_human"\|"retire"\|"dismiss", admin_note?, updated_title?, updated_question?, updated_sql? }` | Resolves open report(s) via 3-way Human-in-the-loop flow without auto-locking |
| `GET` | `/api/v1/admin/llm-usage` | — | Daily call budget, active gateway models, `recent_drafts`, and `recent_calls` (`sample_no`, `samples_total`, `repair_round`, `error_alert`) |
| `GET` | `/api/v1/admin/gateway-status` | — | Secret-Blind status for `https://apithat.dev/v1` (`configured`, `valid`, `masked_key`, `available_models`) |
| `POST` | `/api/v1/admin/gateway-key` | `{ api_key, base_url?, preferred_model?, persist_env? }` | Probes `/v1/models` on `apithat.dev`, activates runtime key & masks audit trail |
| `PUT` | `/api/v1/admin/settings/{key}` | `{ value }` | Supports `review.approval_mode` (`"calibrated"` \| `"strict"`), `weekly.question_count`, `generation.daily_budget_calls` |

## 4. 🇬🇧 Admin Question Groups & 1-Click Batch Publishing (`/api/v1/admin/question-groups/*`)  
*(🇻🇳 4. Nhóm câu hỏi Quản trị & Phát hành hàng loạt một chạm)*
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
| `DELETE` | `/api/v1/admin/weekly-sets/{set_id}/items/{question_id}` | — | Removes a single question from a `draft` or `published` weekly set and re-indexes `1..N` |
