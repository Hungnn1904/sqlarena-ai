# PROMPT — Tạo `sqlarena_db` và bàn giao đúng 2 file SQL (DDL + data)

Hãy đọc và thực hiện **đúng file quy tắc đính kèm `sqlarena_core_mapping_rules_v2.md`**. Đây là đặc tả chính về các bảng, cột, FK, ánh xạ dữ liệu và kiểm chứng. Không thiết kế lại hoặc mở rộng ngoài phạm vi.

**Bối cảnh đã hoàn tất:** `enterprise_db` đã có 16 bảng và dataset; `questions_validated.json` đã có **50 câu SQL nguồn**, metadata và Reference SQL; file `enterprise_50_question_rules_v1.md` quy định taxonomy và quota. Không sinh lại bất kỳ dữ liệu hoặc câu hỏi nào.

## Yêu cầu thực hiện

1. Đọc các file hiện có (JSON 50 câu, Rules, tài liệu Core, schema/BR) và chỉ đọc cấu trúc `enterprise_db` nếu cần để lấy metadata chính xác.
2. Tạo một PostgreSQL database **riêng tên `sqlarena_db`** nếu nó chưa tồn tại và có quyền; không xóa/ghi đè DB đã có. DB này chứa schema `core` với đúng 4 bảng `worlds`, `skills`, `templates`, `source_questions`.
3. **Bắt buộc tạo 2 file SQL thực sự chứa mã SQL hoàn chỉnh:**
   - **`01_create_sqlarena_core.sql`**: tạo schema `core`, 4 bảng, các PK/FK/CHECK/index. **Chỉ DDL, không chứa dữ liệu INSERT.** File chạy trong `sqlarena_db` đã được tạo trước đó.
   - **`02_insert_sqlarena_core_data.sql`**: **SQL INSERT đầy đủ và tự chứa**, nạp **1 `worlds`**, **6 `skills` (S1–S6)**, **50 `source_questions`** lấy nguyên từ `questions_validated.json`, **0 `templates`**. Có transaction và kiểm tra DB đích trống trước khi nạp. File phải mở chạy trực tiếp trong pgAdmin trên `sqlarena_db`, **không cần Python hay file JSON khi thực thi**.
4. `world_id` phải dùng **`enterprise_v1`** như JSON; trường `database_name` trong `core.worlds` là **`enterprise_db`**. Đó là metadata ánh xạ; không có FK xuyên database.
5. Lưu nguyên `question_text`, `reference_sql` và `validation` từ JSON, giữ metadata phụ dưới JSONB; không tự chỉnh nội dung hoặc gán độ khó mới. Không chạy reference SQL trong import.
6. Nếu có quyền, thực sự chạy hai file trên `sqlarena_db` mới, kiểm tra counts **1 / 6 / 0 / 50**, FK, quota 20/20/10, nhóm kỹ năng/domain và đối chiếu dữ liệu SQL với JSON. Nếu không chạy được, báo thẳng là **chưa thực thi**, không tự nhận PASS.
7. Bàn giao **hai file SQL**, `sqlarena_database_guide.md` (cách tạo DB, chạy lần lượt hai SQL bằng pgAdmin) và `core_import_report.md` (kết quả xác minh).

**Cấm:** chạy Generator/seed, sửa dữ liệu hoặc schema `enterprise_db`, tạo DB `draft/live`, sinh lại 50 câu, xóa/RESET/TRUNCATE, đẩy mật khẩu vào SQL, hoặc đưa pseudocode/INSERT thiếu dữ liệu. Nếu phải dùng Python để **xuất** INSERT từ JSON, được phép, nhưng thành phẩm giao cho tôi vẫn phải là hai file `.sql` có thể chạy độc lập theo thứ tự.

Hãy tự thực hiện và báo cáo kết quả, không yêu cầu tôi nhập thủ công 50 câu.
