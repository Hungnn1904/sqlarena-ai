# Ghi Chú Pipeline AI

Current pipeline: `model_a_v2.1_topic_groups`. No SQL answers are generated or
executed. Draft uses `schema_text TEXT` and retains `schema_context JSONB`;
`reference_sql` is no longer a Draft field. The existing shared DB is already
migrated; do not add reference_sql back. See [question_only_pipeline.md](question_only_pipeline.md)
for current commands, storage, tests and limitations.

## Historical Answer-Generating Pipeline

The sections below document the prior version, not the current generation flow. For the current Model A behavior and recent run evidence, use `question_only_pipeline.md` and the dated section at the end of `test_report.md`. For current Model B calibration instructions and the latest false-acceptance warning, use `review_pipeline.md`.

## Run

From the project root:

```powershell
python -m pip install "psycopg[binary]" pglast scikit-learn python-dotenv
python ai/main.py --check
python ai/main.py
```

The Vietnamese terminal asks for count, difficulty, primary skill, domain,
preferred tables and extra constraints, then asks for confirmation. Canceling
does not generate or insert anything. `--check` reads configuration, Rules,
Core, the live Enterprise catalog and Draft, and runs a short Ollama JSON check.
It never inserts a question or runs AI SQL.

## Configuration

Edit `ai/.env`. Environment variables override this file.

- `ARENA_DB_*`: existing SQLArena connection, Core SELECT and Draft INSERT.
- `CATALOG_DB_*`: fixed read-only catalog/fingerprint queries on Enterprise.
  These credentials are never used to execute model-generated SQL.
- `ENTERPRISE_DB_*`: an existing SELECT-only login for AI execution. The user
  field is deliberately blank initially because the only existing login was
  the superuser `postgres`. No fallback to catalog/admin credentials occurs.
- `AI_PROVIDER=ollama`, `MODEL_NAME=llama3`, `OLLAMA_HOST=http://localhost:11434`.
- `MAX_RETRIES=2` means at most three attempts for each requested question.
- Statement timeout, Ollama timeout/context size, result-read limit and
  experimental duplicate thresholds are configurable.
- `RULES_PATH` is relative to the project root. Missing/incomplete Rules stop
  generation rather than replacing the taxonomy.

Do not commit `.env` or output files containing questions. No API key is needed.
Start Ollama yourself if unavailable. If a configured model is missing, the CLI
prints `ollama pull <model>` but never downloads the model itself.

An Enterprise execution login must have SELECT on all world tables and no
superuser, administrative, write, schema CREATE or database CREATE/TEMP
privileges. A database's default PUBLIC TEMP privilege also causes refusal.
Provisioning/revoking privileges is intentionally outside this program.
With missing/unsafe credentials a structurally valid question can still be
saved as Draft, with execution `not_run` and explicit review warnings.

## Storage And Checks

Core is the primary source. Every candidate receives exactly five sources from
the same world and difficulty, prioritizing skill/domain/related tables. These
are abstract metadata, not source answers or Enterprise data rows. Related
tables, FK bridge tables, applied Business Rules and Rules excerpts form a
separate context for each candidate. Rule validator excerpts are reference text,
not commands. Original source-set quotas do not restrict the new requested count.

`pglast` parses PostgreSQL ASTs. The conservative validator rejects multi-statement
SQL, non-SELECT statements including writable CTEs, SELECT INTO, row locks,
system/foreign-schema tables, unknown functions/operators/types and unsupported
FROM constructs. It resolves table/column references through aliases, CTEs,
derived tables, correlated subqueries and recursive seed branches. SQL columns
must actually exist and be declared in `required_columns`. Unsupported syntax
is rejected for retry, not executed with a weaker fallback.

Execution additionally requires a verified nonprivileged login, READ ONLY
transaction, timeout and `pg_catalog, public` search path. Server EXPLAIN binding
is refused if public has potentially shadowing functions/operators from the
allowlists. Binding
and query execution happen only after those checks. Results are counted by
streaming; above `MAX_RESULT_ROWS` the report records a lower bound, not a fake
exact count. Empty results are allowed. Tests of empty/error/timeout paths use
mocks when no SELECT-only login exists; they are not real execution evidence.

Duplicates are checked against all Core sources, existing Drafts and the current
session using normalized SHA-256, Vietnamese character TF-IDF/cosine, logic
signatures and literal-insensitive SQL shape. Legacy signature keys map explicitly
from goal/grain/predicate/transformation. Exact/clear duplicates retry. Lexical
or partial-logic suspicion is saved as `suspected_duplicate`, not auto-rejected.
This is a heuristic, not proof of novelty or SQL equivalence.

Accepted candidates only INSERT into `draft.question_drafts`, always `pending`.
The actual current schema uses JSONB skills/traps/parent_ids/context/report,
ordered/unordered comparison and integer depth. Depth **1** is generation
provenance from original Core roots, not SQL nesting; Core's nullable depth is
not changed. Traps are `[]` because this version does not claim to generate or
validate planted traps. Title, domain, primary skill, goal, reason and signature
remain in `validation_report.candidate_metadata` as the Draft table has no
dedicated columns for them. No review_logs or self_solve_runs are written.

Missing required Draft columns, incompatible types or unverified user triggers
block insertion. No migrations, reset, reseed, database/schema/table creation,
Core update or Enterprise data update exists in this program.

Every confirmed generation session gets a unique `ai/outputs/generation_*.json`.
Checkpoints include all attempts, failures, references, candidate metadata,
validation, acknowledged Draft IDs, and before/after Core/Enterprise fingerprints.
Insert failure is not reported as saved; an ambiguous commit requires manual
reconciliation before another insert. Session count reports actual committed
successes, never the requested count as assumed success.

## Limits

`passed_basic` is **not** semantic PASS, difficulty certification, novelty
certification or Model B approval. Output ordering/ties, time, money, NULL,
business logic and simplest-solution difficulty still need review. Static column
checks cannot fully resolve PostgreSQL types/functions without the safe login.
The SQL allowlist intentionally supports fewer constructs than PostgreSQL.
Ollama near-window/truncated responses are rejected; choose smaller table context
if needed. Manual extra requirements are passed to the model, not semantically
proven by a second LLM. Concurrent runs can still race between duplicate checking
and insertion; prefer one generation session at a time.

## Historical tests

The command below documents an earlier test subset, not a complete current verification. For current test commands and latest observed generation/calibration outcomes, use `README.md` and `test_report.md`.

```powershell
python -m unittest discover -s ai -p test_model_a.py -v
```

Includes offline fixtures and read-only integration checks of this existing Core
and catalog. It does not create database fixtures or insert test questions.
See `test_report.md` for the actual local run and remaining untested paths.

## v2 changes (prompt `model_a_v2`)

See `CHANGES_v2.md`. In short: the menu only offers skill/difficulty pairs the Rules taxonomy defines
(S1 is easy-only); S1 context is one table and S2 at least two; the prompt states the same contract the
validator enforces; `tables_used`, `required_columns` and `source_question_ids` are derived by code
(the model's own declaration is kept under `candidate._normalization`); retries carry `FIX:` instructions,
the goals already tried, and new focus columns instead of repeating the rejected goal.
