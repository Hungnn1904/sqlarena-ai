# Tham chiếu API — AI Pipeline & Question Management

Base URL: `/api/v1` · Swagger UI: `/api/docs` · OpenAPI JSON: `/api/openapi.json`
Xác thực: `Authorization: Bearer <JWT HS256>`; role (`learner`/`admin`) và trạng thái khóa tài khoản luôn đọc lại từ DB.

## Quy ước chung
- **Lỗi** luôn dạng `{"code": "...", "message": "...", "details": {...}}`.
- **Phân trang** `page` (≥1), `page_size` (1–100); response `{items, total, page, page_size}`.
- **Độ khó** là số: `1=Easy, 2=Medium, 3=Hard`. **Thời gian** ISO 8601.

| HTTP | `code` | Khi nào |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Body/query sai, skill không hợp lệ, Rules không hỗ trợ tổ hợp skill–độ khó, `selected_run_id` sai |
| 401 | `UNAUTHORIZED` | Thiếu/sai/hết hạn token |
| 403 | `FORBIDDEN` | Không đủ quyền hoặc tài khoản bị khóa |
| 404 | `NOT_FOUND` | Không tồn tại; **câu hỏi ngoài bộ đề đang mở cũng trả 404** (không lộ tồn tại) |
| 409 | `INVALID_STATE` | Sai trạng thái (approve draft không phải `needs_human`, sửa items khi không còn DRAFT…) |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Cùng `Idempotency-Key` nhưng nội dung khác |
| 409 | `MANDATORY_GATE_FAILED` | Admin approve nhưng lời giải không qua cổng bắt buộc (`details.reasons`) |
| 409 | `LEASE_LOST` | Draft đã bị tiến trình khác xử lý |
| 409 | `WEEK_ALREADY_HAS_SET` · `QUESTION_NOT_ELIGIBLE` (kèm `details.invalid_test_cases` nếu thiếu/lệch dataset_version) · `EMPTY_SET` · `SET_NOT_PUBLISHABLE` · `ANOTHER_SET_PUBLISHED` · `BEFORE_CUTOFF` · `QUESTION_ALREADY_USED` | Quy tắc bộ đề tuần (xem `WEEKLY_SETS.md`) |
| 429 | `LLM_BUDGET_EXCEEDED` | Vượt trần LLM/ngày khi tạo job; kèm `Retry-After` |
| 503 | `REVIEW_INFRA_ERROR` | Không chạy lại được cổng kiểm tra (Enterprise DB/catalog) |

## Job sinh đề (admin)
`POST /admin/generation-jobs` → **202** (200 nếu phát lại cùng `Idempotency-Key` + cùng nội dung)
```json
{ "difficulty": 1, "skill_ids": [1], "quantity": 5, "topic": "Human Resources", "world_id": null }
```
`skill_ids` **tùy chọn**: bỏ trống = mọi kỹ năng đang active mà Rules cho phép ở độ khó đó (đúng luồng "sinh đề theo độ khó, số lượng, chủ đề").
`topic` (tùy chọn) trùng tên domain nghiệp vụ → chọn domain đó; ngược lại được đưa vào prompt như gợi ý. `quantity` ≤ `generation.max_quantity` (mặc định 30).
Response: `job_id, world_id, difficulty, skill_ids, topic, requested_count, created_count, failed_count, status(queued|running|done|failed), error_message, created_at, started_at, finished_at`.
`GET /admin/generation-jobs/{id}` thêm `drafts_by_status` và `llm_calls[{stage,status,n}]` để xem tiến độ.

## Draft & kiểm duyệt (admin)
- `GET /admin/drafts?status=&job_id=&difficulty=` — danh sách.
- `GET /admin/drafts/{id}` — `question`, `schema_text`, `blueprint`, `validation_report`, `self_solve_runs[]` (kèm `model_sql`, `exec_status`, `mismatch_detail`), `review_logs[]`, `promoted_question`.
- `POST /admin/drafts/{id}/approve` `{ "selected_run_id": 12, "note": "..." }` — chỉ cho `needs_human`. Chạy lại cổng kiểm tra bằng lời giải đã chọn; chỉ các lý do "cần phán đoán của người" được admin xác nhận, mọi cổng bắt buộc vẫn áp dụng.
- `POST /admin/drafts/{id}/reject` `{ "reason": "..." }` (3–500 ký tự).
- `PATCH /admin/drafts/{id}` `{ "title"?, "question"?, "note"? }` — **chỉnh sửa** draft `needs_human`/`rejected`. Draft quay về `pending` (xóa đáp án tham chiếu cũ), Model B + mọi cổng chạy lại trên nội dung mới; **không bao giờ tự thành READY**. Bản cũ lưu trong `live.audit_logs`; bằng chứng các vòng review được giữ (`review_round`).
- `POST /admin/drafts/{id}/requeue` `{ "note"? }` — đưa draft `needs_human`/`rejected` về `pending` không sửa nội dung (vd sau khi đổi model/cấu hình).

## Câu hỏi đã xuất bản (admin)
`GET /admin/questions?status=&difficulty=&skill_id=&q=` (có `weekly_set_id`) · `GET /admin/questions/{id}` (có `test_cases[]`, `weekly`) ·
`POST …/retire` `{reason}` → thêm `weekly_effect` (`voided_in_published_set` | `removed_from_draft_set` | null) · `POST …/restore` `{note?}` · `PATCH …/source` `{is_source}`.

## Bộ đề tuần (admin)
| Endpoint | Mô tả |
|---|---|
| `GET /admin/weekly-sets?status=` | Danh sách (kèm `question_count`) |
| `POST /admin/weekly-sets` `{week_start, title?}` → **201** | Tạo DRAFT, tự chọn câu READY chưa dùng theo `weekly.question_count`; trả `warnings`, `deficits_by_difficulty`, `supplemental_generation_job_ids`. 409 `WEEK_ALREADY_HAS_SET` |
| `GET /admin/weekly-sets/{id}` | `items[{position,is_voided,question}]`, `ends_at`, `warnings`, `deficits_by_difficulty` |
| `PUT /admin/weekly-sets/{id}/items` `{question_ids:[…]}` | Thay toàn bộ items khi còn DRAFT; thứ tự mảng = `position`. 409 `QUESTION_NOT_ELIGIBLE` kèm `details.{not_found,not_ready,flagged,already_in_another_set,invalid_test_cases}` |
| `POST /admin/weekly-sets/{id}/publish` | DRAFT → PUBLISHED (bất kỳ ngày nào trong tuần). 409: `EMPTY_SET`, `SET_NOT_PUBLISHABLE` (`not_ready_or_flagged`, `missing_test_cases`, `stale_dataset_version`), `ANOTHER_SET_PUBLISHED` |
| `POST /admin/weekly-sets/{id}/close` | PUBLISHED → CLOSED, archive câu READY trong một transaction. 409 `BEFORE_CUTOFF` chỉ khi setting `weekly.close_requires_cutoff` được bật |

## Người học
| Endpoint | Response |
|---|---|
| `GET /weekly/current` | `{set_id, title, week_start, ends_at, question_count, solved_count}`; 404 nếu chưa có bộ PUBLISHED |
| `GET /weekly/current/questions?difficulty=&skill_id=&q=&solved=` (`q` = lọc theo tên đề) | `items[{question_id, position, title, difficulty, skills[], solved, is_voided}]` |
| `GET /weekly/history` | `items[{set_id, title, week_start, closed_at, question_count, voided_count}]` — lịch sử **tóm tắt** các tuần đã đóng, không có nội dung đề |
| `GET /questions/{id}` | `{question_id, title, question, difficulty, skills[], tables_used, schema_text, solved, is_voided, attempt_count}`; 404 nếu không thuộc bộ đang mở |
| `GET /dataset/schema` | `{name, version, tables[{name, columns[{name,type,nullable,pk,references?}]}]}` |

> `solved`, `solved_count`, `attempt_count` hiện luôn `false/0/0` — cần bảng bài nộp của module chấm điểm. `solved=true` trả danh sách rỗng.

## Cấu hình & giám sát (admin)
- `GET /admin/settings` · `PUT /admin/settings/{key}` `{ "value": … }` — chỉ key đã đăng ký, có kiểu/min/max/trần cứng, ghi audit:

| Key | Mặc định | Ghi chú |
|---|---|---|
| `generation.daily_budget_calls` | 300 | Trần call LLM/ngày (ngày theo `APP_TIMEZONE`) |
| `generation.lease_seconds` / `generation.heartbeat_seconds` | 120 / 20 | Lease của job/draft |
| `generation.max_attempts` | 3 | Số lần claim tối đa trước khi failed/needs_human |
| `generation.max_quantity` | 30 | Draft tối đa mỗi job |
| `solve.samples_k` | 3 | Số lời giải Model B mỗi đề |
| `llm.max_concurrent` | 1 | Cần restart worker |
| `weekly.question_count` | `{"1":5,"2":10,"3":5}` | Mục tiêu mỗi tuần theo độ khó (tài liệu chốt: 20 câu = 5/10/5; tổng ≤ 100) |
| `weekly.close_requires_cutoff` | `false` | Bật để chỉ đóng tuần sau `week_start + 7 ngày`; mặc định admin chủ động đóng tuần cũ để chuyển bộ mới |
| `solve.consensus`, `review.checklist_enabled` | `all`, `false` | Không sửa qua API |

- `GET /admin/skills` · `GET /admin/llm-usage` (`daily_cap`, `used_today`, theo stage/status) · `GET /health` (hàng đợi + job/draft kẹt lease).
