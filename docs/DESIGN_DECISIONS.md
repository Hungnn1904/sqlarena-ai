# Quyết định thiết kế & giới hạn — AI Pipeline & Question Management

Tài liệu liên quan: [`API.md`](API.md) · [`WEEKLY_SETS.md`](WEEKLY_SETS.md) · [`OPERATIONS.md`](OPERATIONS.md) · [`../CHANGELOG.md`](../CHANGELOG.md)

## 1. Kiến trúc
- **Giữ nguyên `ai/`** (0 dòng bị sửa). Backend nạp nó như thư viện và chỉ thay 3 thứ: (a) cấu hình (thay `.env` + CLI tương tác), (b) truy cập DB (CLI cũ ghi thẳng schema v1 → repository trên schema mới), (c) một lớp chặn duy nhất quanh `arena.ollama_request` để áp ngân sách + ghi ledger. Logic sinh/kiểm tra (validator, guard SQL, đồng thuận, contract, semantic audit) là mã đã có, không viết lại.
- **Worker tách process, hàng đợi PostgreSQL** (`FOR UPDATE SKIP LOCKED`), lease + heartbeat + **fencing token** (`lease_version`): worker mất lease không ghi đè được kết quả (có test).
- **Fail-closed:** thiếu bằng chứng, lỗi hạ tầng, hết ngân sách, kết quả bị cắt/không xác định ⇒ không bao giờ thành `approved`. Lỗi hạ tầng/ngân sách trả draft về `pending` và hoàn lượt review.
- **Promote nguyên tử:** `approved` + `live.questions` + `live.test_cases` trong một transaction; `source_draft_id UNIQUE` ⇒ retry không tạo bản sao và không ghi đè `expected_result`.
- **Admin không bỏ qua cổng bắt buộc.** Khi approve, SQL được chạy lại trên mọi dataset qua cùng guard/consensus/contract. Chỉ các lý do "cần phán đoán của người" (`ADMIN_OVERRIDABLE` trong `pipeline/review.py`: kết quả rỗng, lệch cột, thiếu tie-breaker, nghi trùng…) được admin xác nhận; thiếu `ORDER BY` khi đề yêu cầu, kết quả bị cắt, không xác định… ⇒ `409 MANDATORY_GATE_FAILED`. Semantic audit LLM được thay bằng *xác nhận của admin* và ghi rõ `admin_attested`/`admin_overrides`/`audit_logs`.
- **Ngân sách LLM hai tầng:** (1) khi tạo job: `đã dùng hôm nay + ước lượng job đang chờ + ước lượng job mới > trần` ⇒ 429 (ước lượng = `quantity × (1 + k)`, chưa tính retry); (2) mỗi call: reserve có khóa advisory trước khi gửi, call lỗi/timeout vẫn tính. Ollama hỏng 2 slot liên tiếp ⇒ job `failed(system)` thay vì đốt hết ngân sách.

## 2. Khác biệt so với Design v7 (có chủ đích)
| # | Thay đổi | Lý do |
|---|---|---|
| 1 | **Sửa lỗi cú pháp `db/postgres_schema.sql`**: thiếu `;` sau `COMMENT ON COLUMN draft.generation_jobs.lease_expires_at` (dòng 143) làm cả file không nạp được (đã xác minh trên PostgreSQL 16). | Lỗi thật của bản thiết kế; baseline mới đã sửa. **Nên sửa cả file gốc v7.** |
| 2 | `core.skills.code` (S1–S6); `core.worlds.name` = khóa nội bộ `enterprise_v1`; `schema_description`/`business_rules` đổi `text`→`jsonb`. | Pipeline hiện có định danh skill bằng S1–S6 và cần metadata có cấu trúc để dựng context. |
| 3 | Giữ `core.source_questions` (50 đề nguồn đã kiểm chứng) thay vì nhập vào `live.questions`. | Là corpus tham chiếu/phát hiện trùng của engine; không phải đề cho người học, nên không để lẫn trong pool. |
| 4 | `draft.question_drafts` thêm `schema_text`, `schema_context`, `validation_report` (jsonb), `status_reason`, `review_attempts`, lease review. `live.questions` thêm `tables_used`, `schema_text`. | Engine review cần đúng các ngữ cảnh này; người học cần schema liên quan. |
| 5 | `review_logs.stage` thêm `semantic_audit`, `decision`; `self_solve_runs` thêm `exec_status,row_count,result_hash,error,review_model,review_round`. | Ghi đủ bằng chứng mà engine thực sự tạo ra. |
| 6 | Không có `draft.test_cases`: test case sinh trong lúc review nằm trong kết quả engine và được ghi **thẳng** vào `live.test_cases` khi promote. | Approve là một bước nguyên tử; tránh hai nguồn sự thật. |
| 7 | `expected_result` = `{columns, rows, row_count, result_hash, compare_mode, dataset_fingerprint}`; `dataset_version` int lấy từ world, hash catalog nằm trong `dataset_fingerprint`. | v7 để `expected_result` jsonb tự do; đây là hợp đồng cho Đạt (sandbox chấm điểm). |
| 8 | **API người học đi theo bộ đề tuần**: `GET /weekly/current`, `GET /weekly/current/questions`, `GET /questions/{id}` (chỉ câu thuộc bộ PUBLISHED). Không có pool phẳng. | Yêu cầu của nhóm (không dùng pool phẳng); khớp OpenAPI v7. Câu ngoài bộ trả 404 để không lộ tồn tại. |
| 9 | Thêm `live.weekly_sets/weekly_set_items` (migration `0002`) và API quản trị bộ đề trong gói này. `weekly_results`, `user_stats`, bảng bài nộp **không** tạo. `close` archive câu READY và chạy `CLOSE_HOOKS` cùng transaction; `solved/solved_count/attempt_count` trả `false/0/0`. | Phân việc chưa giao bộ đề tuần cho ai nên làm ở đây để API người học chạy độc lập (tách `services/weekly.py`); phần chấm điểm thuộc module khác. Chi tiết `WEEKLY_SETS.md`. |
| 9b | Mặc định theo **tài liệu chốt**: mỗi tuần 20 câu = 5/10/5 (v7 seed là 20/20/10), admin đóng tuần cũ chủ động (`weekly.close_requires_cutoff` mặc định tắt; v7 yêu cầu sau cutoff — vẫn bật được). Mốc `ends_at` = 00:00 ngày `week_start + 7` theo `APP_TIMEZONE`. Job sinh bổ sung do thiếu hụt **không tự thêm câu** vào bộ. | Tài liệu chốt mới hơn v7; thêm câu tự động sẽ làm bộ đề đổi âm thầm. |
| 9d | Chọn đề vào bộ yêu cầu **test case hợp lệ đúng dataset/version** (có ít nhất một, không cái nào lệch `dataset_version` của world), kiểm ở lúc chọn và lúc publish. | Tài liệu chốt §3.2. |
| 9e | Admin **chỉnh sửa** draft `needs_human`/`rejected` (`PATCH`/`requeue`): draft về `pending`, xóa đáp án cũ, chạy lại toàn bộ cổng; bằng chứng được giữ theo `review_round`. Không có đường nào đưa needs_human thành READY ngoài `approve` (vẫn chạy lại cổng). | Tài liệu chốt: "chỉnh sửa nếu cần" và "không tự chuyển needs_human thành READY". |
| 9f | `GET /weekly/history`: lịch sử **tóm tắt** các tuần đã đóng, không nội dung đề. `skill_ids` của job là tùy chọn. | Tài liệu chốt: người học chỉ xem lịch sử tóm tắt; sinh đề theo độ khó/số lượng/chủ đề. |
| 9c | Chưa làm: CRUD prompt/template/world, planner LLM. Prompt của engine nằm trong code (`ai/main.py`, `ai/review.py`) và được ghi vào ledger qua `prompt_version`. | Ngoài phạm vi phân việc. |
| 10 | `PUT /admin/settings/{key}` chỉ nhận key đã đăng ký (`services/settings_registry.py`) với kiểu/min/max/trần cứng. | Tránh cấu hình tùy ý nới trần an toàn. |

## 3. Giới hạn & rủi ro đã biết (đọc trước khi demo/bảo vệ)
1. **Chưa chạy với Ollama/model thật** (môi trường dựng backend không có GPU/Ollama). Mọi test dùng `FakeOllama` thay *chỉ* HTTP; engine, SQL, DB là thật. Cần chạy `python -m app.cli check` rồi một job `quantity=1` trên máy có Ollama trước khi dựa vào chất lượng sinh/giải.
2. **Chỉ có 1 dataset (base)**: engine tự ghi chú "chỉ 1 dataset ⇒ chưa bắt được đáp án hardcode". Khi Đạt có biến thể dataset, khai báo `REVIEW_VARIANT_DBS` (engine `ai/review.py`) là đủ để sinh thêm test case ẩn; số mẫu giải k lấy từ cấu hình DB `solve.samples_k` (thay `REVIEW_SAMPLES`).
3. Ước lượng ngân sách khi tạo job không tính retry/repair/audit; trần runtime mới là chốt chặn cuối.
4. Worker mặc định 1 call LLM đồng thời (`llm.max_concurrent`, cần restart khi đổi).
5. `live.users/roles` ở đây là bản tối thiểu để chạy độc lập; cần hợp nhất với migration Auth.
6. Chưa có rate-limit HTTP riêng cho endpoint admin (OpenAPI v7 có 429 chung).
7. **Bộ đề tuần:** `close` chưa ghi `weekly_results`/`pass_rate` (cần module xếp hạng đăng ký `CLOSE_HOOKS`); `solved`, `solved_count`, `attempt_count` chưa có nguồn dữ liệu bài nộp; lọc theo trạng thái làm bài (`solved`) chưa có tác dụng.
8. Thuật toán chọn đề tự động chỉ xoay vòng theo kỹ năng chính, chưa cân bằng theo domain nghiệp vụ hay độ mới của đề.

## 4. Đối chiếu phạm vi (Phân việc 17/10/2026 + Tài liệu chốt)
| Yêu cầu | Trạng thái | Ở đâu |
|---|---|---|
| Tích hợp Model A + Model B vào backend | ✅ | `app/pipeline/*`, `app/worker.py` (engine `ai/` giữ nguyên) |
| API + DB: sinh đề, trạng thái job, draft, kết quả kiểm duyệt, test case | ✅ | `admin/generation-jobs`, `admin/drafts`, `review_logs`, `self_solve_runs`, `live.test_cases` |
| Draft → kiểm duyệt → review thủ công → đủ điều kiện xuất bản | ✅ | worker + `approve`/`reject`/`PATCH`/`requeue` |
| API danh sách câu hỏi đã xuất bản cho người học | ✅ | `weekly/current/questions`, `questions/{id}` (đi theo bộ đề tuần) |
| Admin khởi chạy pipeline, xem tiến độ/kết quả, xử lý `needs_human` | ✅ | `admin/generation-jobs[/{id}]`, `admin/drafts` |
| Sinh đề theo độ khó, số lượng, chủ đề, xem trạng thái | ✅ | `POST /admin/generation-jobs` |
| Xử lý đề bị từ chối + `needs_human`, chỉnh sửa nếu cần | ✅ | `reject`, `PATCH`, `requeue`, danh sách lọc theo status |
| Chỉ đề READY + test case hợp lệ đúng dataset/version vào bộ đề; không tự chuyển needs_human thành READY | ✅ | `services/weekly.py` (`VALID_TESTS`), `drafts.approve` |
| Bộ đề tuần 20 câu (5/10/5), đăng bộ mới / đóng bộ cũ | ✅ | `admin/weekly-sets*` |
| Đóng tuần: ARCHIVED, người học chỉ xem lịch sử tóm tắt, không mở lại đề | ✅ (câu → `archived`, bộ → `closed`) | `close`, `weekly/history` |
| Báo cáo/gắn cờ không tự xóa đề giữa tuần | ✅ phần của mình: không có đường xóa; câu gắn cờ không được chọn vào bộ mới | `is_flagged` |
| Migration + test + tài liệu setup/sử dụng/testing | ✅ | Alembic 0001–0002, 46 test, `docs/*.md` |
| Tech stack: FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL, worker + queue, JWT, pytest + HTTPX | ✅ với 2 lưu ý ↓ | |
| Ngoài phạm vi (theo yêu cầu bỏ qua): đăng ký/đăng nhập, sandbox/nộp bài/chấm, xếp hạng, báo lỗi từ người học, thống kê, quản lý tài khoản, Docker Compose, frontend | — | module của Đạt/Nguyên |

Lưu ý về stack: (1) truy vấn dùng **SQLAlchemy 2.x Core + SQL tường minh** (không khai báo ORM model) để kiểm soát khóa/transaction của hàng đợi; (2) request được Pydantic validate, còn **response là dict chưa khai báo `response_model`** nên Swagger chưa hiển thị schema response — việc cần làm tiếp nếu muốn hợp đồng response chặt. `sqlglot` không dùng vì engine `ai/` đã dùng `pglast` (parser PostgreSQL thật) để kiểm tra SQL.
