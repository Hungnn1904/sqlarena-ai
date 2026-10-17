# Model A v1 Local Verification

Date: 2026-10-11 (Asia/Bangkok).

## Actual Results

- `python ai/main.py --check`: exit 0. Rules read from
  `question_create/enterprise_50_question_rules_v1.md`; Core has 1 world,
  6 skills and 50 sources. Live Enterprise catalog matches all 16 Core tables.
  Draft exists with both required JSONB columns and the inspected mapping.
- Local Ollama responds, `llama3:latest` is installed, and the short request
  returned `{"ok":true}`. No model was installed/downloaded by this task.
- `python -m unittest discover -s ai -p test_model_a.py -v`: **21 tests passed**
  after final code changes. Tests cover JSON fields, real PostgreSQL AST safety,
  physical/CTE/derived/correlated/recursive column binding, metadata mismatches,
  duplicate/suspicion handling, empty/error/timeout/not-run mocks, bounded retry,
  terminal reprompts/cancel, unique outputs, insert mapping/commit acknowledgment,
  insert failure, Ollama error paths, actual Core/reference rotation, and actual
  rejection of the superuser before model SQL could execute.
- A concurrent test invocation while Ollama was resident once failed to import
  SciPy with `MemoryError`. Re-running serially after the generation process
  exited passed all 21 tests. No dependency or DB change was needed; on this
  machine avoid unnecessary concurrent Python/model processes.

## Real Generation And Storage

The first prompt version made three bounded attempts and saved **0/1**, because
Llama omitted `source_question_ids`. Nothing was silently filled or inserted.
That failure remains in `outputs/generation_20261011_171508.json`.

After strengthening the prompt's final required schema and user constraints,
the second session saved **1/1** on its first attempt:

- File: `outputs/generation_20261011_172056.json`.
- Draft ID: **1**, status **pending**, difficulty **easy**, primary skill **S1**.
- Domain: Product & Inventory; table: products.
- Goal: list product prices/costs and the arithmetic price spread, ordered by
  spread descending then product_id ascending. It does not assert realized profit.
- Five source IDs: ENT-005, ENT-008, ENT-001, ENT-002, ENT-003, all easy from Core.
- Stored SQL:

```sql
SELECT product_id, product_name, list_price, cost_price,
       list_price - cost_price AS price_spread
FROM products
ORDER BY price_spread DESC, product_id ASC;
```

Real Ollama metrics: 2,802 prompt tokens, 302 generated tokens, approximately
93.44 seconds total model time. Closest lexical source ENT-005 scored 0.576285;
no exact/clear logic duplicate was detected. This is not a novelty certificate.

After commit, SELECT readback confirmed that the DB and JSON question, SQL,
validation report and schema-table context match. Validation of the saved
candidate with the final parser/allowlist code also passed basic checks.

Before/after fingerprints and a subsequent independent read matched for all
16 Enterprise tables, its inspected column/constraint catalog, and all four
Core tables, including all 50 source records. Existing seed/SQL/Core-generation
files were not modified. The only DB write was the one Draft INSERT.

## Not Executed / Not Approved

The only existing PostgreSQL login is superuser `postgres`. No SELECT-only
login exists/configured. Therefore the generated SQL was **not executed**;
its real execution status is **not_run**, row count **null**. No admin fallback,
role creation, grant, database migration, reset or reseed was performed.

Actual AI query execution, real empty result handling and real query timeout
remain untested until the user supplies an existing SELECT-only connection in
`ai/.env`. Empty/timeout behavior passed mocked tests only. Draft 1 remains
pending, `semantic_valid=null`, `model_b_reviewed=false`; basic PASS is not a
claim that the answer or reasoning difficulty has been formally reviewed.

Dependencies available during final tests: psycopg 3.3.6, pglast 8.5,
scikit-learn 1.9.1, and python-dotenv. The production entrypoint and validator
are the only two implementation modules; the third Python file is tests.


---

# Trạng thái xác minh mới nhất — 2026-10-17

Phần trên là báo cáo lịch sử của Model A answer-generating pipeline ngày 2026-10-11; không dùng riêng phần đó để mô tả hành vi hiện tại. Tài liệu này được bổ sung các lần chạy mới nhất có log trong repository.

## Model A — sinh câu hỏi, không sinh đáp án

- Prompt version trong log: `model_a_v2.1_topic_groups`. Model A chỉ tạo câu hỏi/metadata; không tạo reference SQL và không thực thi đáp án.
- Chạy 1 câu `medium`, kỹ năng `S2`, domain không giới hạn: thử 3 lần, `saved_count = 0`. JSON: `outputs/generation_20261017_102543.json`.
- Cả ba candidate đều bị `topic_relations` từ chối vì `join_relations` không khớp quan hệ FK thật giữa các bảng được khai báo. Một số lần còn bị `business_dependencies` vì câu hỏi dùng `orders.status` hoặc `customer_addresses.is_default` nhưng metadata không khai báo đúng cột.
- `protected_data_unchanged = true`; fingerprint trước/sau trong JSON không thay đổi. Lần chạy này không lưu draft.

**Đánh giá:** validator đã fail-closed và ngăn đề lỗi được lưu, nhưng retry chưa khắc phục được lỗi JOIN/metadata. Chưa có bằng chứng cho thấy Model A hiện tại sinh ổn định; cần sửa prompt/retry hoặc context chọn bảng, không nên nới lỏng validator.

## Model B — calibration

Lệnh đã chạy trên máy người dùng:

```powershell
python ai/review.py --calibrate --skip 15 --limit 20 --samples 3
```

- File JSON: `outputs/calibration_20261017_101930.json`.
- Model B: `qwen2.5-coder:7b`; semantic auditor: `llama3:latest`; 3 mẫu mỗi câu; 2 few-shot examples.
- Kết quả: `approved_correct = 10`, `approved_WRONG = 1`, `needs_human = 8`, `needs_human_but_all_samples_correct = 1`.
- ENT-017 là false acceptance: cả 3 mẫu dùng `SUM(total_amount + shipping_fee)` trong khi reference dùng `SUM(total_amount)`. JSON cho thấy `semantic_contract.passed = true` và `semantic_audit.verdict = pass` dù các mẫu không đúng theo reference/dataset calibration.

**Đánh giá:** đây là lỗi nghiêm trọng. Không nên dùng Model B để duyệt tự động hàng loạt cho tới khi đã điều tra logic audit/contract, thêm regression test cho ENT-017, chạy lại calibration và kiểm tra một tập holdout. Đổi sang model lớn hơn có thể đáng thử nhưng không thay thế regression test.

## Điều chưa được chứng minh

- Chưa có bằng chứng từ báo cáo này rằng toàn bộ unit test của snapshot ngày 2026-10-17 đã được chạy thành công; hãy chạy lại các lệnh kiểm thử trong README trên đúng source hiện tại.
- Calibration là đánh giá trên câu nguồn có đáp án, không ghi database và không chứng minh khả năng tổng quát trên mọi dataset.
- Lần sinh đề thất bại không chứng minh PostgreSQL bị lỗi; JSON ghi fingerprint dữ liệu không đổi.
