# Pipeline kiểm duyệt (Model B) — hướng dẫn cài và chạy

`ai/review.py` lấy các draft `pending` do Model A sinh, cho **Model B giải k lần**, chạy từng lời giải trên
`enterprise_db` bằng role chỉ đọc, so kết quả, rồi chốt `approved` / `needs_human` / `rejected`.
Draft `approved` có sẵn **reference SQL + test case** (kết quả mong đợi) trong `draft.test_cases`.

`main.py` (Model A) **không bị sửa**. Các draft cũ đang `pending` dùng được ngay.

## 1. Cài đặt (làm đúng thứ tự, một lần)

**Bước 1 — Chép file vào dự án** (giữ đúng đường dẫn, ghi đè `.env.example` và `README.md` nếu hỏi):

| File | Việc |
|---|---|
| `ai/review.py` | pipeline kiểm duyệt |
| `ai/test_review.py` | unit test (không cần DB/Ollama) |
| `postgre/sqlarena_db/03_create_review_pipeline.sql` | migration cho `sqlarena_db` |
| `postgre/enterprise_db/03_create_readonly_role.sql` | tạo role chỉ đọc cho `enterprise_db` |

**Bước 2 — Migration (pgAdmin hoặc psql, kết nối `sqlarena_db`):** chạy `03_create_review_pipeline.sql`.
Chạy lại nhiều lần vẫn an toàn. File chỉ thêm bảng `draft.test_cases`, thêm cột cho `draft.self_solve_runs`
và nới ràng buộc `draft.review_logs.stage`; không động vào `core.*` hay `draft.question_drafts`.

**Bước 3 — Role chỉ đọc (kết nối `enterprise_db` bằng `postgres`):**
1. Mở `03_create_readonly_role.sql`, đổi `DOI_MAT_KHAU_NAY` thành mật khẩu của bạn.
2. Chạy file. Dòng kiểm tra cuối phải ra `f | f | t`.

Lý do: code từ chối chạy SQL do model sinh bằng `postgres` (superuser). Role mới chỉ có `SELECT`,
không có `CREATE`/`TEMP`.

**Bước 4 — Sửa `ai/.env`:**
```
ENTERPRISE_DB_USER=sqlarena_ai_ro
ENTERPRISE_DB_PASSWORD=<mật khẩu ở bước 3>
REVIEW_MODEL_NAME=<model B, xem bước 5>
```
Các khóa `REVIEW_*` khác có trong `.env.example` (đều có giá trị mặc định; không bắt buộc chép hết).

**Bước 5 — Cài Model B** (tên model hãy kiểm tra lại trên ollama.com/library trước khi pull):
```
ollama pull qwen2.5-coder:7b      # máy yếu/CPU; 14b nếu có GPU 16GB; qwen3-coder:30b nếu có 24GB+
```
Nên chọn model **khác họ** với Model A (`llama3`). Nếu `REVIEW_MODEL_NAME` trùng `MODEL_NAME`,
`--check` sẽ cảnh báo vì hai model sẽ sai giống nhau.

**Bước 6 — Kiểm tra:**
```
python ai/review.py --check
```
Phải thấy: Model B đã cài, role chỉ đọc đạt chuẩn, và không có dòng "Thiếu migration".
Nếu role chưa đạt, thông báo nói rõ lý do (còn quyền TEMP/CREATE, thiếu SELECT...).

## 2. Cách dùng

| Lệnh | Tác dụng |
|---|---|
| `python ai/review.py --calibrate --limit 10 --samples 1` | Cho Model B giải câu **nguồn** có đáp án thật, không ghi DB. **Chạy trước.** |
| `python ai/review.py --dry-run --limit 3` | Review thử, chỉ ghi JSON, không đổi DB |
| `python ai/review.py` | Review tất cả draft `pending` (hỏi xác nhận; `--yes` để bỏ qua) |
| `python ai/review.py --draft-id 7` | Review một draft |
| `python ai/review.py --show 7` | Xem log, các lời giải, test case của draft 7 |
| `python ai/review.py --reset-stuck` | Trả draft kẹt `reviewing` về `pending` (sau khi bị tắt đột ngột) |
| `--samples K` | Ghi đè số lần giải (mặc định 3) |

Kết quả JSON lưu ở `ai/outputs/review_*.json` và `ai/outputs/calibration_*.json`.

**Cách đọc `--calibrate`** (quan trọng nhất trước khi tin pipeline):
- `consensus_correct`: các lần giải đồng ý và đúng đáp án nguồn.
- `consensus_WRONG`: các lần giải đồng ý với nhau **nhưng sai**. Đây là rủi ro lớn nhất, vì pipeline sẽ duyệt nhầm.
- `no_consensus` / `no_valid_solution`: pipeline sẽ đẩy sang `needs_human` / `rejected` — an toàn nhưng tốn công.

Nếu `consensus_WRONG` cao, đổi Model B (mạnh hơn, khác họ) hoặc tăng `--samples` trước khi review hàng loạt.

## 3. Luồng xử lý và cách chốt trạng thái

1. **Kiểm tra trước giải**: đề trống/quá ngắn, bảng khai báo không hợp lệ, đề chứa SQL (lộ đáp án) → `rejected`.
2. **Model B giải k lần** (chỉ thấy câu hỏi, schema, FK, CHECK; không thấy metadata của Model A).
   Mỗi lần qua guard AST (`validator.py`) rồi chạy bằng role chỉ đọc; lỗi thì thử lại tối đa `REVIEW_SAMPLE_RETRIES` lần kèm lý do lỗi.
3. **Đồng thuận kiểu `all`**: mọi lời giải hợp lệ phải cho cùng kết quả (so theo vị trí cột, không so tên alias).
4. **Chọn reference SQL**: lời giải đơn giản nhất (ít node AST nhất; ưu tiên có `ORDER BY` nếu đề yêu cầu sắp xếp).
5. **Kiểm tra code**: chạy lại reference (phải ổn định), kết quả không rỗng và không quá lớn, khớp skill/độ khó, có tie-breaker nếu có thứ tự, không hardcode `*_id`, không nghi trùng lặp.
6. **Sinh test case** từ chính reference SQL, gắn `dataset_version`.

| Trạng thái | Khi nào |
|---|---|
| `approved` | Mọi bước đạt → có test case |
| `rejected` | Lộ đáp án; bảng khai báo sai; **không lời giải nào hợp lệ** (đổi được sang `needs_human` bằng `REVIEW_ZERO_VALID_ACTION`); reference không ổn định |
| `needs_human` | Chỉ một phần lời giải hợp lệ; các lần giải bất đồng; khác thứ tự; kết quả rỗng/quá lớn; skill/độ khó lệch; thiếu tie-breaker; hardcode id; nghi trùng |

Nguyên tắc **fail-closed**: thiếu bằng chứng thì không bao giờ `approved`.

## 4. Dữ liệu được ghi ở đâu

- `draft.question_drafts.status` (+ `compare_mode` khi `approved`)
- `draft.self_solve_runs`: mỗi lời giải của Model B, đánh dấu `is_selected`
- `draft.test_cases`: reference SQL + `expected_columns` + `expected_rows` + `result_hash` + `dataset_ref`/`dataset_version`
- `draft.review_logs`: từng giai đoạn (`code_check`, `self_solve`, `test_case`, `decision`); review lại thì log được **thêm**, còn `self_solve_runs`/`test_cases` được **thay**

Chuẩn hóa `expected_rows`: số → chuỗi chuẩn (`1.50` → `"1.5"`, `3` và `3.00` giống nhau), ngày → ISO, `NULL` giữ nguyên.
Bộ chấm bài sau này nên dùng cùng quy tắc (hàm `norm_value` trong `review.py`).

Mỗi draft được ghi trong **một transaction**; nếu bị tắt giữa chừng, draft ở `reviewing` và `--reset-stuck` trả về `pending`.
Lỗi Ollama/DB giữa phiên thì dừng, trả draft đang làm về `pending`, không kết luận gì về đề.

## 5. Giới hạn đã biết (đọc trước khi tin kết quả)

- **Chỉ một dataset thì không bắt được lời giải "đúng nhờ dữ liệu hiện tại"** (ví dụ cố định giá trị). Code có kiểm tra `*_id` hardcode nhưng đó chỉ là heuristic. Muốn chắc hơn: tạo thêm DB cùng schema khác dữ liệu rồi khai `REVIEW_VARIANT_DBS=ten_db1,ten_db2`; code đã hỗ trợ, test case sinh cho từng dataset.
- Đồng thuận giữa các lần giải của **cùng một model** vẫn có thể sai giống nhau; đó là lý do cần `--calibrate`.
- Kiểm tra skill/độ khó là heuristic trên AST, không chứng minh độ khó thực.
- Chưa có bước checklist LLM (bảng `review_logs` đã cho phép stage `checklist` để thêm sau).
- Đề vốn mơ hồ (không nói rõ cột kết quả, thứ tự, làm tròn) thường ra `needs_human` — đó là hành vi mong muốn.
- Mô hình yếu → nhiều `rejected`/`needs_human`. Đây là tín hiệu để đổi model, không phải lỗi code.

## 6. Xử lý sự cố

| Thông báo | Cách xử |
|---|---|
| `Chưa chạy migration...` | Làm bước 2 |
| `Chưa cấu hình ENTERPRISE_DB_USER` | Làm bước 3–4 |
| `Role chỉ đọc không đạt chuẩn an toàn` | Chạy lại `03_create_readonly_role.sql`; kiểm tra role không có quyền ghi/TEMP/CREATE |
| `Model B ... chưa cài` | `ollama pull <tên>` |
| `Ollama không phản hồi/timeout` | `ollama serve`; tăng `OLLAMA_TIMEOUT_SECONDS` nếu model nặng |
| `Prompt gần/vượt cửa sổ context` | Tăng `OLLAMA_CONTEXT_SIZE` |
| Draft kẹt `reviewing` | `python ai/review.py --reset-stuck` |

## 7. Kiểm thử

- `python -m unittest discover -s ai -p "test_review.py" -v`: 16 test, không cần DB hay Ollama.
- Các test cũ `test_model_a.py`, `test_domain_groups.py` cần DB thật và mật khẩu trong `ai/.env`.
