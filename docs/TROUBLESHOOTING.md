# Hướng dẫn kiểm tra nhanh SQLArena AI

Tài liệu này bổ sung README, tập trung vào cách xác định lỗi trước khi thay đổi dữ liệu.

## Thứ tự chẩn đoán

1. **Python**: chạy `python --version`, `python -m pip check`.
2. **PostgreSQL**: trong pgAdmin xác nhận server online và database đích tồn tại.
3. **Core**: trong `sqlarena_db`, xác nhận `core.worlds`, `core.skills`, `core.source_questions` tồn tại và có dữ liệu.
4. **Enterprise dataset**: trong `enterprise_db`, xác nhận bảng nghiệp vụ tồn tại; kết nối mà pipeline dùng nên là read-only.
5. **Ollama**: chạy `ollama list`; model phải khớp `MODEL_NAME` và `REVIEW_MODEL_NAME`.
6. **Environment**: chạy lệnh từ thư mục gốc repo; kiểm tra `RULES_PATH` và các biến `*_DB_*` trong `ai/.env`.
7. Chạy `python ai/main.py --check`, sau đó `python ai/review.py --check`.

## Câu lệnh kiểm tra database

Trong Query Tool của `sqlarena_db`:

```sql
SELECT COUNT(*) FROM core.worlds;
SELECT COUNT(*) FROM core.skills;
SELECT COUNT(*) FROM core.source_questions;
SELECT COUNT(*) FROM draft.question_drafts;
```

Trong Query Tool của `enterprise_db`:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
```

Nếu các bảng không đúng như mong đợi, dừng và xác định database đang kết nối. Không xoá schema hay chạy script reset để “thử sửa”.

## Chọn chế độ chạy

- `python ai/main.py --check`: kiểm tra trước khi sinh, không ghi draft.
- `python ai/main.py --dry-run`: chạy thử sinh đề, xuất JSON, không ghi draft.
- `python ai/main.py`: sinh và lưu draft đạt kiểm tra sơ bộ.
- `python ai/review.py --check`: kiểm tra điều kiện Model B, không review.
- `python ai/review.py --draft-id <ID>`: chỉ review draft được chỉ định.

## Khi cần báo lỗi cho nhóm

Gửi:
- lệnh đã chạy và thư mục hiện tại;
- toàn bộ traceback từ dòng đầu đến cuối;
- phiên bản `python --version`, `ollama --version`;
- thông báo `--check` đã lược bỏ thông tin nhạy cảm;
- tên database/schema/bảng liên quan.

Không gửi password, nội dung `.env`, token, dump database chứa dữ liệu nhạy cảm hoặc log có thông tin xác thực.
