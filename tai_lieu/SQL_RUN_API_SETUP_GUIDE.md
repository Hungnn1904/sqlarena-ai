# SQLArena SQL Run API: Setup va Huong Dan Test

Tai lieu nay huong dan rieng phan thuc thi SQL, nop bai, cham ket qua, tien do va bang xep hang trong thu muc `SQL_run_API`.

Pham vi hien tai chi danh cho cau lenh `SELECT` va `WITH`. Cac cau `INSERT`, `UPDATE`, `DELETE` chua duoc cho phep tren API nay.

## 1. Mo hinh database

He thong dung hai database PostgreSQL:

```text
enterprise_db
  Dataset 16 bang nghiep vu. API chay truy van doc tren database nay.

sqlarena_db
  Du lieu cau hoi, expected result, user, submission va bo de tuan.
```

Trong `sqlarena_db` co cac schema lien quan:

```text
core
  source_questions: 50 cau hoi, reference_sql, metadata, expected_result

app
  users, submissions, weekly_sets, weekly_set_questions

draft
  du lieu draft va review cua pipeline AI. Khong phai bang runtime de cham submission.
```

`enterprise_db` la dataset goc. `sqlarena_db` la database ung dung va du lieu cau hoi. Khong nham hai database nay voi nhau.

## 2. Cai dat va file cau hinh

Tai thu muc `SQL_run_API` co san file `requirements.txt`. Mo PowerShell tai thu muc nay va chay:

```powershell
cd SQL_run_API
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
```

Frontend `learner.html` khong can cai thu vien JavaScript. Chi can trinh duyet va Python de chay web server tinh.

Script sinh expected trong `SQL_run_API/postgre/app_db/populate_expected_results.py` dung cung cac thu vien:

```text
psycopg[binary]
python-dotenv
```

Neu sau nay chay lai pipeline AI sinh/review de thi moi can them cac dependency trong `requirements.txt` cua phan AI. Khong cai them pipeline AI chi de chay SQL API.

### Tao `.env`

Neu project da co mot file `.env` cau hinh o thu muc goc, dung chinh file do. Khong can tao them `.env` trong `SQL_run_API`.

Chi khi tai rieng thu muc `SQL_run_API` ma khong co file `.env` cau hinh cua project, copy `SQL_run_API/.env.example` thanh `SQL_run_API/.env`, sau do thay `CHANGE_ME` bang gia tri tren may local:

```env
ARENA_DB_HOST=localhost
ARENA_DB_PORT=5432
ARENA_DB_NAME=sqlarena_db
ARENA_DB_USER=postgres
ARENA_DB_PASSWORD=MAT_KHAU_POSTGRES_CUA_BAN

ENTERPRISE_DB_HOST=localhost
ENTERPRISE_DB_PORT=5432
ENTERPRISE_DB_NAME=enterprise_db
ENTERPRISE_DB_USER=sqlarena_ai_ro
ENTERPRISE_DB_PASSWORD=MAT_KHAU_CUA_ROLE_READ_ONLY

STATEMENT_TIMEOUT_MS=10000
MAX_RESULT_ROWS=100000
EXPECTED_TIMEOUT_MS=15000
```

Backend va script expected doc file `.env` cau hinh cua project; neu khong co thi moi dung `SQL_run_API/.env`. Chi duy tri mot file cau hinh, khong can tao ca hai. Neu dat file o ten/duong dan khac, dat bien moi truong `SQLARENA_ENV_FILE` tro toi file do. `ARENA_DB_USER` can quyen tao va ghi database `sqlarena_db`; `ENTERPRISE_DB_USER` phai la tai khoan doc dataset.

## 3. Cac file SQL va code trong SQL_run_API

### Enterprise database

```text
SQL_run_API/postgre/enterprise_db/schema_code.sql
SQL_run_API/postgre/enterprise_db/constraint.sql
SQL_run_API/postgre/enterprise_db/enterprise_seed_data.sql
SQL_run_API/postgre/enterprise_db/03_create_readonly_role.sql
SQL_run_API/postgre/enterprise_db/validate_enterprisedb_br01_br16.sql
```

`enterprise_seed_data.sql` la file du lieu seed can thiet khi tao `enterprise_db` moi.

### SQLArena database

```text
SQL_run_API/postgre/sqlarena_db/01_create_sqlarena_core.sql
SQL_run_API/postgre/sqlarena_db/02_insert_sqlarena_core_data.sql
SQL_run_API/postgre/app_db/01_create_app_tables.sql
SQL_run_API/postgre/app_db/populate_expected_results.py
SQL_run_API/postgre/app_db/db_readonly.py
```

`01_create_sqlarena_core.sql` da co san cot:

```sql
core.source_questions.expected_result JSONB
```

File nay cung tao cac bang `core` va `draft` can thiet. `02_insert_sqlarena_core_data.sql` them 50 cau hoi, reference SQL va metadata.

`01_create_app_tables.sql` tao schema `app`, cac khoa ngoai va du lieu test user/bo de tuan.

`03_create_review_pipeline.sql` chi tao bang review pipeline nhu `draft.test_cases`. Bang nay phuc vu pipeline AI va khong can chay de API submit hoat dong.

## 4. Kich ban A: Chua co database

### Buoc 1: Tao database

Trong pgAdmin, tao hai database rong:

```text
enterprise_db
sqlarena_db
```

Khong chay file Enterprise vao `sqlarena_db` va nguoc lai.

### Buoc 2: Tao Enterprise database

Ket noi Query Tool vao `enterprise_db`, chay theo thu tu:

```text
1. SQL_run_API/postgre/enterprise_db/schema_code.sql
2. SQL_run_API/postgre/enterprise_db/constraint.sql
3. SQL_run_API/postgre/enterprise_db/enterprise_seed_data.sql
4. SQL_run_API/postgre/enterprise_db/03_create_readonly_role.sql
5. SQL_run_API/postgre/enterprise_db/validate_enterprisedb_br01_br16.sql
```

Truoc khi chay `03_create_readonly_role.sql`, doi mat khau placeholder trong file. Tai khoan nay dung cho ket noi doc dataset.

### Buoc 3: Tao SQLArena database

Ket noi Query Tool vao `sqlarena_db`, chay:

```text
1. SQL_run_API/postgre/sqlarena_db/01_create_sqlarena_core.sql
2. SQL_run_API/postgre/sqlarena_db/02_insert_sqlarena_core_data.sql
3. SQL_run_API/postgre/app_db/01_create_app_tables.sql
```

Buoc 1 tao cot `expected_result`. Buoc 2 tao 50 cau hoi. Buoc 3 tao cac bang cho API va tao user/bo de test.

### Buoc 4: Sinh expected result cho submit

File can chay:

```text
SQL_run_API/postgre/app_db/populate_expected_results.py
```

Script doc `reference_sql` trong `core.source_questions`, chay tung reference SQL tren `enterprise_db` bang ket noi doc, sau do ghi JSON ket qua vao:

```text
sqlarena_db.core.source_questions.expected_result
```

Chay tu thu muc goc repository:

```powershell
python SQL_run_API/postgre/app_db/populate_expected_results.py --dry-run
python SQL_run_API/postgre/app_db/populate_expected_results.py
```

`--dry-run` chi kiem tra, khong ghi database. Lenh khong co `--dry-run` moi cap nhat expected.

Kiem tra sau khi chay:

```sql
SELECT COUNT(*) AS total_questions,
       COUNT(expected_result) AS expected_filled
FROM core.source_questions;
```

Ket qua mong doi:

```text
total_questions = 50
expected_filled = 50
```

### Buoc 5: Kiem tra file cau hinh

Neu da lam phan `Tao .env` o tren thi khong can tao them file nao. Backend khong can ket noi den Ollama de chay SQL API.

## 5. Kich ban B: Da co database tu pipeline AI

Neu da co `enterprise_db` va `sqlarena_db` theo huong dan AI truoc day, khong chay lai cac file import du lieu core hoac Enterprise tren database dang co du lieu.

Lam cac buoc sau:

1. Kiem tra `enterprise_db` da co 16 bang dataset.
2. Kiem tra `sqlarena_db.core.source_questions` da co 50 cau.
3. Kiem tra cot `expected_result`:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'core'
  AND table_name = 'source_questions'
  AND column_name = 'expected_result';
```

4. Neu chua co cot, chay lai phan `ALTER TABLE` trong `SQL_run_API/postgre/sqlarena_db/01_create_sqlarena_core.sql`.
5. Neu co cot nhung chua co du lieu, chay:

```powershell
python SQL_run_API/postgre/app_db/populate_expected_results.py --dry-run
python SQL_run_API/postgre/app_db/populate_expected_results.py
```

6. Chay `SQL_run_API/postgre/app_db/01_create_app_tables.sql` tren `sqlarena_db` de tao bo bang `app`.

Day la phan them cho SQL API. Khong can chay lai pipeline AI neu chi muon chay thu, submit va BXH.

## 6. Chuc nang cua cac bang app

### `app.users`

Luu tai khoan va user test. Cac cot chinh:

```text
user_id, username, email, password_hash,
display_name, role, status, created_at
```

Chuc nang dang ky/dang nhap sau nay se ghi va doc tai khoan tu bang nay. Cot `role` dung cho role ung dung, vi du `learner` va `admin`; no khac voi PostgreSQL role. Cot `password_hash` da co san de module authentication su dung theo cach ma nguoi lam dang nhap chon. Ba user seed chi la user test local.

Phan SQL API hien tai nhan `user_id` de test. Khi ghep module dang nhap, module authentication tra ve `user_id` cua tai khoan da dang nhap, sau do dung id do cho progress, submit va BXH. Khong can doi cau truc cac bang submission.

### `app.submissions`

Moi lan bam `Nop bai` tao mot dong. Mot user co the co nhieu submission cho cung mot cau. `user_id` lien ket `app.users`; `question_id` lien ket `core.source_questions`.

### `app.weekly_sets` va `app.weekly_set_questions`

Luu bo de tuan dang phat hanh va danh sach cau trong bo. Danh sach learner hien tai doc bo de tuan qua API, khong doc toan bo 50 cau.

### `core.source_questions.expected_result`

Day la JSON ket qua chuan dung de cham submit. Khong nham voi `draft.test_cases` cua pipeline review.

## 7. Chay backend

Tu thu muc goc repository:

```powershell
python -m uvicorn backend.app:app --app-dir SQL_run_API --host 127.0.0.1 --port 8000
```

Mo Swagger:

```text
http://127.0.0.1:8000/docs
```

Kiem tra nhanh:

```text
GET /health
GET /api/users
GET /api/weekly-sets/current?user_id=1
GET /api/leaderboard/weekly
GET /api/leaderboard/monthly
```

### Danh sach API hien co

```text
GET  /health
     Kiem tra backend dang chay va ket noi duoc sqlarena_db.

GET  /api/users
     Lay danh sach user test trong app.users.

GET  /api/questions
     Lay danh sach cau hoi trong core.source_questions.

GET  /api/questions/{question_id}
     Lay chi tiet mot cau hoi va schema cac bang duoc su dung.

GET  /api/weekly-sets/current?user_id=1
     Lay bo de tuan dang published, kem trang thai cua user.

GET  /api/progress?user_id=1
     Lay trang thai tung cau cua user: not_started, attempted, passed.

GET  /api/progress/skills?user_id=1
     Tong hop tien do theo ky nang trong bo de tuan hien tai.

GET  /api/leaderboard/weekly
     Xep hang theo so cau passed trong bo de tuan dang phat hanh.

GET  /api/leaderboard/monthly?year=2026&month=10
     Xep hang theo cac cau passed trong cac bo de cua thang.

POST /api/run
     Chay thu mot cau SELECT/WITH, tra ket qua nhung khong luu submission.

POST /api/submissions
     Chay, so sanh voi expected_result va luu lich su nop bai.
```

Tat ca API chay SQL hien tai chi chap nhan `SELECT` va `WITH`. Cac lenh `INSERT`, `UPDATE`, `DELETE` bi tu choi.

Chay thu va nop bai dung user test:

```powershell
curl -X POST http://127.0.0.1:8000/api/run `
  -H "Content-Type: application/json" `
  -d '{"question_id":"ENT-002","user_id":1,"sql":"SELECT DISTINCT city FROM customer_addresses ORDER BY city"}'
```

`/api/run` chi chay thu va khong tao submission.

```powershell
curl -X POST http://127.0.0.1:8000/api/submissions `
  -H "Content-Type: application/json" `
  -d '{"question_id":"ENT-002","user_id":1,"sql":"SELECT DISTINCT city FROM customer_addresses ORDER BY city"}'
```

`/api/submissions` chay, so sanh voi `expected_result` va luu lich su.

## 8. Chay frontend

Mo PowerShell thu hai, tu thu muc goc repository:

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory SQL_run_API
```

Mo:

```text
http://127.0.0.1:5500/learner.html
```

Frontend hien tai co dropdown chon 3 user test. Dropdown chi de test local. Khi co login that, frontend se bo dropdown va gui session/token.

## 9. Tich hop dang nhap va tao bo de sau nay

### Dang ky/dang nhap

Module authentication se dung bang:

```text
sqlarena_db.app.users
```

Role PostgreSQL `sqlarena_ai_ro` khong phai tai khoan nguoi hoc. Role nay chi co quyen ket noi va `SELECT` tren `enterprise_db`, dung de API chay truy van doc. Khong dung role nay de dang nhap vao giao dien; tai khoan giao dien nam trong `app.users`.

Sau khi dang nhap, backend can lay `current_user.user_id` tu session/token thay vi tin `user_id` tu JSON body. Logic chay SQL, cham submit, luu submission va BXH giu nguyen.

### Tao bo de

Chuc nang admin tao bo de se ghi:

```text
app.weekly_sets
app.weekly_set_questions
```

Moi dong trong `weekly_set_questions` phai tham chieu mot `core.source_questions.question_id`. Chi cau hoi da co expected result hop le moi nen dua vao bo de chinh thuc.

## 10. Kiem tra sau khi cai dat

```sql
SELECT COUNT(*) FROM core.source_questions;
SELECT COUNT(*) FROM core.source_questions WHERE expected_result IS NOT NULL;
SELECT COUNT(*) FROM app.users;
SELECT COUNT(*) FROM app.weekly_sets;
SELECT COUNT(*) FROM app.weekly_set_questions;
```

Gia tri test hien tai can co:

```text
source_questions: 50
expected_result: 50
users: 3
weekly_set_questions: 10
```

Khi test:

- User 1 da co mot so submission mau.
- `/api/run` khong luu submission.
- `/api/submissions` moi luu submission.
- SQL `UPDATE`, `INSERT`, `DELETE` bi tu choi.
- BXH tuan va thang chi tinh cac submission passed theo bo de/thoi gian.

## 11. Loi thuong gap

### `password authentication failed`

Kiem tra lai user/password trong file cau hinh dang dung. `ARENA_DB_*` tro vao `sqlarena_db`; `ENTERPRISE_DB_*` tro vao `enterprise_db`. Neu role `sqlarena_ai_ro` chua ton tai, chay `SQL_run_API/postgre/enterprise_db/03_create_readonly_role.sql` bang tai khoan PostgreSQL quan tri.

### `No active weekly set found`

Kiem tra `app.weekly_sets.starts_at`, `ends_at` va `status = 'published'`.

### `expected_result` dang NULL

Chay script `populate_expected_results.py --dry-run` truoc, sau do chay lai khong co `--dry-run`.

### `ModuleNotFoundError: db_readonly`

Phai co file:

```text
SQL_run_API/postgre/app_db/db_readonly.py
```

File nay di kem script populate expected.
