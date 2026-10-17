# SQLArena AI

SQLArena AI là pipeline Python dùng LLM để **sinh câu hỏi SQL (Model A)** và **kiểm duyệt câu hỏi bằng cách giải độc lập, đối chiếu kết quả và tạo test cases (Model B)**. Dữ liệu nghiệp vụ và metadata được lưu trong PostgreSQL.

> Hướng dẫn này dành cho người clone repo mới trên Windows + PowerShell + pgAdmin 4. Nếu bạn đã có database chứa dữ liệu, hãy đọc phần an toàn dữ liệu trước khi chạy SQL.

## 1. Kiến trúc nhanh

Gói source dùng để chia sẻ không nên chứa `.git/`, `ai/.env`, `ai/outputs/`, `.venv/` hoặc `__pycache__/`. Các file output và cấu hình cá nhân được tạo lại trên máy chạy; không cần để người khác cài dự án.

- `enterprise_db`: dataset nghiệp vụ PostgreSQL để làm ngữ cảnh cho câu hỏi; pipeline kết nối đọc.
- `sqlarena_db`: dữ liệu lõi trong schema `core`, draft và trạng thái kiểm duyệt trong schema `draft`.
- `ai/main.py`: Model A tạo đề và kiểm tra sơ bộ.
- `ai/review.py`: Model B giải đề nhiều lần, so sánh kết quả và ghi kết quả kiểm duyệt/test cases.
- `ai/validator.py`, `ai/context_policy.py`: kiểm tra SQL, kỹ năng và giới hạn ngữ cảnh.
- `postgre/`: SQL schema, constraints, dữ liệu nguồn và kiểm tra.
- `build/enterprise_seed_data.sql`: dữ liệu Enterprise đã xuất sẵn; không cần chạy lại script sinh dữ liệu.
- `question_create/`, `question_generation/`: quy tắc và bộ 50 câu nguồn.
- Tài liệu quy trình chi tiết: [`ai/review_pipeline.md`](ai/review_pipeline.md), [`ai/question_only_pipeline.md`](ai/question_only_pipeline.md), [`postgre/sqlarena_db/sqlarena_database_guide.md`](postgre/sqlarena_db/sqlarena_database_guide.md).

## 2. Yêu cầu

- Windows 10/11 64-bit (hướng dẫn dưới đây dùng PowerShell).
- PostgreSQL và pgAdmin 4; PostgreSQL server phải đang chạy, mặc định cổng `5432`.
- Python **3.11–3.13 khuyến nghị**. Dùng phiên bản Python được các dependency hỗ trợ; nếu gặp lỗi build package, không nên mặc định dùng bản Python mới nhất.
- Ollama cho Windows, có thể truy cập tại `http://localhost:11434`.
- Mặc định trong `.env.example`: Model A `llama3`, Model B `qwen2.5-coder:7b`, semantic auditor `llama3:latest`. Tên tag thực tế phải khớp `ollama list`.
- Model cần RAM/VRAM tùy kích thước, quantization, context và các ứng dụng đang chạy. Với RAM 16 GB/GTX 1650 4 GB, ưu tiên chạy tuần tự và thử từng model trước khi đổi cấu hình cả pipeline.

## 3. Clone và tạo môi trường Python

Mở PowerShell tại nơi muốn lưu source:

```powershell
git clone --branch Hung --single-branch https://github.com/Hungnn1904/sqlarena-ai.git
cd sqlarena-ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu `py -3.12` không tồn tại, cài Python 3.12 rồi thử lại. Nếu PowerShell chặn kích hoạt môi trường, có thể dùng trực tiếp `\.venv\Scripts\python.exe -m pip install -r requirements.txt` và `\.venv\Scripts\python.exe ai\main.py --check`.

## 4. Cài PostgreSQL database (cài mới)

Tạo **hai database trống** trong pgAdmin: `enterprise_db` và `sqlarena_db`. Không chạy các file khởi tạo trên database có dữ liệu quan trọng.

### 4.1 `enterprise_db`

Mở Query Tool kết nối đúng database `enterprise_db`; chạy toàn bộ từng file theo thứ tự:

1. `postgre/enterprise_db/schema_code.sql`
2. `postgre/enterprise_db/constraint.sql`
3. `build/enterprise_seed_data.sql`
4. `postgre/enterprise_db/03_create_readonly_role.sql` (khuyến nghị; thay placeholder password trước khi chạy)
5. `postgre/enterprise_db/validate_enterprisedb_br01_br16.sql`
6. `validate_scenario_coverage.sql`

Sau mỗi file, đọc cả tab Messages và kết quả truy vấn. Dừng nếu có lỗi. Kiểm tra Business Rules BR01–BR16 đều `PASS`, `overall_status = PASS`, `total_violations = 0`; scenario coverage không có dòng `FAIL`.

### 4.2 `sqlarena_db`

Mở Query Tool kết nối `sqlarena_db`; chạy toàn bộ theo thứ tự:

1. `postgre/sqlarena_db/01_create_sqlarena_core.sql`
2. `postgre/sqlarena_db/02_insert_sqlarena_core_data.sql`
3. `postgre/sqlarena_db/03_create_review_pipeline.sql` (cần cho Model B; chạy sau hai file đầu)

Kết quả kiểm tra cuối file dữ liệu cần là `worlds=1`, `skills=6`, `templates=0`, `source_questions=50`.

**Không chạy lại bước import dữ liệu** trên database đã được nạp. Các script được thiết kế để phát hiện một số trường hợp sai cấu trúc/dữ liệu và có thể dừng thay vì ghi đè; đừng xem đó là script reset.

## 5. Cấu hình `.env`

Tạo file cấu hình cục bộ nếu chưa có:

```powershell
Copy-Item ai\.env.example ai\.env
```

Mở `ai/.env` và sửa các trường sau cho khớp máy của bạn:

- `ARENA_DB_*`: kết nối `sqlarena_db`.
- `CATALOG_DB_*`: kết nối đọc `enterprise_db`; nên dùng role `sqlarena_ai_ro`.
- `OLLAMA_HOST`: mặc định `http://localhost:11434`.
- `MODEL_NAME`: model sinh đề, mặc định `llama3`.
- `REVIEW_MODEL_NAME`: model kiểm duyệt, mặc định `qwen2.5-coder:7b`.

Điền password vào `ARENA_DB_PASSWORD`, `CATALOG_DB_PASSWORD` và `ENTERPRISE_DB_PASSWORD` nếu tài khoản yêu cầu. Nếu đã chạy `03_create_readonly_role.sql`, đặt `CATALOG_DB_USER` và `ENTERPRISE_DB_USER` là `sqlarena_ai_ro`; chỉ `ARENA_DB_USER` cần quyền ghi vào `sqlarena_db`. Không commit, gửi hoặc đăng `ai/.env`. File `.env.example` chỉ là mẫu; nó không chứa thông tin xác thực. Không dùng tài khoản superuser trong môi trường dùng chung/production.

## 6. Cài và kiểm tra Ollama / đổi model

Cài Ollama từ [trang chính thức](https://ollama.com/download/windows). Mặc định của dự án có thể tải bằng:

```powershell
ollama pull llama3
ollama pull qwen2.5-coder:7b
ollama pull llama3:latest
ollama list
ollama run llama3 "Return JSON only: {\"ok\":true}"
```

Một số tag có thể cùng trỏ tới một model đã tải; `ollama list` là nguồn xác nhận tên model local. Không cần tải `llama3:latest` lần nữa nếu Ollama đã báo tag này tồn tại.

Để thử model khác, tải tag được Ollama hỗ trợ rồi sửa `ai/.env` (không sửa `.env.example` để lưu cấu hình máy cá nhân):

```dotenv
MODEL_NAME=<tag-model-a-da-pull>
REVIEW_MODEL_NAME=<tag-model-b-da-pull>
REVIEW_AUDIT_MODEL_NAME=<tag-semantic-auditor-da-pull>
```

Thay dấu ngoặc nhọn bằng tên tag thật, không giữ nguyên placeholder. `REVIEW_MODEL_NAME` và `REVIEW_AUDIT_MODEL_NAME` là hai vai trò riêng; kiểm tra cả hai. Nên thử từng model trên cùng một bộ câu, giữ lại kết quả JSON để so sánh trước/sau. Model lớn hơn không bảo đảm chính xác hơn, và có thể chạy rất chậm hoặc hết RAM trên máy ít bộ nhớ.

**Cảnh báo chất lượng hiện tại:** calibration 20 câu ngày 2026-10-17 ghi nhận `approved_WRONG = 1` (ENT-017). Đây là lỗi duyệt nhầm nghiêm trọng; chưa nên coi pipeline Model B đủ an toàn để duyệt hàng loạt chỉ vì đổi model. Xem [ai/review_pipeline.md](ai/review_pipeline.md) và [ai/test_report.md](ai/test_report.md).

## 7. Kiểm tra và chạy pipeline

Chạy lệnh từ **thư mục gốc repository** (thư mục chứa `ai`, `postgre`, `build`):

```powershell
python ai/main.py --check
```

Lệnh này kiểm tra cấu hình, Rules/Core/Draft và Ollama; không sinh hay ghi đề. Chỉ tiếp tục nếu kiểm tra thành công.

Sinh thử, không lưu draft:

```powershell
python ai/main.py --dry-run
```

Sinh đề và lưu các đề qua kiểm tra sơ bộ vào `draft.question_drafts`:

```powershell
python ai/main.py
```

Chương trình sẽ hỏi số lượng, độ khó, kỹ năng, chủ đề và tùy chọn bổ sung. Đề được lưu có trạng thái `pending`; **pending không có nghĩa là đã được duyệt**. Kết quả mỗi lượt cũng được xuất JSON trong `ai/outputs/` (thư mục này không được commit).

Kiểm tra Model B trước khi review:

```powershell
python ai/review.py --check
```

Review một draft cụ thể:

```powershell
python ai/review.py --draft-id 123
```

Thay `123` bằng `draft_id` thật. Để xem các tuỳ chọn, chạy `python ai/review.py --help`. Đọc [`ai/review_pipeline.md`](ai/review_pipeline.md) trước khi chạy review hàng loạt; bước này có thể cập nhật trạng thái draft và ghi log/test cases vào database.

## 8. Kiểm thử theo từng tầng

Chạy từ thư mục gốc repository. Trước hết kiểm tra cú pháp và dependency:

```powershell
python --version
python -m pip check
python -m py_compile ai/main.py ai/review.py ai/validator.py ai/context_policy.py
```

Chạy test offline/unit:

```powershell
python -m unittest discover -s ai -p "test_*.py" -v
```

Nếu đang điều tra riêng một pipeline:

```powershell
python -m unittest discover -s ai -p "test_question_only.py" -v
python -m unittest discover -s ai -p "test_review.py" -v
```

Sau đó kiểm tra dịch vụ thật:

```powershell
python ai/main.py --check
python ai/review.py --check
```

Cuối cùng mới chạy `python ai/main.py --dry-run` để kiểm tra sinh đề mà không ghi draft, rồi chạy một câu thật nếu kết quả đã được xem xét. Calibration Model B dùng `python ai/review.py --calibrate --skip 15 --limit 20 --samples 3`; lệnh này đọc bộ câu nguồn có đáp án, xuất JSON vào `ai/outputs/` và không ghi database. Xem mục calibration trong tài liệu Model B trước khi chạy.

Test pass chỉ chứng minh các trường hợp được test đã qua; không chứng minh LLM luôn sinh đúng, semantic auditor không bao giờ sai, hoặc database mới đã được khởi tạo chính xác.

## 9. Dữ liệu và an toàn

- Không chạy SQL setup/import trên database đang chứa dữ liệu quan trọng.
- Không commit mật khẩu, token, dump cá nhân hoặc file `.env`.
- Không đưa tài khoản superuser cho pipeline nếu có thể tạo user giới hạn quyền.
- Model AI có thể sinh SQL sai hoặc câu hỏi mơ hồ. Model A validator chỉ là kiểm tra sơ bộ; kết quả Model B vẫn cần xem xét theo quy trình review.
- Các file `ai/outputs/`, `__pycache__/`, `.venv/` là dữ liệu local/cache, không phải source cần clone.
- Thư mục `.git` không cần đóng gói khi gửi source dạng ZIP.

## 10. Lỗi thường gặp

| Triệu chứng | Kiểm tra / cách xử lý |
|---|---|
| `connection refused` PostgreSQL | Kiểm tra service PostgreSQL đang chạy, `*_DB_HOST`, `*_DB_PORT`, firewall và database name. |
| `password authentication failed` | Kiểm tra user/password trong `ai/.env`; không sửa bằng cách commit password. |
| Thiếu bảng/schema hoặc số câu nguồn không đúng | Xác nhận đã chạy đúng SQL trên đúng database theo đúng thứ tự; kiểm tra database đích trước khi chạy lại. |
| `Ollama` không kết nối được | Mở Ollama, kiểm tra `http://localhost:11434`, `ollama list`; không nhầm tên model với model đã tải. |
| Sinh đề `0/N`, lỗi `topic_relations` | Model A khai báo JOIN không khớp FK thật. Đọc JSON mới nhất trong `ai/outputs/`, kiểm tra `checks.topic_relations`; không nới lỏng validator để cho đề lọt qua. |
| Lỗi `business_dependencies` | Nội dung câu hỏi dùng điều kiện nghiệp vụ nhưng thiếu cột trong `required_columns`/`tables_used`. Kiểm tra câu hỏi và metadata trong JSON; nếu retry vẫn lặp, dừng và sửa prompt/logic thay vì tăng số lần retry vô hạn. |
| Calibration có `approved_WRONG` | Đây là release blocker cho duyệt tự động. Mở JSON calibration, đối chiếu SQL mẫu với `reference_sql`, sửa hard guard/auditor rồi chạy lại cùng tập và tập holdout. Không coi số mẫu đúng là bằng chứng đủ để bỏ qua lỗi này. |
| Không đủ RAM hoặc model chạy rất chậm | Thử model nhỏ hơn và giảm context; cấu hình model phải tồn tại trong Ollama. |
| `Rules` không tìm thấy | Chạy lệnh ở thư mục gốc repository; kiểm tra `RULES_PATH` trong `ai/.env`. |
| Sinh được JSON nhưng không có draft lưu | Dùng `--dry-run` sẽ không ghi DB; nếu không dùng dry-run, xem `saved_count`, lỗi kết nối và bảng `draft.question_drafts`. |
| Draft vẫn `pending` | Đây là trạng thái chờ review, chưa phải lỗi tự động; chạy quy trình Model B sau khi `python ai/review.py --check` thành công. |

## 11. Tài liệu tham khảo

- [PostgreSQL Downloads](https://www.postgresql.org/download/)
- [pgAdmin](https://www.pgadmin.org/download/)
- [Python](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download/windows)
- [Hướng dẫn database SQLArena](postgre/sqlarena_db/sqlarena_database_guide.md)
- [Quy trình Model B](ai/review_pipeline.md)
- [Ghi chú pipeline AI](ai/pipeline_ai_notes.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
