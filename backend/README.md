# SQLArena — AI Pipeline & Question Management Backend (phần việc của Hưng)

Backend FastAPI + Generation/Review Worker bao quanh pipeline AI hiện có (`../ai/`: Model A sinh đề, Model B giải/kiểm duyệt).
Phạm vi theo phân việc 17/10/2026: **job sinh đề → draft → kiểm duyệt (Model B + admin) → promote thành câu hỏi + test case → bộ đề tuần → API câu hỏi cho người học**.

```
Admin ──POST /admin/generation-jobs──► draft.generation_jobs (queued)
                                         │  Worker: claim (SKIP LOCKED, lease, fencing)
                                         ▼
                      Model A (ai/main.py) → Blueprint gate (ai/validator.py) → draft.question_drafts (pending)
                                         ▼
                      Model B ×k (ai/review.py): guard SQL, chạy trên Enterprise DB, đồng thuận, contract, semantic audit
                         ├─ approved  ──► live.questions (ready) + live.test_cases   (cùng 1 transaction)
                         ├─ needs_human ► Admin: approve (chạy lại cổng) / reject
                         └─ rejected
Admin ──POST /admin/weekly-sets──► bộ đề DRAFT (tự chọn câu READY chưa dùng; thiếu → ghi deficits + xếp job sinh bổ sung)
      ──PUT …/items──► ──POST …/publish──► PUBLISHED ──POST …/close──► CLOSED (câu READY → archived)
Người học ──GET /weekly/current, /weekly/current/questions, /questions/{id}, /dataset/schema
            (chỉ câu thuộc bộ đề PUBLISHED; không bao giờ thấy reference_sql/expected)
```
Mọi call LLM đi qua **BudgetGuard + `draft.llm_call_ledger`** (trần theo ngày, atomic, tính cả call lỗi/timeout).

## Tài liệu
| File | Nội dung |
|---|---|
| [`docs/API.md`](../docs/API.md) | Tham chiếu endpoint, mã lỗi, ví dụ request/response |
| [`docs/WEEKLY_SETS.md`](../docs/WEEKLY_SETS.md) | Vòng đời bộ đề tuần, quy tắc chọn đề, thiếu hụt, retire/void, close và hook xếp hạng |
| [`docs/OPERATIONS.md`](../docs/OPERATIONS.md) | Cài đặt, chạy worker, ngân sách LLM, lease/khôi phục, sự cố thường gặp |
| [`docs/DESIGN_DECISIONS.md`](../docs/DESIGN_DECISIONS.md) | Quyết định thiết kế, khác biệt so với Design v7, giới hạn đã biết |
| [`CHANGELOG.md`](../CHANGELOG.md) | Lịch sử thay đổi |

## Chạy thử (dev)
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # (Linux/macOS: cp) điền DATABASE_URL, JWT_SECRET, thông tin Enterprise DB (chỉ đọc)
python -m app.cli migrate       # Alembic 0001 (core/draft/live) + 0002 (bộ đề tuần)
python -m app.cli seed          # world Enterprise, S1–S6, 50 đề nguồn, cấu hình mặc định
python -m app.cli check         # kiểm tra Core + schema Enterprise + Ollama (không tốn call sinh)
uvicorn app.main:app --port 8080            # API  → http://localhost:8080/api/docs
python -m app.cli worker                    # worker (process riêng, chạy được nhiều bản)
```
Chưa có module Auth? `python -m app.cli create-admin --email a@x.io --username admin` rồi `python -m app.cli token --user-id 1` để lấy Bearer token dev.

Điều kiện: PostgreSQL ≥ 14, Ollama với model trong `.env` đã `ollama pull`, Enterprise DB đã nạp (xem `../postgre/enterprise_db`) và role `sqlarena_ai_ro` đã tạo.

## Test
```bash
python -m pytest tests -q        # 46 test, PostgreSQL thật + Enterprise DB thật; chỉ HTTP tới Ollama là giả
```
Biến `TEST_PG_ADMIN_DSN`, `TEST_ENTERPRISE_USER/PASSWORD`, `TEST_CATALOG_USER/PASSWORD` chỉnh kết nối (mặc định xem `tests/conftest.py`). Test tạo DB tạm `sqlarena_app_pytest`, chạy Alembic từ đầu rồi seed.

| File test | Phủ |
|---|---|
| `test_api_contract.py` | xác thực/phân quyền, định dạng lỗi, idempotency, trần ngân sách khi tạo job, `skill_ids` tùy chọn, settings |
| `test_pipeline_e2e.py` | job → Model A → Model B → promote → bộ đề → người học; đồng thuận, audit, trùng đề nguồn |
| `test_review_and_safety.py` | admin approve/reject/sửa/requeue, cổng bắt buộc, ngân sách runtime, Ollama hỏng, claim đồng thời, fencing, khôi phục lease, promote idempotent |
| `test_weekly_sets.py` | mặc định 5/10/5, thiếu hụt/job bổ sung, dataset/version, thay items, publish, close (atomic), view + lịch sử người học, retire → void |

## API (prefix `/api/v1`) — chi tiết ở `docs/API.md`
| Nhóm | Endpoint |
|---|---|
| Job sinh đề | `POST/GET /admin/generation-jobs` · `GET /admin/generation-jobs/{id}` |
| Draft/kiểm duyệt | `GET /admin/drafts[/{id}]` · `PATCH …/{id}` (sửa) · `POST …/approve` · `…/reject` · `…/requeue` |
| Câu hỏi (admin) | `GET /admin/questions[/{id}]` · `POST …/retire` · `POST …/restore` · `PATCH …/source` |
| Bộ đề tuần (admin) | `GET/POST /admin/weekly-sets` · `GET /admin/weekly-sets/{id}` · `PUT …/items` · `POST …/publish` · `POST …/close` |
| Người học | `GET /weekly/current` · `GET /weekly/current/questions` · `GET /weekly/history` · `GET /questions/{id}` · `GET /dataset/schema` |
| Khác | `GET /admin/skills` · `GET/PUT /admin/settings[/{key}]` · `GET /admin/llm-usage` · `GET /health` |

## Bàn giao cho các phần khác
- **Auth (Nguyên):** backend chỉ *xác minh* JWT HS256 (`sub` = `live.users.user_id`, cùng `JWT_SECRET`); role/khóa tài khoản luôn đọc lại từ DB. Migration `0001` tạo `live.roles/users` tối thiểu theo cột v7 (`IF NOT EXISTS`) — hợp nhất với migration Auth khi ghép repo.
- **Chấm điểm & xếp hạng (Đạt):** đọc `live.weekly_set_items` (`is_voided`), `live.test_cases.expected_result` (`columns`, `rows`, `result_hash`, `compare_mode`). Cần tạo `live.weekly_results` và đăng ký hàm vào `app.services.weekly.CLOSE_HOOKS` để `close` ghi kết quả/`pass_rate` **trong cùng transaction** (xem `docs/WEEKLY_SETS.md`). Các trường `solved`, `solved_count`, `attempt_count` hiện trả `false/0` vì chưa có bảng bài nộp.
- **Frontend:** response/enum bám OpenAPI v7; trường bổ sung và khác biệt ở `docs/DESIGN_DECISIONS.md`.
