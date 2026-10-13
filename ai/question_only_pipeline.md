# Ghi Chú Pipeline Question-only

## Topic Groups (model_a_v2.1_topic_groups)

Context is selected by business topic, not copied from a source question's table
list. Finance rotates payments/refunds and operating costs; other topics use
customer/order, employee/department/pay, product/catalog/stock/warehouse, and
sales/detail/history neighborhoods. Every neighborhood is checked against the
actual world schema and FK graph. Unrestricted topic choice cycles all five
topics; a concrete topic still governs each generated question.

Preferred tables must fit a group in the chosen topic, otherwise generation stops
with an explicit error rather than changing the topic. S1 can see a neighborhood
but must declare one table. S2 and Medium questions must declare at least two
genuinely useful tables. This is a dataset-diversity generation policy, not proof
that two tables make a question Medium. Easy S3 and Hard/S6 can still legitimately
declare one table; reasoning and actual difficulty need human review.

New metadata includes table_roles and join_relations. Each role must name the
data a table contributes. Joins must match actual FK definitions (either direction)
and connect all declared tables, including bridge tables and every composite FK column. Join keys
must appear in required_columns. At least one primary topic table is required.
Context stores the full neighborhood, while schema_text still lists only question
tables. There are no new DB columns or migrations.

Explicit phrase guards reject known missing dependencies such as warehouse
managers without warehouses, designated department managers without departments,
successful payments without payments.payment_status, or customer-based order
analysis without orders.customer_id. These guards are deliberately narrow and
cannot prove arbitrary natural-language semantics or table necessity.

Five same-difficulty Core references remain. Out-of-scope source goals are not
sent as business examples; only their abstract techniques are included. Model A
still never generates or executes SQL answers. Accepted questions are pending /
NEEDS_HUMAN, not semantic PASS. Temperature is .35 and output is bounded to 1200
tokens to reduce long answer-like responses. Existing .env credentials are unchanged.

Ollama receives a required JSON Schema in format, not just the string json, so
question fields cannot be replaced by a copy of the TASK object. This uses the
[documented generate API](https://docs.ollama.com/api/generate). Known FK join keys
can be added deterministically to required_columns from a validated declared
relationship. Original model declarations and added keys are retained in
_normalization; invalid columns are never renamed and business dependencies are
never invented. This is not SQL lineage or a semantic repair of the question.

This patch is specific to the project in
`D:\nam 4\do an\SQL app\New folder\new_design_AI\new_design_AI`.
It retains the local v2 menus, table selection, source selection and retry flow.

Model A now returns only questions and metadata, not reference_sql. tables_used
and required_columns are model-declared and checked against the real schema;
source_question_ids are assigned by code. Answer fields/SQL snippets are rejected.
There is no answer execution, SQL AST proof of usage or semantic approval.
Accepted drafts remain pending/NEEDS_HUMAN with execution=not_applicable.

The shared database already has reference_sql removed from draft.question_drafts
and schema_text TEXT added. No further migration/reset is needed or run by the CLI.
schema_context stays unchanged in structure. schema_text contains only declared
question tables with all their actual columns, types and nullability. Code renders
it from checked schema definitions, not from model-written schema text.
Core source answers and existing Draft records are not modified by this code fix.
compare_mode retains the default unordered; this stage does not certify ordering.

```powershell
python ai/main.py --check
python ai/main.py
python ai/main.py --dry-run
python -m unittest discover -s ai -p 'test_*.py' -v
```

The startup must show `model_a_v2.1_topic_groups`, not require reference_sql or a
SELECT-only AI execution login. Existing ENTERPRISE_DB execution credentials may
remain in .env but are not used to run answers. CATALOG remains read-only.
--dry-run writes output but never inserts Drafts. Old .env and output files are
not overwritten. Historical CHANGES_v2.md/test_report.md describe the earlier
answer-generating pipeline, not this new version.
