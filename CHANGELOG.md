# Changelog

## [1.2.0] — Khớp Tài liệu chốt
- Mặc định bộ đề tuần **20 câu = 5/10/5** (trước đó 50 câu theo seed v7); `weekly.close_requires_cutoff` mặc định tắt.
- Chọn/publish đề yêu cầu **test case hợp lệ đúng dataset/version** (`invalid_test_cases`, `stale_dataset_version`).
- Admin **chỉnh sửa** draft `needs_human`/`rejected`: `PATCH /admin/drafts/{id}`, `POST …/requeue`; draft về `pending` và chạy lại toàn bộ cổng. Sửa lỗi đánh số `review_round` để vòng review lại không bị mất bằng chứng.
- Người học: `GET /weekly/history` (lịch sử tóm tắt), lọc theo tên `q`. Job sinh đề: `skill_ids` tùy chọn.
- Tài liệu: bảng đối chiếu phạm vi (DESIGN_DECISIONS §4). 46 test.

## [1.1.0] — Bộ đề tuần
- Thêm `live.weekly_sets`, `live.weekly_set_items` (migration `0002`).
- API quản trị bộ đề tuần: tạo (tự chọn đề READY, tính thiếu hụt, xếp job sinh bổ sung), thay items, publish, close (atomic, archive câu READY, `CLOSE_HOOKS`).
- **Đổi API người học:** bỏ `GET /questions` (pool phẳng); thêm `GET /weekly/current`, `GET /weekly/current/questions`; `GET /questions/{id}` chỉ trả câu thuộc bộ PUBLISHED.
- `retire` câu trong bộ PUBLISHED ⇒ `is_voided`; trong bộ DRAFT ⇒ gỡ và đánh lại thứ tự. `restore` chặn câu từng thuộc bộ.
- Thêm cấu hình `weekly.question_count`, `weekly.close_requires_cutoff`; `GET /admin/questions` có `weekly_set_id`.
- Tài liệu: `docs/API.md`, `docs/WEEKLY_SETS.md`, `docs/OPERATIONS.md`, `CHANGELOG.md`; cập nhật README và DESIGN_DECISIONS. 40 test.

## [1.0.0] — AI Pipeline & Question Management
- Backend FastAPI + Worker: job sinh đề, draft, kiểm duyệt Model B, admin approve/reject, promote sang `live.questions` + `live.test_cases`.
- BudgetGuard + `llm_call_ledger`; lease/heartbeat/fencing; settings registry; audit log.
- Migration `0001`; seed 50 đề nguồn; `ai/` giữ nguyên.
