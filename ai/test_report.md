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
