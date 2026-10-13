# Hướng Dẫn Database SQLArena

Database `sqlarena_db` lưu đề và metadata trong schema `core`, gồm đúng bốn bảng:
`worlds`, `skills`, `templates`, `source_questions`.
World `enterprise_v1` ánh xạ tới database luyện SQL `enterprise_db`; không có FK xuyên database.

File 01 còn tạo schema `draft` với bảng lưu đề AI, có `schema_text` và không có đáp án SQL trong `question_drafts`. File 02 chỉ nạp dữ liệu Core; Draft được thêm đề khi chạy AI ở chế độ lưu.

## Chạy bằng pgAdmin

1. Kiểm tra database `sqlarena_db`. Nếu chưa có, chọn Databases > Create > Database, nhập `sqlarena_db`. Nếu đã có thì chỉ dùng database trống và tương thích; không xóa database hoặc bảng cũ.
2. Mở Query Tool kết nối **sqlarena_db** và chạy toàn bộ `01_create_sqlarena_core.sql`.
3. Trên cùng database, mở và chạy toàn bộ `02_insert_sqlarena_core_data.sql`.
4. Kết quả SELECT cuối file data phải là `worlds=1`, `skills=6`, `templates=0`, `source_questions=50`.

Có thể tạo database riêng qua Query Tool kết nối database bảo trì `postgres`, bật Auto-commit,
chạy lệnh này một lần **chỉ khi sqlarena_db chưa tồn tại**:

```sql
CREATE DATABASE sqlarena_db;
```

Hai file chính không chứa CREATE DATABASE và không cần Python, JSON, extension hoặc lệnh psql lúc thực thi.
File 01 chỉ DDL và kiểm tra cấu trúc; file 02 chỉ INSERT dữ liệu cùng kiểm tra trước nhập.
Reference SQL nhiều dòng được lưu trong TEXT, không chạy trong import.
Giữ file UTF-8 để bảo toàn tiếng Việt.

## Khi chạy lại

- File 01 dùng IF NOT EXISTS và đối chiếu cột, kiểu, nullable, default, identity, PK/FK/CHECK/index. Khác cấu trúc thì báo lỗi và rollback; không tự sửa bảng.
- File 02 khóa bốn bảng trong transaction, kiểm tra cấu trúc và từ chối trước INSERT nếu bất kỳ bảng nào có dữ liệu. Không duplicate, overwrite hoặc reset.
- Nếu Query Tool còn transaction lỗi sau một lần chạy thất bại, chạy `ROLLBACK;` để kết thúc transaction đó. Đây không phải thao tác xóa dữ liệu.

## Kiểm tra

```sql
SELECT difficulty, COUNT(*) AS question_count
FROM core.source_questions
GROUP BY difficulty
ORDER BY difficulty;
-- easy=20, medium=20, hard=10

SELECT primary_skill_group, COUNT(*) AS question_count
FROM core.source_questions
GROUP BY primary_skill_group
ORDER BY primary_skill_group;
-- S1=8, S2=10, S3=10, S4=7, S5=10, S6=5

SELECT difficulty, primary_skill_group, COUNT(*) AS question_count
FROM core.source_questions
GROUP BY difficulty, primary_skill_group
ORDER BY difficulty, primary_skill_group;

SELECT primary_business_domain, COUNT(*) AS question_count
FROM core.source_questions
GROUP BY primary_business_domain
ORDER BY primary_business_domain;
-- Customer Management=8, Sales & Orders=13,
-- Product & Inventory=12, Human Resources=9, Finance=8

SELECT
  (SELECT COUNT(*) FROM core.source_questions q
   LEFT JOIN core.worlds w USING (world_id)
   WHERE w.world_id IS NULL) AS question_world_orphans,
  (SELECT COUNT(*) FROM core.source_questions q
   LEFT JOIN core.skills s ON s.skill_id=q.primary_skill_group
   WHERE s.skill_id IS NULL) AS question_skill_orphans,
  (SELECT COUNT(*) FROM core.templates t
   LEFT JOIN core.worlds w USING (world_id)
   WHERE w.world_id IS NULL) AS template_world_orphans;
-- Tất cả bằng 0

SELECT question_id, title, difficulty, primary_skill_group,
       validation->>'status' AS original_validation_status
FROM core.source_questions
ORDER BY question_id;
```

## Ánh xạ nguồn

`question_generation/questions_validated.json` là nguồn chuẩn. `secondary_skills` ánh xạ nguyên mảng vào `skills`.
Các field chưa tách thành cột được giữ nguyên trong `metadata`; `validation` là object gốc.
Có thể tái dựng lossless object nguồn từ các cột tách riêng và metadata, không cần sao chép thêm source_json.

`depth=NULL` vì chưa chốt generation depth. `created_at` là thời điểm import, không phải thời điểm tạo đề.
`base_difficulty` của S1–S6 là mức nền tham khảo, không thay độ khó từng câu.
`templates` để trống, không tạo 50 template giả.

Metadata World lấy bảng/cột/kiểu/PK/nullable/FK từ catalog EnterpriseDB thực tế bằng quyền chỉ đọc.
BR lưu trích đoạn tài liệu có nguồn và đoạn validator v1 tương ứng; đề xuất chưa áp dụng vẫn ghi rõ là đề xuất.
Các planted_traps chỉ ghi tình huống đếm được từ snapshot bảng gốc, không suy đoán.
Không có mật khẩu hoặc DSN chứa bí mật trong hai SQL và dữ liệu Core.

Xem `core_import_report.md` để biết kết quả đã thực thi. Bằng chứng chi tiết ở `sqlarena_create/evidence/`.
Script `sqlarena_create/build_core_artifacts.py` chỉ là công cụ xuất và kiểm chứng của Agent, không phải bước bắt buộc khi nhập bằng pgAdmin.
