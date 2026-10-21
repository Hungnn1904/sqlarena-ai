# Vận hành

## Thành phần
| Thành phần | Lệnh | Ghi chú |
|---|---|---|
| API | `uvicorn app.main:app --port 8080` | Không gọi LLM trực tiếp (trừ chạy lại SQL khi admin approve) |
| Worker | `python -m app.cli worker` | Process riêng; chạy nhiều bản được (claim bằng `SKIP LOCKED`) |
| Một nhịp worker | `python -m app.cli worker --once` | Dùng khi debug |
| Kiểm tra | `python -m app.cli check` | Core + schema Enterprise + Ollama, không tốn call sinh |

Biến môi trường: xem `backend/.env.example`. Engine đọc mặc định từ `ai/.env.example`, rồi `backend/.env`, rồi biến môi trường.

## Ngân sách LLM
- Trần: `generation.daily_budget_calls` (ngày theo `APP_TIMEZONE`). Mỗi call (kể cả lỗi/timeout) ghi `draft.llm_call_ledger`; reserve có khóa advisory nên nhiều worker không vượt trần.
- Tạo job: từ chối 429 nếu `đã dùng + ước lượng hàng đợi + ước lượng job mới > trần` (ước lượng = `quantity × (1 + solve.samples_k)`).
- Hết ngân sách giữa chừng: job `failed` (`budget: …`), draft đang review trả về `pending` và hoàn lượt review.
- Xem mức dùng: `GET /admin/llm-usage`.

## Lease & khôi phục
- Job/draft giữ lease (`generation.lease_seconds`), heartbeat mỗi `generation.heartbeat_seconds`. Mất lease ⇒ worker bỏ kết quả (fencing token).
- Mỗi nhịp worker: job `running` quá hạn lease và đã đủ `generation.max_attempts` ⇒ `failed`; draft `reviewing` quá hạn ⇒ `pending`, hoặc `needs_human` nếu đã hết lượt. Ledger kẹt >15 phút ⇒ `failed(orphaned)`.
- `GET /health` cho biết số job/draft đang kẹt lease.

## Sự cố thường gặp
| Hiện tượng | Nguyên nhân / xử lý |
|---|---|
| Job `failed`: `system: Ollama/Model A không phản hồi` | Ollama tắt/quá tải; sinh 2 slot lỗi liên tiếp thì dừng để không đốt ngân sách. Bật Ollama rồi tạo job mới |
| Job `failed`: `config: …` | Chưa `seed`, hoặc schema Enterprise lệch `core.worlds` — chạy `python -m app.cli check` |
| Draft kẹt `pending` | Worker chưa chạy hoặc `released` do Ollama/ngân sách; xem log worker |
| Approve → 409 `MANDATORY_GATE_FAILED` | Lời giải vi phạm cổng bắt buộc (vd thiếu `ORDER BY` khi đề yêu cầu); chọn lời giải khác hoặc reject |
| Tạo bộ đề: `deficits` > 0 | Chưa đủ câu READY; chờ job bổ sung chạy + duyệt, rồi `PUT …/items` |
| `close` → 409 `BEFORE_CUTOFF` | Chỉ xảy ra khi đã bật `weekly.close_requires_cutoff`; tắt bằng `PUT /admin/settings/weekly.close_requires_cutoff {"value": false}` |
| Câu `ready` không vào được bộ (`invalid_test_cases`) | Thiếu test case hoặc test case lệch `dataset_version` hiện hành của world; sinh/duyệt lại câu đó |
| Draft `needs_human`/`rejected` cần xử lý | `PATCH /admin/drafts/{id}` (sửa tiêu đề/nội dung) hoặc `POST …/requeue`; worker review lại; hoặc `approve`/`reject` |
| Lỗi/triệu chứng của pipeline AI (prompt, Ollama, validator) | Xem `docs/TROUBLESHOOTING.md` |

## Sao lưu / migration
`python -m app.cli migrate` (Alembic). Downgrade `0002` chỉ xóa bảng bộ đề. Không migrate khi worker đang chạy job.
