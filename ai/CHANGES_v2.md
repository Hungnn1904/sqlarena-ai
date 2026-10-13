# Model A pipeline v2 — what changed and why

Prompt version: `model_a_v1` -> `model_a_v2` (stored in `draft.question_drafts.gen_prompt_version`).
Files changed: `main.py`, `validator.py`. New: `test_pipeline_v2.py`. `test_model_a.py` is unchanged.

| # | Problem in the 0/10 run | Change |
|---|---|---|
| 1 | `medium + S1` has no valid answer (Rules quota S1 = 8/0/0; validator forbids joins/aggregates/subqueries for S1) | `read_rules` parses the skill x difficulty table; `prompt_input` hides skills the taxonomy does not define for the chosen difficulty; `check_feasible` stops a bad request before any model call. Zero cells mean "pairing not defined", not a quota for new runs. |
| 2 | Context held one table (`orders`) but the model invented goals needing `refunds`, `employees`, `order_items` | S1 context = one table (S1 forbids JOIN); S2 context = at least two tables (FK neighbour added). Prompt says the goal must be answerable with the ALLOWED TABLES alone. |
| 3 | Model had to invent a goal, write SQL and declare matching metadata | `tables_used`, `required_columns`, `source_question_ids` are computed by code (`derive_sql_metadata`, chosen references). Validation still rejects tables outside the context and columns that do not exist. The model's own declaration is saved in `candidate._normalization`. |
| 4 | Retry repeated the same goal 3 times; feedback was bare error strings plus "Rejected prior goal" | `repair_hints` adds a `FIX:` instruction per error; rejected goals are listed as "already tried, pick a different entity/measure"; each retry suggests new focus columns. |
| 5 | Prompt contradicted the validator (asked for relative dates while `now()` / `CURRENT_DATE` are rejected; classification of all six skills; schema JSON twice) | `validator.py` now owns `SKILL_CONTRACTS`, `DIFFICULTY_CONTRACTS`, `COMMON_SQL_RULES`; the prompt prints them. Only the chosen skill's classification line is sent; precedence/alignment notes and long rule excerpts are trimmed in the prompt (the saved `schema_context` is unchanged). The S1 error now lists the offending features. |

Not changed on purpose: security allowlists, duplicate detection, insert/commit logic, one model call per attempt.
Not done: Planner/Blueprint with templates and Model B solving as in v7 (Model A still writes `reference_sql`).
