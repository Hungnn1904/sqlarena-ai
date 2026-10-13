# Hướng Dẫn Cài Database Và Chạy AI

## 1. Phần Mềm Và Thư Viện Cần Có

Cài các phần mềm sau trước khi chạy dự án:

| Phần mềm | Yêu cầu |
|---|---|
| PostgreSQL và pgAdmin 4 | Chạy và quản lý database; dùng cổng `5432`, ghi nhớ mật khẩu tài khoản `postgres` |
| Python | Cài Python kèm pip; dự án đang dùng Python 3.14.1 |
| Ollama | Chạy model `llama3` để sinh đề |

Có thể tải [PostgreSQL](https://www.postgresql.org/download/windows/) và [Ollama](https://docs.ollama.com/windows) từ trang chính thức. Khi cài Python, chọn **Add Python to PATH**.

Mở PowerShell tại thư mục dự án, nơi có `ai`, `postgre`, `build` và README này. Cài thư viện Python:

```powershell
python -m pip install "psycopg[binary]" python-dotenv pglast scikit-learn
```

Các thư viện gồm: `psycopg` kết nối PostgreSQL, `python-dotenv` đọc cấu hình, `pglast` phục vụ validator và `scikit-learn` kiểm tra tương đồng đề.

## 2. Cài Database Bằng File SQL

Dự án sử dụng hai database:

| Database | Nội dung |
|---|---|
| `enterprise_db` | 16 bảng nghiệp vụ và dữ liệu dùng để luyện SQL |
| `sqlarena_db` | Schema `core` lưu câu nguồn; schema `draft` lưu đề AI sinh |

**Các bước tạo bảng và import bên dưới chỉ dành cho cài mới. Nếu DB đã có cấu trúc và dữ liệu đúng, bỏ qua và chuyển đến mục 3. Không chạy lại `generate_seed.py`, không xóa hoặc reset DB.**

### 2.1. Cài enterprise_db

1. Mở pgAdmin, kết nối PostgreSQL server bằng tài khoản đã cài, ví dụ `postgres`.
2. Nhấp phải **Databases > Create > Database**, nhập `enterprise_db`, chọn Save.
3. Nhấp phải **enterprise_db > Query Tool**.
4. Dùng **Open File** để mở và chạy toàn bộ từng file theo thứ tự dưới đây. Không chọn riêng một đoạn SQL. Kiểm tra Results/Messages sau mỗi file; nếu báo lỗi thì dừng, không chạy file tiếp theo.

| Thứ tự | File SQL | Tác dụng |
|---|---|---|
| 1 | `postgre/enterprise_db/schema_code.sql` | Tạo bảng và cấu trúc schema cuối cùng |
| 2 | `postgre/enterprise_db/constraint.sql` | Thêm ràng buộc và index |
| 3 | `build/enterprise_seed_data.sql` | Nạp dữ liệu đã có sẵn trong file SQL |
| 4 | `postgre/enterprise_db/validate_enterprisedb_br01_br16.sql` | Kiểm tra Business Rules BR01–BR16 |
| 5 | `validate_scenario_coverage.sql` | Kiểm tra các tình huống dữ liệu |

Tất cả các file trên chạy trong **enterprise_db**. File dữ liệu chỉ import vào các bảng trống, không chạy lần hai.

Sau kiểm tra BR, cần thấy BR01–BR16 đều `PASS`, `overall_status = PASS`, `total_violations = 0`. Đọc cả các kết quả bổ sung cuối file; chỉ có thông báo chạy SQL thành công chưa đủ. Scenario coverage không được có dòng `FAIL`.

### 2.2. Cài sqlarena_db

1. Trong pgAdmin, tạo database mới tên `sqlarena_db`.
2. Nhấp phải **sqlarena_db > Query Tool**.
3. Mở và chạy toàn bộ hai file theo thứ tự:

| Thứ tự | File SQL | Tác dụng |
|---|---|---|
| 1 | `postgre/sqlarena_db/01_create_sqlarena_core.sql` | Tạo schema Core và Draft, bao gồm các cột bổ sung cuối file |
| 2 | `postgre/sqlarena_db/02_insert_sqlarena_core_data.sql` | Nạp World, kỹ năng và 50 câu nguồn vào Core |

Tất cả chạy trong **sqlarena_db**, không chạy trong enterprise_db.

Kết quả cuối file 02 cần có: `worlds=1`, `skills=6`, `templates=0`, `source_questions=50`.

File 01 đã dùng cấu trúc Draft mới: có `schema_text`, giữ `schema_context`, không có cột đáp án `reference_sql` trong `draft.question_drafts`. Cài mới bằng file này không cần chạy thêm migration.

**File 02 chỉ nạp Core, không nạp Draft.** Draft được thêm đề khi chạy Python AI ở chế độ lưu. Đáp án 50 câu nguồn trong `core.source_questions.reference_sql` vẫn giữ nguyên.

## 3. Cấu Hình Và Chạy Python AI

### 3.1. Cấu Hình Kết Nối

Dự án có file mẫu [ai/.env.example](ai/.env.example), không chứa mật khẩu thật. Sau khi pull về, chạy một lần để tạo cấu hình local nếu chưa có:

```powershell
if (-not (Test-Path -LiteralPath 'ai/.env')) {
    Copy-Item -LiteralPath 'ai/.env.example' -Destination 'ai/.env'
}
```

Mở `ai/.env`, điền `ARENA_DB_PASSWORD` và `CATALOG_DB_PASSWORD` bằng mật khẩu PostgreSQL trên máy. Kiểm tra host, port, user và tên DB nếu máy bạn dùng cấu hình khác. Nếu `.env` đã có cấu hình đúng thì giữ nguyên.

**Đưa `.env.example` lên GitHub; giữ `.env` trên máy, không commit.**

`ARENA_DB_*` kết nối SQLArena; `CATALOG_DB_*` đọc EnterpriseDB. Giữ các dòng `ENTERPRISE_DB_*` như mẫu: pipeline hiện không chạy đáp án SQL nên không cần điền login ở hai dòng cuối. Không chia sẻ file chứa mật khẩu.

### 3.2. Chuẩn Bị Model

Mở Ollama. Trong PowerShell, tải model nếu chưa có:

```powershell
ollama pull llama3
```

Kiểm tra model đã tải:

```powershell
ollama list
```

Giữ PostgreSQL và Ollama hoạt động khi chạy AI.

### 3.3. Kiểm Tra Kết Nối

Từ thư mục gốc dự án:

```powershell
python ai/main.py --check
```

Cần thấy Core có **50 câu, 6 kỹ năng, 16 bảng Enterprise**, thông báo **JSON smoke OK** và không có dòng **Chặn sinh**. Lệnh này không lưu đề vào DB.

### 3.4. Chạy Sinh Đề

Để sinh đề và lưu các câu đạt kiểm tra sơ bộ vào Draft:

```powershell
python ai/main.py
```

Nhập lần lượt số câu, độ khó, kỹ năng, chủ đề, bảng ưu tiên và yêu cầu bổ sung. Có thể Enter để bỏ qua hai phần tùy chọn cuối. Đọc đúng nhãn kỹ năng trên menu, rồi nhập `y` để xác nhận.

Nếu chỉ muốn thử mà **không lưu Draft**, dùng lệnh này thay cho lệnh trên:

```powershell
python ai/main.py --dry-run
```

Cả hai chế độ đều xuất kết quả vào `ai/outputs/generation_*.json`. Chế độ thường lưu câu đạt sơ bộ vào `draft.question_drafts` với trạng thái `pending`; AI không sinh đáp án SQL và không thay đổi dữ liệu EnterpriseDB.

Để xem đề đã lưu, chạy trong Query Tool của **sqlarena_db**:

```sql
SELECT draft_id, question, difficulty, skills, schema_text, status
FROM draft.question_drafts
ORDER BY draft_id DESC
LIMIT 10;
```

`pending` nghĩa là cần duyệt tiếp, không phải đề đã được công nhận đúng hoàn toàn.

## 4. Các File Và Thư Mục Cần Biết

Phần này chỉ để tra cứu, không phải các bước cần chạy thêm khi cài đặt.

### Tài Liệu Và File Database

| File | Nội dung cơ bản |
|---|---|
| [Schema database.docx](<Schema database.docx>) | Tài liệu thiết kế bảng, cột và quan hệ của EnterpriseDB |
| [rang_buoc.docx](rang_buoc.docx) | Các ràng buộc và Business Rules nghiệp vụ |
| `postgre/enterprise_db/` | SQL tạo bảng, bổ sung ràng buộc và kiểm tra BR của EnterpriseDB |
| `build/enterprise_seed_data.sql` | Dữ liệu SQL đã xuất sẵn để import khi cài mới |
| `postgre/enterprise_db/enterprise_50_questions_answers.sql` | 50 câu nguồn và đáp án SQL để tự chạy lại trên EnterpriseDB |
| [sqlarena_database_guide.md](postgre/sqlarena_db/sqlarena_database_guide.md) | Thông tin chi tiết về SQLArena và kiểm tra dữ liệu Core |

Tài liệu Word giúp hiểu thiết kế/nghiệp vụ; cấu trúc thực tế cần đối chiếu SQL và database đang dùng.

### Các Thư Mục Chính

| Thư mục | Dùng để làm gì |
|---|---|
| `question_create/` | Bộ quy tắc của 50 câu nguồn: độ khó, kỹ năng, nghiệp vụ và yêu cầu metadata |
| `question_generation/` | Bộ 50 câu nguồn đã xây dựng; đọc `questions_validated.json` để xem đề/đáp án, `validation_report.json` để xem kiểm chứng |
| `sqlarena_create/` | Tài liệu ánh xạ bộ câu nguồn vào Core và bằng chứng import |
| `seed_create/` | Tài liệu thiết kế dữ liệu và các tình huống Dataset; không cần chạy lại để dùng DB hiện có |
| `ai/` | Pipeline sinh đề hiện tại: `main.py` điều phối, `validator.py` kiểm tra sơ bộ, `.env` lưu cấu hình |
| `ai/outputs/` | JSON kết quả của từng lượt AI sinh đề |
| `logs/` | Log các bước dựng và kiểm tra DB trước đó, dùng để tra cứu |

Hướng dẫn riêng đã được đặt tên theo nội dung: [enterprise_source_questions_guide.md](question_generation/enterprise_source_questions_guide.md) cho bộ 50 câu nguồn; [pipeline_ai_notes.md](ai/pipeline_ai_notes.md) cho ghi chú AI. Các phần ghi rõ Historical là thông tin phiên bản cũ.

### AI Lưu Kết Quả Ở Đâu?

- `python ai/main.py`: lưu câu đạt sơ bộ vào `sqlarena_db.draft.question_drafts` với trạng thái `pending`, **đồng thời xuất JSON** vào `ai/outputs/generation_*.json`.
- `python ai/main.py --dry-run`: vẫn xuất JSON nhưng **không lưu Draft**.
- JSON ghi câu sinh ra, metadata, các lần thử và lỗi kiểm tra. Không phải câu nào có trong JSON cũng đã được lưu DB; xem `draft_id` và `saved_count` để biết kết quả lưu.
- `question_generation/questions_validated.json` là bộ **50 câu nguồn**, khác với JSON đề mới trong `ai/outputs/`. Pipeline AI hiện không sinh đáp án SQL.
