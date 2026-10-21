# Bộ đề tuần

Nguồn quy tắc: Design v7 (`business_rules.md` mục 4, state machine, bảng ràng buộc). Dữ liệu: `live.weekly_sets`, `live.weekly_set_items` (migration `0002`).

## Vòng đời
Theo tài liệu chốt: **mỗi tuần một bộ, mục tiêu 20 câu = 5 Easy + 10 Medium + 5 Hard** (`weekly.question_count`); admin chủ động sinh thừa (20–30 đề/đợt, `generation.max_quantity`) để dự phòng; bộ đề có thể sẵn sàng/publish vào bất kỳ ngày nào trong tuần.

`draft → published → closed`. Chỉ **một** bộ PUBLISHED tại một thời điểm (unique index một phần; có test). Mỗi câu chỉ thuộc **một** bộ (`UNIQUE(question_id)`). `week_start` là duy nhất.

| Bước | Điều kiện | Kết quả |
|---|---|---|
| Tạo (`POST /admin/weekly-sets`) | tuần chưa có bộ | Chọn câu `ready`, không bị gắn cờ, **có test case hợp lệ đúng dataset/version hiện hành của world**, chưa từng gán bộ, theo `weekly.question_count`; xoay vòng theo kỹ năng chính; xếp `position` Easy→Medium→Hard |
| Thiếu hụt | số câu `ready` < mục tiêu | `deficits_by_difficulty`; mỗi độ khó thiếu → job sinh bổ sung (tất cả skill active; ≤ 30 draft/job). Hết ngân sách ⇒ không xếp job, bộ giữ DRAFT, ghi `warnings`. **Không nới tiêu chí chất lượng**; job xong **không tự thêm câu** vào bộ — admin cập nhật items khi còn DRAFT |
| Sửa items (`PUT …/items`) | bộ còn DRAFT | Câu phải `ready`, không gắn cờ, test case hợp lệ đúng dataset/version, chưa thuộc bộ khác; thay toàn bộ trong một transaction |
| Publish | DRAFT, không rỗng, không có bộ khác PUBLISHED, mọi câu `ready` + không gắn cờ + test case hợp lệ đúng dataset/version (kiểm tra lại lúc publish phòng dataset đổi phiên bản) | `published_at`; cổng duyệt cuối của admin |
| Close ("đóng bộ cũ để chuyển bộ mới") | PUBLISHED; mặc định admin đóng chủ động, chỉ chặn trước mốc `week_start + 7 ngày` khi bật `weekly.close_requires_cutoff` | Một transaction: khóa bộ → chạy `CLOSE_HOOKS` → câu `ready` trong bộ → `archived` (không ghi đè `retired`) → `closed` |

`ends_at` = 00:00 ngày `week_start + 7` theo `APP_TIMEZONE` (giả định của backend; chỉ để hiển thị và cho cutoff tùy chọn).

**Dataset/version:** test case lưu `dataset_version` (int từ `core.worlds`) và `dataset_fingerprint` (hash catalog lúc sinh). Backend chặn câu có test case lệch `dataset_version` hiện hành; so khớp `dataset_fingerprint` với dữ liệu thật thuộc module chấm điểm.

## Tác động của retire
- Câu trong bộ **PUBLISHED**: `is_voided = true` (vẫn hiển thị cho người học, bị loại khỏi bảng điểm).
- Câu trong bộ **DRAFT**: bị gỡ khỏi bộ và đánh lại `position`.
- `restore` chỉ khi câu **chưa từng** nằm trong bộ nào (còn dòng item ⇒ 409 `QUESTION_ALREADY_USED`).

## Người học
Chỉ thấy câu thuộc bộ PUBLISHED (lọc theo độ khó / kỹ năng / tên `q` / `solved`). Câu ngoài bộ, bộ DRAFT, hoặc câu của bộ đã đóng (đã archive) đều trả 404. Bộ đã đóng chỉ còn **lịch sử tóm tắt** qua `GET /weekly/history` (tên, tuần, số câu, số câu void) — không mở lại đề. Số câu passed của người dùng thuộc module chấm điểm và không bị đóng tuần đụng tới.

## Điểm nối cho module chấm điểm/xếp hạng
`app.services.weekly.CLOSE_HOOKS` là danh sách hàm `(conn, set_id) -> dict | None` chạy **trong transaction đóng tuần**. Module xếp hạng đăng ký hàm ghi `weekly_results`, cập nhật `pass_rate` (theo mẫu người dùng duy nhất) tại đây; hook ném lỗi ⇒ toàn bộ đóng tuần rollback (có test). Khi chưa có hook, `close` trả cảnh báo "weekly_results/pass_rate CHƯA được tính". Backend này **không** tạo `weekly_results`, `user_stats`, bảng bài nộp.
