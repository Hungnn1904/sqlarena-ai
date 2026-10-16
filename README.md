# SQLArena AI

Pipeline Python dùng LLM chạy cục bộ (Ollama) để **tự động sinh và kiểm duyệt câu hỏi SQL** trên một cơ sở dữ liệu doanh nghiệp mô phỏng (PostgreSQL).

- **Model A** (`ai/main.py`): sinh câu hỏi SQL + metadata (không sinh đáp án), kiểm tra sơ bộ rồi lưu vào bảng draft.
- **Model B** (`ai/review.py`): giải độc lập từng câu nhiều lần, chạy trên DB bằng role chỉ đọc, đối chiếu kết quả, chạy semantic audit và tạo test case. Thiếu bằng chứng thì không bao giờ tự duyệt (`fail-closed`).

```
Core (50 câu nguồn) ──► Model A ──► draft.question_drafts (pending)
                                          │
                       enterprise_db ◄──► Model B ──► approved / needs_human / rejected + test case
```

## Mục lục

1. [Cấu trúc repo](#1-cấu-trúc-repo)
2. [Yêu cầu](#2-yêu-cầu)
3. [Cài đặt nhanh (Quick start)](#3-cài-đặt-nhanh)
4. [Cài đặt database](#4-cài-đặt-database)
5. [Cấu hình `ai/.env`](#5-cấu-hình-aienv)
6. [Cài model Ollama](#6-cài-model-ollama)
7. [Sử dụng](#7-sử-dụng)
8. [Kiểm thử](#8-kiểm-thử)
9. [Lưu ý an toàn](#9-lưu-ý-an-toàn)
10. [Tài liệu chi tiết](#10-tài-liệu-chi-tiết)

## 1. Cấu trúc repo

| Thư mục / file | Nội dung |
|---|---|
| `ai/` | Code pipeline: `main.py` (Model A), `review.py` (Model B), `validator.py`, `context_policy.py`, các file `test_*.py`, `.env.example` |
| `postgre/enterprise_db/` | SQL tạo schema, ràng buộc, role chỉ đọc và script kiểm tra BR01–BR16 cho `enterprise_db` |
| `postgre/sqlarena_db/` | SQL tạo schema `core` / `draft` và nạp 50 câu nguồn cho `sqlarena_db` |
| `build/` | Dữ liệu seed đã sinh sẵn: `enterprise_seed_data.sql` (không cần sinh lại) |
| `validate_scenario_coverage.sql` | Kiểm tra dataset đủ các tình huống thiết kế |
| `question_create/`, `question_generation/` | Bộ quy tắc và 50 câu nguồn (JSON) + công cụ tạo/kiểm chứng. **Không cần chạy khi setup** |
| `sqlarena_create/`, `seed_create/` | Công cụ/prompt đã dùng để dựng Core và seed. **Không cần chạy khi setup** |
| `docs/` | Tài liệu chi tiết (xem [mục 10](#10-tài-liệu-chi-tiết)) |

## 2. Yêu cầu

- **PostgreSQL** (dự án được kiểm chứng trên PostgreSQL 18.3; các bản khác chưa được kiểm chứng) và pgAdmin 4 *hoặc* `psql`; server chạy ở cổng `5432`.
- **Python 3.11–3.13**. Nếu `pip install` lỗi build, đừng dùng bản Python mới nhất ngay khi ra mắt.
- **Ollama** chạy tại `http://localhost:11434`.
- Hệ điều hành: Windows 10/11, macOS hoặc Linux (lệnh bên dưới có đủ cả hai kiểu).
- Cấu hình máy: Model B mặc định `qwen2.5-coder:7b` cần khoảng 8 GB RAM/VRAM trở lên. Máy yếu hãy chọn model nhỏ hơn trong `.env` (chất lượng review có thể giảm).

## 3. Cài đặt nhanh

```bash
git clone https://github.com/<your-username>/sqlarena-ai.git
cd sqlarena-ai
```

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item ai\.env.example ai\.env
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp ai/.env.example ai/.env
```

> PowerShell chặn kích hoạt venv? Gọi trực tiếp `.\.venv\Scripts\python.exe` thay cho `python`.

Sau đó làm tiếp [mục 4](#4-cài-đặt-database) → [5](#5-cấu-hình-aienv) → [6](#6-cài-model-ollama) → [7](#7-sử-dụng).

## 4. Cài đặt database

Tạo **hai database trống**: `enterprise_db` và `sqlarena_db`.

```sql
-- kết nối database "postgres", chạy từng lệnh một (bật auto-commit)
CREATE DATABASE enterprise_db;
CREATE DATABASE sqlarena_db;
```

Chạy các file theo **đúng thứ tự**, mỗi file trên **đúng database** ghi bên dưới. Dùng pgAdmin Query Tool (mở file → Execute) hoặc `psql`:

```bash
psql -U postgres -d enterprise_db -f postgre/enterprise_db/schema_code.sql
```

Sau mỗi file hãy đọc tab Messages; dừng lại nếu có lỗi.

### 4.1 `enterprise_db`

| # | File | Ghi chú |
|---|---|---|
| 1 | `postgre/enterprise_db/schema_code.sql` | Tạo 16 bảng (đã gồm các bước migration ở cuối file) |
| 2 | `postgre/enterprise_db/constraint.sql` | Ràng buộc nghiệp vụ bổ sung |
| 3 | `build/enterprise_seed_data.sql` | Dữ liệu mẫu (~1 MB) |
| 4 | `postgre/enterprise_db/03_create_readonly_role.sql` | Tạo role `sqlarena_ai_ro`. **Đổi `DOI_MAT_KHAU_NAY` thành mật khẩu của bạn trước khi chạy.** Dòng kiểm tra cuối phải ra `false / false / true` |
| 5 | `postgre/enterprise_db/validate_enterprisedb_br01_br16.sql` | Kỳ vọng `overall_status = PASS`, `total_violations = 0` |
| 6 | `validate_scenario_coverage.sql` | Kỳ vọng không có dòng `FAIL` |

### 4.2 `sqlarena_db`

| # | File | Ghi chú |
|---|---|---|
| 1 | `postgre/sqlarena_db/01_create_sqlarena_core.sql` | Tạo schema `core` và `draft` |
| 2 | `postgre/sqlarena_db/02_insert_sqlarena_core_data.sql` | Kết quả cuối: `worlds=1, skills=6, templates=0, source_questions=50` |
| 3 | `postgre/sqlarena_db/03_create_review_pipeline.sql` | Bảng `draft.test_cases`… (cần cho Model B) |

> **Đây không phải script reset.** File 02 từ chối chạy nếu Core đã có dữ liệu. Không chạy trên database đang chứa dữ liệu quan trọng. Nếu một lần chạy lỗi giữa chừng và Query Tool báo transaction lỗi, chạy `ROLLBACK;`.

## 5. Cấu hình `ai/.env`

Mở `ai/.env` (đã tạo ở mục 3) và điền:

| Nhóm biến | Ý nghĩa |
|---|---|
| `ARENA_DB_*` | Kết nối `sqlarena_db`. Đây là kết nối duy nhất cần quyền ghi |
| `CATALOG_DB_*` | Kết nối **đọc** `enterprise_db` để lấy catalog/schema |
| `ENTERPRISE_DB_USER` / `_PASSWORD` | Role chỉ đọc dùng để chạy SQL do model sinh: `sqlarena_ai_ro` + mật khẩu đã đặt ở bước 4.1-4 |
| `OLLAMA_HOST` | Mặc định `http://localhost:11434` |
| `MODEL_NAME` | Model A (sinh đề), mặc định `llama3` |
| `REVIEW_MODEL_NAME` | Model B (kiểm duyệt), mặc định `qwen2.5-coder:7b`. **Nên khác họ với Model A** |

Các biến còn lại (`REVIEW_*`, timeout, ngưỡng trùng lặp…) có giá trị mặc định hợp lý và được giải thích trong `.env.example`.

Pipeline **từ chối** chạy SQL của model bằng superuser; vì vậy bắt buộc dùng `sqlarena_ai_ro` cho `ENTERPRISE_DB_*` khi chạy Model B.

## 6. Cài model Ollama

Cài Ollama từ <https://ollama.com/download>, rồi:

```bash
ollama pull llama3
ollama pull qwen2.5-coder:7b
ollama list
```

Giữ Ollama chạy nền khi dùng pipeline. Nếu đổi model, sửa tên tương ứng trong `ai/.env`.

## 7. Sử dụng

Chạy mọi lệnh từ **thư mục gốc repo**.

### Bước 1 — Kiểm tra môi trường

```bash
python ai/main.py --check       # Rules, Core, Draft, Ollama (không sinh, không ghi)
python ai/review.py --check     # migration, Model B, role chỉ đọc
```

Chỉ tiếp tục khi cả hai báo thành công.

### Bước 2 — Sinh câu hỏi bằng Model A

```bash
python ai/main.py --dry-run     # sinh thử, chỉ xuất JSON, KHÔNG ghi DB
python ai/main.py               # sinh và lưu draft đạt kiểm tra sơ bộ (status = pending)
```

Chương trình hỏi số lượng, độ khó, kỹ năng (S1–S6), chủ đề nghiệp vụ và yêu cầu bổ sung. Draft `pending` **chưa phải đã được duyệt**. Mỗi lượt chạy được xuất JSON ở `ai/outputs/` (thư mục này không được commit).

### Bước 3 — Kiểm duyệt bằng Model B

```bash
python ai/review.py --calibrate --limit 15 --samples 3   # đo độ tin cậy trên câu nguồn có đáp án (chạy trước)
python ai/review.py --dry-run --limit 3                  # review thử, không ghi DB
python ai/review.py --draft-id 7                         # review một draft
python ai/review.py                                      # review mọi draft pending (hỏi xác nhận)
python ai/review.py --show 7                             # xem log, lời giải, test case của draft 7
python ai/review.py --reset-stuck                        # trả draft kẹt "reviewing" về "pending"
```

Kết quả: `approved` (kèm reference SQL + test case trong `draft.test_cases`), `needs_human` hoặc `rejected`. Xem [docs/model_b_review.md](docs/model_b_review.md) trước khi review hàng loạt: bước này ghi vào database.

## 8. Kiểm thử

```bash
python -m unittest discover -s ai -p "test_*.py"
```

| File test | Cần DB/Ollama? |
|---|---|
| `test_review.py`, `test_pipeline_v2.py`, `test_question_only.py` | Không |
| `test_model_a.py` | Phần lớn chạy offline; 2 test tích hợp (`test_real_core_...`, `test_superuser_...`) cần `sqlarena_db` đã cài |
| `test_domain_groups.py` | Cần `sqlarena_db` đã cài và `ai/.env` đúng |

Trên máy chưa cài DB, các test cần DB sẽ báo `connection refused`: đó là bình thường. Test pass không thay thế việc kiểm tra dữ liệu thực.

## 9. Lưu ý an toàn

- **Không commit `ai/.env`** (đã nằm trong `.gitignore`). Kiểm tra bằng `git status` trước khi push.
- Không chạy SQL setup/import trên database đang có dữ liệu quan trọng.
- Dùng role giới hạn quyền cho pipeline, không dùng superuser ở môi trường dùng chung.
- LLM có thể sinh SQL/câu hỏi sai hoặc mơ hồ. Kiểm tra của Model A chỉ là sơ bộ; kết quả Model B (kể cả semantic audit) vẫn cần con người xem xét, đặc biệt các draft `needs_human`.
- Dữ liệu Enterprise là **dữ liệu mô phỏng**, không chứa thông tin cá nhân thật.

## 10. Tài liệu chi tiết

| Tài liệu | Nội dung |
|---|---|
| [docs/model_a_pipeline.md](docs/model_a_pipeline.md) | Cách Model A sinh đề, validator, lưu trữ, giới hạn |
| [docs/model_b_review.md](docs/model_b_review.md) | Pipeline kiểm duyệt, cấu hình, calibrate, trạng thái |
| [docs/enterprise_db.md](docs/enterprise_db.md) | Schema 16 bảng của `enterprise_db` |
| [docs/business_rules.md](docs/business_rules.md) | Business Rules BR01–BR16 |
| [docs/enterprise_db_validation_report.md](docs/enterprise_db_validation_report.md) | Kết quả kiểm tra dataset seed |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Chẩn đoán và xử lý lỗi thường gặp |
| [postgre/sqlarena_db/sqlarena_database_guide.md](postgre/sqlarena_db/sqlarena_database_guide.md) | Cấu trúc và truy vấn kiểm tra `sqlarena_db` |
| [question_create/enterprise_50_question_rules_v1.md](question_create/enterprise_50_question_rules_v1.md) | Quy tắc bộ 50 câu nguồn |