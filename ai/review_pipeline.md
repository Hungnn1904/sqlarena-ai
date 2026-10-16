# Pipeline kiểm duyệt (Model B) — hướng dẫn cài và chạy

`ai/review.py` lấy các draft `pending` do Model A sinh, cho **Model B giải k lần**, chạy từng lời giải trên
`enterprise_db` bằng role chỉ đọc, so kết quả, kiểm tra hợp đồng đầu ra/ORDER BY, rà alias subquery và chạy thêm
**semantic audit** bằng một lượt gọi LLM riêng trước khi chốt `approved` / `needs_human` / `rejected`.
Draft `approved` có sẵn **reference SQL + test case** (kết quả mong đợi) trong `draft.test_cases`.
Semantic audit giúp giảm lỗi hiểu đề nhưng không phải chứng minh toán học; phải tiếp tục theo dõi `approved_WRONG`
qua calibration và có thể cấu hình một model audit khác với Model B.

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
| `python ai/review.py --calibrate --limit 15 --samples 3` | Chạy **đúng pipeline review** trên câu **nguồn** có đáp án thật, không ghi DB. **Chạy trước.** |
| `python ai/review.py --calibrate --skip 15 --limit 20 --samples 3` | Đo tiếp từ câu thứ 16 (ENT-016...). Lần đo sau khi chỉnh prompt nên dùng các câu chưa dùng để chỉnh |
| `python ai/review.py --dry-run --limit 3` | Review thử, chỉ ghi JSON, không đổi DB |
| `python ai/review.py` | Review tất cả draft `pending` (hỏi xác nhận; `--yes` để bỏ qua) |
| `python ai/review.py --draft-id 7` | Review một draft |
| `python ai/review.py --show 7` | Xem log, các lời giải, test case của draft 7 |
| `python ai/review.py --reset-stuck` | Trả draft kẹt `reviewing` về `pending` (sau khi bị tắt đột ngột) |
| `--samples K` | Ghi đè số lần giải (mặc định 3) |

Kết quả JSON lưu ở `ai/outputs/review_*.json` và `ai/outputs/calibration_*.json`.

**Cách đọc `--calibrate`** (quan trọng nhất trước khi tin pipeline). Mỗi câu nguồn được chạy qua toàn bộ pipeline, rồi so với đáp án thật:
- `approved_correct`: pipeline duyệt và test case đúng.
- `approved_WRONG`: pipeline duyệt **nhưng sai** so với đáp án nguồn. Đây là rủi ro lớn nhất. Màn hình in kèm SQL của model và đáp án để so.
- `needs_human` / `rejected`: pipeline chặn lại. An toàn, nhưng tốn công duyệt tay.
- `*_but_all_samples_correct`: đề thực ra đúng nhưng bị chặn (quá thận trọng); nhiều dòng này nghĩa là kiểm tra đang quá chặt.

Ví dụ trong tập đo, các câu nguồn được **loại khỏi nguồn few-shot**, nên kết quả không bị "chép đáp án".
Nếu `approved_WRONG` còn cao: đổi/tăng Model B hoặc dùng hai model (mục 3b) trước khi review hàng loạt.

## 3. Luồng xử lý và cách chốt trạng thái

1. **Kiểm tra trước giải**: đề trống/quá ngắn, bảng khai báo không hợp lệ, đề chứa SQL (lộ đáp án) → `rejected`.
2. **Model B giải k lần** (chỉ thấy câu hỏi, schema, FK, CHECK; không thấy metadata của Model A).
   Prompt có: bảng nghĩa các cụm tiếng Việt ("loại/bỏ/trừ" = loại trừ, "giữ nguyên" = không lọc...), quy tắc **không tự thêm điều kiện** và **không bịa giá trị thay NULL**, và `REVIEW_FEWSHOT` ví dụ đã giải (cùng skill/bảng, **không** lấy câu cha của đề đang duyệt).
   Mỗi lần qua guard AST (`validator.py`) rồi chạy bằng role chỉ đọc; lỗi thì thử lại tối đa `REVIEW_SAMPLE_RETRIES` lần kèm lý do lỗi.
3. **Hợp đồng đầu ra**: nếu câu hỏi nêu `Cột kết quả theo thứ tự`, so sánh đúng tên và thứ tự cột. Nếu yêu cầu `Sắp xếp`, mọi mẫu phải có `ORDER BY`; khi parser hiểu được yêu cầu, đối chiếu đúng khóa và chiều tăng/giảm.
4. **Đồng thuận kiểu `all`**: mọi lời giải hợp lệ phải cho cùng kết quả (so theo vị trí cột; alias được kiểm tra riêng theo hợp đồng đầu ra).
5. **Kiểm tra code**: chạy lại reference (phải ổn định), kết quả không rỗng và không quá lớn, khớp skill/độ khó, **dùng đúng các bảng đã khai báo**, tie-breaker phải duy nhất theo cả bộ khóa sắp xếp trên dataset và các khóa này cần hiện trong đầu ra, không hardcode `*_id`, **không có hằng chuỗi lạ**, không nghi trùng lặp. S4 bắt buộc phải có subquery/derived table, không thể chỉ dùng JOIN.
6. **Semantic audit**: một prompt audit riêng phải trả về ít nhất 5 mục checklist bao phủ (a) cột/alias đầu ra, (b) WHERE/HAVING/ngưỡng aggregate, (c) JOIN/grain/EXISTS/subquery tương quan, (d) NULL/ngày/rounding/đơn vị, (e) ORDER BY/tie-breaker. Nếu audit báo lỗi, thiếu một trong 5 nhóm, checklist không đủ 5 mục, output lỗi hoặc không chắc chắn thì `needs_human`. Đây là kiểm tra bổ sung dựa trên LLM, không phải chứng minh toán học rằng SQL đúng.
7. **Sinh test case** từ chính reference SQL, gắn `dataset_version` chỉ sau khi toàn bộ lớp kiểm tra đạt.

| Trạng thái | Khi nào |
|---|---|
| `approved` | Mọi bước đạt → có test case |
| `rejected` | Lộ đáp án; bảng khai báo sai; reference không ổn định; hoặc không có lời giải hợp lệ nếu người quản trị đặt `REVIEW_ZERO_VALID_ACTION=rejected`. Mặc định mới là `needs_human` vì Model B không giải được chưa chứng minh đề sai. |
| `needs_human` | Chỉ một phần lời giải hợp lệ; các lần giải bất đồng; thiếu/sai ORDER BY; sai hợp đồng cột; thứ tự không xác định; alias subquery bị che khuất; audit ngữ nghĩa báo lỗi/không chắc chắn; kết quả rỗng/quá lớn; skill/độ khó lệch; `tables_mismatch`; `hardcoded_id_literal`; `unstated_string_literal`; nghi trùng |

Nguyên tắc **fail-closed**: thiếu bằng chứng thì không bao giờ `approved`.

## 3b. Cấu hình bổ sung (trong `ai/.env`)

| Khóa | Ý nghĩa |
|---|---|
| `REVIEW_FEWSHOT=2` | Số ví dụ đã giải đưa vào prompt Model B (0 = tắt). Lấy từ `core.source_questions`, loại câu cha của draft |
| `REVIEW_MODEL_NAME=modelX,modelY` | **Hai (hoặc nhiều) model** cùng giải. Các mẫu chia liên tiếp cho các model (k=3, 2 model → X, X, Y) và **phải đồng thuận chung**. Cần `REVIEW_SAMPLES` ≥ số model. Chọn hai model khác họ để giảm duyệt nhầm. Hai model nặng có thể phải nạp/đổi liên tục trong RAM nên chậm hơn |
| `REVIEW_SEMANTIC_AUDIT=true` | Bật semantic audit riêng. Nếu tắt, pipeline vẫn fail-closed: không tự động duyệt khi thiếu audit. |
| `REVIEW_AUDIT_MODEL_NAME=modelY` | Model dùng cho semantic audit; để trống thì mặc định dùng model B cuối cùng trong `REVIEW_MODEL_NAME`. Chọn model khác nếu máy đủ tài nguyên, nhưng model khác cũng không bảo đảm audit đúng tuyệt đối. |
| `REVIEW_AUDIT_NUM_PREDICT=600` | Giới hạn đầu ra của semantic audit; nếu output bị cắt, câu chuyển `needs_human`. |

Semantic audit cần ít nhất 5 mục kiểm tra có `requirement`, `status=pass` và `finding` không rỗng. Nếu Qwen trả checklist quá ngắn, hệ thống chủ động chặn tự động duyệt thay vì bỏ qua.

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
- Đồng thuận giữa các lần giải của **cùng một model** vẫn có thể sai giống nhau; semantic audit cũng là LLM và có thể bỏ sót lỗi. Đây là lý do cần `--calibrate`.
- Khi chỉ có một model local, solver và auditor mặc định có thể dùng cùng model nhưng prompt riêng; đây không phải hai đánh giá độc lập hoàn toàn. Có thể đặt `REVIEW_AUDIT_MODEL_NAME` sang model khác nếu tài nguyên đáp ứng.
- Kiểm tra skill/độ khó là heuristic trên AST, không chứng minh độ khó thực.
- Các yêu cầu sắp xếp/cột đầu ra không khai báo rõ thường được chuyển `needs_human` thay vì tự suy đoán.
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

- `python -m unittest discover -s ai -p "test_review.py" -v`: 25 test, không cần DB hay Ollama.
- Các test cũ `test_model_a.py`, `test_domain_groups.py` cần DB thật và mật khẩu trong `ai/.env`.


## v1.2: explicit semantic contract checks

Before calling the LLM semantic auditor, the reviewer now applies conservative checks for explicit question contracts:

- A field explicitly marked `(loại NULL)` must be excluded by the top-level `WHERE`.
- A question asking for at least N delivered orders must apply the delivered predicate inside the `HAVING` threshold, not merely count all orders.
- A month explicitly defined as the first day of the month must be cast to PostgreSQL `date`, not left as a timestamp.
- If `min_hours`, `max_hours`, and `avg_hours` are explicitly required to be rounded to N digits, each metric must be wrapped in the matching `ROUND(..., N)`.

These are conservative targeted checks, not a general proof of SQL equivalence. Any violation is sent to `needs_human` before the LLM audit can approve. Continue to run calibration and inspect false approvals on a holdout set.
