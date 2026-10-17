"""Unit test cho review.py: khong can PostgreSQL hay Ollama (dataset/solver gia lap)."""

import unittest
from datetime import date
from unittest import mock
from decimal import Decimal

import review as rv

SCHEMA = {"orders": {"order_id": "integer", "customer_id": "integer", "total_amount": "numeric", "status": "text"}}


def ok(columns, rows):
    return {"status": "ok", "columns": columns, "rows": rv.norm_rows(rows), "row_count": len(rows), "truncated": False}


class FakeDataset:
    def __init__(self, ref, results, version="v1", flaky=False):
        self.ref, self.results, self.version, self.flaky, self.calls = ref, results, version, flaky, 0

    def run(self, sql):
        self.calls += 1
        res = self.results.get(sql, {"status": "execution_error", "error": "unknown sql"})
        if self.flaky and self.calls > 3 and res["status"] == "ok":
            return ok(res["columns"], [[999]])
        return res


def make_ctx(**kw):
    ctx = {"draft_id": 1, "question": "Liệt kê đơn hàng, trả order_id và total_amount.", "difficulty": "easy",
           "skill": "S1", "tables_used": ["orders"], "schema": SCHEMA, "fks": [], "checks": {}, "rules": [],
           "primary_keys": {"order_id"}, "schema_text": "", "duplicate": {}}
    ctx.update(kw)
    return ctx


def scripted(sqls):
    it = iter(sqls)
    return lambda prompt, seed, temperature, model=None: (next(it), {})


def passing_audit(_ctx, _sql):
    groups = ["output columns and aliases", "WHERE/HAVING/aggregate thresholds",
              "joins, row grain, EXISTS and correlated subqueries",
              "NULL/date/rounding/unit edge cases", "ordering and tie-breakers"]
    return {"verdict": "pass", "issues": [],
            "checks": [{"requirement": group, "status": "pass", "finding": "unit-test mock"}
                       for group in groups]}


Q = "SELECT order_id AS order_id, total_amount AS total_amount FROM orders"
ROWS = ok(["order_id", "total_amount"], [[1, Decimal("10.50")], [2, Decimal("7")]])


class Normalisation(unittest.TestCase):
    def test_numbers_are_canonical(self):
        self.assertEqual(rv.norm_value(Decimal("1.50")), "1.5")
        self.assertEqual(rv.norm_value(3), rv.norm_value(Decimal("3.00")))
        self.assertEqual(rv.norm_value(2.5), "2.5")
        self.assertEqual(rv.norm_value(Decimal("-0.0")), "0")
        self.assertIsNone(rv.norm_value(None))
        self.assertEqual(rv.norm_value(date(2025, 1, 2)), "2025-01-02")

    def test_same_result_modes_and_positional_columns(self):
        a = ok(["x", "y"], [[1, "a"], [2, "b"]])
        b = ok(["p", "q"], [[2, "b"], [1, "a"]])
        self.assertTrue(rv.same_result(a, b, "unordered"))
        self.assertFalse(rv.same_result(a, b, "ordered"))
        self.assertFalse(rv.same_result(a, ok(["x"], [[1], [2]]), "unordered"))
        self.assertFalse(rv.same_result(a, {"status": "timeout"}, "unordered"))


class SqlAnalysis(unittest.TestCase):
    def test_guard_accepts_and_blocks(self):
        rv.guard_sql(Q, SCHEMA)
        for bad in ("DELETE FROM orders", "SELECT now() AS t FROM orders", "SELECT a AS a FROM other_table",
                    "SELECT order_id FROM orders; SELECT 1", "SELECT pg_sleep(1) AS s FROM orders"):
            with self.assertRaises(rv.SQL_ERRORS, msg=bad):
                rv.guard_sql(bad, SCHEMA)

    def test_mode_and_tiebreaker(self):
        tree, _ = rv.guard_sql(Q + " ORDER BY total_amount DESC", SCHEMA)
        self.assertEqual(rv.decide_mode(tree, "Sắp xếp theo total_amount giảm dần"), "ordered")
        self.assertEqual(rv.decide_mode(tree, "Liệt kê đơn hàng"), "unordered")
        self.assertFalse(rv.tiebreaker_ok(tree, {"order_id"}))
        tree2, _ = rv.guard_sql(Q + " ORDER BY total_amount DESC, order_id", SCHEMA)
        self.assertTrue(rv.tiebreaker_ok(tree2, {"order_id"}))

    def test_hardcoded_ids(self):
        tree, _ = rv.guard_sql(Q + " WHERE customer_id = 101 AND order_id IN (5, 6)", SCHEMA)
        found = rv.hardcoded_id_literals(tree, "Đơn của khách hàng 101")
        self.assertEqual(sorted(found), ["order_id=5", "order_id=6"])

    def test_skill_issues(self):
        _, info = rv.guard_sql(Q, SCHEMA)
        f = info["features"]
        self.assertIn("skill_s3_no_aggregate", rv.skill_difficulty_issues("S3", "medium", f))
        self.assertIn("skill_s2_no_join", rv.skill_difficulty_issues("S2", "easy", f))
        self.assertEqual(rv.skill_difficulty_issues("S1", "easy", f), [])
        _, info = rv.guard_sql("SELECT status AS s, count(*) AS n FROM orders GROUP BY status", SCHEMA)
        self.assertIn("skill_s1_has_forbidden_features", rv.skill_difficulty_issues("S1", "easy", info["features"]))


class Decision(unittest.TestCase):
    def run_review(self, sqls, results, ctx=None, datasets=None, k=3, **kw):
        datasets = datasets or [FakeDataset("enterprise/base", results)]
        kw.setdefault("auditor", passing_audit)
        return rv.review_draft(ctx or make_ctx(), datasets, scripted(sqls), k, kw.pop("retries", 0), **kw)

    def test_approved_creates_testcase_per_dataset(self):
        out = self.run_review([Q] * 3, {Q: ROWS})
        self.assertEqual(out["status"], "approved")
        self.assertEqual(out["reference_sql"], Q)
        self.assertEqual(out["testcases"][0]["expected_rows"], [["1", "10.5"], ["2", "7"]])
        self.assertEqual(out["testcases"][0]["compare_mode"], "unordered")

    def test_zero_valid_follows_config(self):
        bad = "SELECT x AS x FROM missing"
        self.assertEqual(self.run_review([bad] * 3, {})["status"], "needs_human")
        self.assertEqual(self.run_review([bad] * 3, {}, zero_valid_action="rejected")["status"], "rejected")
        self.assertEqual(self.run_review([bad] * 3, {}, zero_valid_action="needs_human")["status"], "needs_human")

    def test_partial_valid_is_not_approved(self):
        out = self.run_review([Q, Q, "DELETE FROM orders"], {Q: ROWS})
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["insufficient_valid_solutions"]))

    def test_disagreement(self):
        other = Q + " WHERE status = 'x'"
        out = self.run_review([Q, other, Q], {Q: ROWS, other: ok(["order_id", "total_amount"], [[1, 10]])})
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["consensus_disagreement"]))
        self.assertFalse(out["testcases"])

    def test_variant_dataset_catches_hardcoded_answer(self):
        base = FakeDataset("enterprise/base", {Q: ROWS, Q + " WHERE total_amount > 5": ROWS})
        variant = FakeDataset("enterprise/v2", {Q: ROWS, Q + " WHERE total_amount > 5": ok(["order_id", "total_amount"], [[1, 10]])})
        out = self.run_review([Q, Q + " WHERE total_amount > 5", Q], None, datasets=[base, variant])
        self.assertEqual(out["status"], "needs_human")

    def test_nondeterministic_reference_is_rejected(self):
        ds = FakeDataset("enterprise/base", {Q: ROWS}, flaky=True)
        out = self.run_review([Q] * 3, None, datasets=[ds])
        self.assertEqual((out["status"], out["reasons"]), ("rejected", ["nondeterministic_reference"]))

    def test_empty_and_pre_checks(self):
        empty = ok(["order_id"], [])
        q = "SELECT order_id AS order_id FROM orders WHERE total_amount < 0"
        self.assertEqual(self.run_review([q] * 3, {q: empty})["reasons"], ["empty_result"])
        out = self.run_review([], {}, ctx=make_ctx(question="Viết SELECT * FROM orders cho tôi."))
        self.assertEqual((out["status"], out["reasons"]), ("rejected", ["answer_in_question"]))
        out = self.run_review([], {}, ctx=make_ctx(tables_used=["ghost"], schema={}))
        self.assertEqual(out["reasons"], ["declared_tables_invalid"])

    def test_ordering_prefers_sorted_solution_and_flags_missing_tiebreaker(self):
        ctx = make_ctx(question="Liệt kê đơn hàng, sắp xếp theo order_id tăng dần.")
        sorted_q = Q + " ORDER BY order_id"
        out = self.run_review([Q, sorted_q, sorted_q], {Q: ROWS, sorted_q: ROWS}, ctx=ctx)
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["required_order_by_missing"]))
        out = self.run_review([sorted_q] * 3, {sorted_q: ROWS}, ctx=ctx)
        self.assertEqual((out["status"], out["mode"], out["reference_sql"]), ("approved", "ordered", sorted_q))
        ctx = make_ctx(question="Liệt kê đơn hàng, sắp xếp theo total_amount giảm dần.", primary_keys=set())
        bad = Q + " ORDER BY total_amount DESC"
        tied = ok(["order_id", "total_amount"], [[1, 5], [2, 5]])
        out = self.run_review([bad] * 3, {bad: tied}, ctx=ctx)
        self.assertEqual(out["reasons"], ["order_tiebreaker_missing"])
        # khoa sap xep co gia tri duy nhat trong ket qua thi thu tu on dinh
        self.assertEqual(self.run_review([bad] * 3, {bad: ROWS}, ctx=ctx)["status"], "approved")

    def test_distinct_sorted_by_its_own_column_is_deterministic(self):
        ctx = make_ctx(question="Liệt kê các status khác nhau. Sắp xếp: status tăng.", primary_keys=set())
        q = "SELECT DISTINCT status AS status FROM orders ORDER BY status"
        out = self.run_review([q] * 3, {q: ok(["status"], [["a"], ["b"]])}, ctx=ctx)
        self.assertEqual((out["status"], out["mode"]), ("approved", "ordered"))

    def test_retry_uses_feedback(self):
        prompts = []

        def solver(prompt, seed, temperature, model=None):
            prompts.append(prompt)
            return ("DELETE FROM orders" if len(prompts) == 1 else Q), {}
        out = rv.review_draft(make_ctx(), [FakeDataset("enterprise/base", {Q: ROWS})], solver, 1, 1,
                              auditor=passing_audit)
        self.assertEqual(out["status"], "approved")
        self.assertIn("PREVIOUS ATTEMPT WAS REJECTED", prompts[1])
        self.assertNotIn("PREVIOUS ATTEMPT", prompts[0])


class ImprovedChecks(unittest.TestCase):
    def test_unstated_literal_blocks_invented_placeholder(self):
        coalesce = "SELECT order_id AS order_id, COALESCE(status, 'None') AS status FROM orders"
        res = ok(["order_id", "status"], [[1, "paid"]])
        out = Decision.run_review(self, [coalesce] * 3, {coalesce: res})
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["unstated_string_literal"]))
        # gia tri co trong de hoac trong CHECK thi hop le
        stated = "SELECT order_id AS order_id FROM orders WHERE status = 'paid'"
        ctx = make_ctx(question="Liệt kê đơn hàng có status là paid.", all_checks=["CHECK (status IN ('paid','open'))"])
        out = Decision.run_review(self, [stated] * 3, {stated: ok(["order_id"], [[1]])}, ctx=ctx)
        self.assertEqual(out["status"], "approved")

    def test_date_words_and_formats_are_not_flagged(self):
        sql = "SELECT date_trunc('month', order_date) AS m, count(*) AS n FROM orders GROUP BY 1"
        # order_date khong co trong SCHEMA test nen chi kiem tra ham phan tich truc tiep
        schema = {"orders": {"order_id": "integer", "order_date": "date"}}
        tree, _ = rv.guard_sql(sql, schema)
        self.assertEqual(rv.unstated_string_literals(tree, "Đếm đơn theo tháng", []), [])

    def test_multi_model_assignment_and_greedy_per_model(self):
        self.assertEqual([rv.model_for(i, 3, ["a", "b"]) for i in range(3)], ["a", "a", "b"])
        self.assertEqual([rv.model_for(i, 2, ["a", "b"]) for i in range(2)], ["a", "b"])
        seen = []

        def solver(prompt, seed, temperature, model=None):
            seen.append((model, temperature))
            return Q, {}
        out = rv.review_draft(make_ctx(), [FakeDataset("enterprise/base", {Q: ROWS})], solver, 3, 0,
                              models=["a", "b"], auditor=passing_audit)
        self.assertEqual(out["status"], "approved")
        self.assertEqual(seen, [("a", 0.0), ("a", None), ("b", 0.0)])
        self.assertEqual([s["model"] for s in out["samples"]], ["a", "a", "b"])

    def test_config_requires_enough_samples_for_models(self):
        base = {"MODEL_NAME": "m", "OLLAMA_HOST": "http://x"}
        with mock.patch.object(rv.arena, "load_config", return_value=dict(base)):
            with self.assertRaisesRegex(ValueError, "REVIEW_SAMPLES"):
                rv.load_review_config({"REVIEW_MODEL_NAME": "a,b", "REVIEW_SAMPLES": "1"})
        with mock.patch.object(rv.arena, "load_config", return_value=dict(base)):
            config = rv.load_review_config({"REVIEW_MODEL_NAME": "a, b", "REVIEW_SAMPLES": "3"})
            self.assertEqual((config["REVIEW_MODELS"], config["REVIEW_FEWSHOT"]), (["a", "b"], 2))


    def test_sql_not_using_declared_tables_is_not_approved(self):
        q = "SELECT 1 AS x"
        out = Decision.run_review(self, [q] * 3, {q: ok(["x"], [[1]])})
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["tables_mismatch"]))


class SemanticSafety(unittest.TestCase):
    def test_extracts_output_columns_contract(self):
        question = "Tìm nhân viên.\nCột kết quả theo thứ tự: employee_id, department_id, current_salary.\nSắp xếp: employee_id tăng."
        self.assertEqual(rv.expected_columns_from_text(question), ["employee_id", "department_id", "current_salary"])

    def test_parses_order_contract_and_direction(self):
        ctx = {"question": "Tìm đơn.\nSắp xếp: total_amount giảm, order_date tăng, order_id tăng."}
        self.assertTrue(rv.ordering_required(ctx))
        self.assertEqual(rv.expected_order_specs(ctx), [("total_amount", "desc"), ("order_date", "asc"), ("order_id", "asc")])

    def test_required_order_by_missing_blocks_approval(self):
        ctx = make_ctx(question="Liệt kê đơn hàng.\nCột kết quả theo thứ tự: order_id, total_amount.\nSắp xếp: order_id tăng.")
        out = Decision.run_review(self, [Q] * 3, {Q: ROWS}, ctx=ctx)
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["required_order_by_missing"]))

    def test_output_column_mismatch_blocks_approval(self):
        ctx = make_ctx(question="Liệt kê đơn hàng.\nCột kết quả theo thứ tự: order_id, total_amount.",
                       expected_output_columns=["order_id", "total_amount"])
        wrong = "SELECT total_amount AS total_amount, order_id AS order_id FROM orders"
        result = ok(["total_amount", "order_id"], [[10, 1], [7, 2]])
        out = Decision.run_review(self, [wrong] * 3, {wrong: result}, ctx=ctx)
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["output_columns_mismatch"]))

    def test_shadowed_correlated_subquery_alias_blocks(self):
        schema = {"employees": {"employee_id": "integer", "department_id": "integer", "current_salary": "numeric"}}
        sql = ("SELECT employee_id AS employee_id FROM employees WHERE current_salary > "
               "(SELECT AVG(current_salary) FROM employees WHERE department_id = employees.department_id)")
        tree, _ = rv.guard_sql(sql, schema)
        self.assertEqual(rv.shadowed_subquery_aliases(tree), ["employees"])

    def test_join_alone_does_not_satisfy_s4(self):
        _, info = rv.guard_sql("SELECT o.order_id AS order_id FROM orders o JOIN orders o2 ON o.order_id=o2.order_id", SCHEMA)
        self.assertIn("skill_s4_no_subquery", rv.skill_difficulty_issues("S4", "medium", info["features"]))

    def test_semantic_auditor_flag_blocks_approval(self):
        q = Q
        ds = FakeDataset("enterprise/base", {q: ROWS})
        audit = lambda _ctx, _sql: {"verdict": "needs_human", "issues": ["HAVING counts all orders, not delivered orders"],
                                   "checks": [{"requirement": "delivered threshold", "status": "fail", "finding": "Wrong aggregate filter"}]}
        out = rv.review_draft(make_ctx(), [ds], scripted([q] * 3), 3, 0, auditor=audit)
        self.assertEqual((out["status"], out["reasons"]), ("needs_human", ["semantic_audit_flagged"]))
        self.assertFalse(out["testcases"])

    def test_missing_semantic_auditor_fails_closed(self):
        out = Decision.run_review(self, [Q] * 3, {Q: ROWS}, auditor=None)
        # Decision helper supplies the normal passing mock unless explicitly overridden.
        self.assertEqual(out["status"], "needs_human")
        self.assertEqual(out["reasons"], ["semantic_audit_unavailable"])


class FewShot(unittest.TestCase):
    POOL = [
        {"question_id": "ENT-001", "difficulty": "easy", "primary_skill_group": "S1", "question_text": "Q1", "reference_sql": "SELECT 1", "metadata": {"tables_used": ["orders"]}},
        {"question_id": "ENT-002", "difficulty": "easy", "primary_skill_group": "S2", "question_text": "Q2", "reference_sql": "SELECT 2", "metadata": {"tables_used": ["orders"]}},
        {"question_id": "ENT-003", "difficulty": "easy", "primary_skill_group": "S1", "question_text": "Q3", "reference_sql": "SELECT 3", "metadata": {"tables_used": ["products"]}},
        {"question_id": "ENT-004", "difficulty": "hard", "primary_skill_group": "S1", "question_text": "x" * 1000, "reference_sql": "SELECT 4", "metadata": {}},
    ]

    def test_prefers_same_skill_and_tables_and_excludes_parents(self):
        ex = rv.pick_examples(self.POOL, make_ctx(), 2, exclude={"ENT-001"})
        self.assertEqual([e["id"] for e in ex], ["ENT-003", "ENT-002"])
        self.assertEqual(rv.pick_examples(self.POOL, make_ctx(), 0), [])

    def test_too_long_examples_are_skipped(self):
        ids = [e["id"] for e in rv.pick_examples(self.POOL, make_ctx(), 4)]
        self.assertNotIn("ENT-004", ids)

    def test_prompt_contains_glossary_rules_and_examples(self):
        ctx = make_ctx(examples=[{"id": "ENT-001", "question": "Câu mẫu", "sql": "SELECT 1"}])
        prompt = rv.build_solver_prompt(ctx)
        for needle in ("EXCLUDE X", "IS NOT NULL", "Do NOT add any WHERE", "Do NOT use COALESCE", "SOLVED EXAMPLES", "Câu mẫu"):
            self.assertIn(needle, prompt)
        self.assertNotIn("SOLVED EXAMPLES", rv.build_solver_prompt(make_ctx()))


class Prompt(unittest.TestCase):
    def test_prompt_hides_everything_but_question_and_schema(self):
        prompt = rv.build_solver_prompt(make_ctx(schema_text="public.orders\n  - order_id: integer NOT NULL"))
        self.assertIn("ALLOWED TABLES", prompt)
        self.assertIn("Liệt kê đơn hàng", prompt)
        self.assertNotIn("difficulty", prompt.lower().replace("difficulty_", ""))


class ExplicitSemanticContracts(unittest.TestCase):
    def test_ent024_wrong_sql_is_blocked_for_null_and_delivered_threshold(self):
        ctx = make_ctx(
            question=("Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, "
                      "số đơn delivered và tổng total_amount chỉ của đơn delivered. "
                      "Giữ người có ít nhất 5 đơn delivered."),
            expected_output_columns=["employee_id", "assigned_orders", "delivered_orders", "delivered_order_value"])
        wrong = ("SELECT employee_id, COUNT(order_id) AS assigned_orders, "
                 "SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders, "
                 "SUM(CASE WHEN status = 'delivered' THEN total_amount ELSE 0 END) AS delivered_order_value "
                 "FROM orders GROUP BY employee_id HAVING COUNT(order_id) >= 5 ORDER BY employee_id")
        issues = rv.explicit_semantic_contract_issues(ctx, wrong)
        self.assertIn("explicit_null_exclusion_missing", issues)
        self.assertIn("conditional_having_threshold_missing_delivered_filter", issues)

    def test_ent024_correct_contract_passes_static_checks(self):
        ctx = make_ctx(
            question=("Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, "
                      "số đơn delivered và tổng total_amount chỉ của đơn delivered. "
                      "Giữ người có ít nhất 5 đơn delivered."),
            expected_output_columns=["employee_id", "assigned_orders", "delivered_orders", "delivered_order_value"])
        correct = ("SELECT employee_id, COUNT(*) AS assigned_orders, "
                   "COUNT(*) FILTER (WHERE status='delivered') AS delivered_orders, "
                   "SUM(total_amount) FILTER (WHERE status='delivered') AS delivered_order_value "
                   "FROM orders WHERE employee_id IS NOT NULL GROUP BY employee_id "
                   "HAVING COUNT(*) FILTER (WHERE status='delivered') >= 5 ORDER BY employee_id")
        self.assertEqual(rv.explicit_semantic_contract_issues(ctx, correct), [])

    def test_month_must_be_date_not_timestamp(self):
        ctx = make_ctx(
            question="Thời gian: expense_date; month là ngày đầu tháng.",
            expected_output_columns=["month", "department_id", "expense_count", "total_expense", "approved_expense"])
        wrong = "SELECT date_trunc('month', expense_date) AS month, department_id FROM orders"
        right = "SELECT date_trunc('month', expense_date)::date AS month, department_id FROM orders"
        self.assertIn("month_output_must_be_date", rv.explicit_semantic_contract_issues(ctx, wrong))
        self.assertNotIn("month_output_must_be_date", rv.explicit_semantic_contract_issues(ctx, right))

    def test_each_hour_aggregate_must_be_rounded(self):
        ctx = make_ctx(
            question="Tính thời gian xử lý. Làm tròn các số giờ 2 chữ số.",
            expected_output_columns=["completed_refunds", "min_hours", "max_hours", "avg_hours"])
        sql = ("SELECT MIN(x) AS min_hours, MAX(x) AS max_hours, "
               "ROUND(AVG(x), 2) AS avg_hours FROM orders")
        issues = rv.explicit_semantic_contract_issues(ctx, sql)
        self.assertIn("required_rounding_missing_min_hours", issues)
        self.assertIn("required_rounding_missing_max_hours", issues)
        self.assertNotIn("required_rounding_missing_avg_hours", issues)


class ContractAndRepairV13(unittest.TestCase):
    def test_audit_labels_must_cover_five_distinct_groups(self):
        groups = ["output columns and aliases"] * 5
        checks = [{"requirement": label, "status": "pass", "finding": "looks fine"} for label in groups]
        # An auditor returning five generic duplicate labels must not satisfy the five-group contract.
        self.assertEqual({rv.audit_requirement_group(c["requirement"]) for c in checks}, {"output_columns"})
        self.assertIsNone(rv.audit_requirement_group("all SQL aspects look correct"))
        canonical = ["output columns and aliases", "WHERE/HAVING/aggregate thresholds",
                     "joins, row grain, EXISTS and correlated subqueries",
                     "NULL/date/rounding/unit edge cases", "ordering and tie-breakers"]
        self.assertEqual({rv.audit_requirement_group(label) for label in canonical},
                         {"output_columns", "filters_aggregates", "joins_grain_subqueries", "edge_cases", "ordering"})

    def test_semantic_auditor_rejects_duplicate_group_labels(self):
        audit = {"verdict": "pass", "issues": [], "checks": [
            {"requirement": "output columns and aliases", "status": "pass", "finding": "All columns seem correct."}
            for _ in range(5)
        ]}
        config = {"REVIEW_SEMANTIC_AUDIT": True, "REVIEW_AUDIT_MODEL_NAME": "test-auditor",
                  "OLLAMA_CONTEXT_SIZE": 4096, "REVIEW_AUDIT_NUM_PREDICT": 600,
                  "REVIEW_OLLAMA_HOST": "http://localhost:11434", "REVIEW_THINK": None}
        ctx = make_ctx()
        with mock.patch.object(rv.arena, "ollama_request", return_value={"response": __import__("json").dumps(audit)}):
            result = rv.call_semantic_auditor(config, ctx, Q)
        self.assertEqual(result["verdict"], "needs_human")
        self.assertIn("audit_group_filters_aggregates_missing", result["issues"])
        self.assertIn("audit_group_ordering_missing", result["issues"])

    def test_explicit_no_order_overrides_stale_metadata(self):
        question = "Tính số yêu cầu và thời gian xử lý.\nSắp xếp: Một dòng nên không có yêu cầu thứ tự."
        ctx = {"question": question, "ordering_required": True, "expected_order_by": "refund_id tăng"}
        self.assertTrue(rv.explicit_no_order_requested(question))
        self.assertFalse(rv.ordering_required(ctx))
        self.assertEqual(rv.expected_order_specs_full(ctx), [])
        self.assertEqual(rv.decide_mode({"SelectStmt": {"sortClause": []}}, question), "unordered")

    def test_inline_question_order_contract_is_recognized(self):
        question = "Liệt kê các status khác nhau. Sắp xếp: status tăng."
        ctx = {"question": question, "ordering_required": False, "expected_order_by": "other_col giảm"}
        self.assertEqual(rv.expected_order_specs_full(ctx), [("status", "asc", "default")])
        self.assertTrue(rv.ordering_required(ctx))

    def test_question_order_contract_precedes_stale_metadata(self):
        ctx = {"question": "Tìm supplier.\nSắp xếp: supplier_id tăng, supplier_name giảm NULLS LAST.",
               "expected_order_by": "supplier_name tăng"}
        self.assertEqual(rv.expected_order_specs_full(ctx),
                         [("supplier_id", "asc", "default"), ("supplier_name", "desc", "last")])

    def test_query_contract_surfaces_question_and_logic_signature(self):
        ctx = make_ctx(
            question="Tính tổng theo status.\nCột kết quả theo thứ tự: status, total.\nSắp xếp: status tăng.",
            expected_output_columns=["status", "total"], output_grain="one row per status",
            logic_signature={"analysis_goal": "sum amount", "filter_pattern": "none",
                             "aggregation_pattern": "SUM by status", "output_grain": "one row per status"})
        contract = rv.build_query_contract(ctx)
        self.assertEqual(contract["required_output_columns"], ["status", "total"])
        self.assertEqual(contract["output_grain"], "one row per status")
        self.assertEqual(contract["ordering"]["keys"][0]["column"], "status")
        self.assertEqual(contract["aggregation_pattern"], "SUM by status")
        self.assertEqual(contract["source_of_truth"], "question_text")

    def test_repair_loop_reruns_all_checks_and_tracks_approval(self):
        failed = {"draft_id": 5, "status": "needs_human", "reasons": ["semantic_audit_flagged"],
                  "reference_sql": "SELECT status FROM orders", "samples": [], "testcases": [], "notes": [],
                  "stages": {"semantic_audit": {"passed": False, "issues": ["aggregate threshold missing"]}}}
        passed = {"draft_id": 5, "status": "approved", "reasons": [], "reference_sql": "SELECT status FROM orders",
                  "samples": [], "testcases": [{"dataset_ref": "base"}], "notes": [], "stages": {}}
        with mock.patch.object(rv, "_review_draft_once", side_effect=[failed, passed]) as run_once:
            result = rv.review_draft(make_ctx(), [], lambda *_: None, 3, 0, auditor=passing_audit, repair_rounds=1)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["stages"]["repair"]["attempted"], 1)
        self.assertTrue(result["stages"]["repair"]["approved_after_repair"])
        self.assertEqual(run_once.call_count, 2)
        self.assertIn("feedback", run_once.call_args.kwargs)

    def test_repair_loop_does_not_repeat_precheck_rejection(self):
        rejected = {"draft_id": 5, "status": "rejected", "reasons": ["answer_in_question"],
                    "samples": [], "testcases": [], "notes": [], "stages": {"pre": {"passed": False}}}
        with mock.patch.object(rv, "_review_draft_once", return_value=rejected) as run_once:
            result = rv.review_draft(make_ctx(), [], lambda *_: None, 3, 0, repair_rounds=2)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(run_once.call_count, 1)
        self.assertEqual(result["stages"]["repair"]["attempted"], 0)

    def test_draft_context_reads_output_grain_from_logic_signature(self):
        row = {
            "draft_id": 9, "question": "Tìm supplier.\nCột kết quả theo thứ tự: supplier_id.\nSắp xếp: supplier_id tăng.",
            "difficulty": "easy", "skills": ["S1"], "parent_ids": [], "schema_text": "",
            "schema_context": {"tables_used": ["suppliers"], "tables": [{"table": "suppliers",
                "columns": [{"name": "supplier_id", "type": "integer"}], "primary_key": ["supplier_id"]}],
                "fk_relations": [], "business_rules": []},
            "validation_report": {"candidate_metadata": {"tables_used": ["suppliers"],
                "output_columns": ["supplier_id"], "logic_signature": {"output_grain": "one row per supplier",
                "analysis_goal": "list suppliers", "filter_pattern": "none", "aggregation_pattern": "none"}}}
        }
        ctx = rv.draft_context(row)
        self.assertEqual(ctx["output_grain"], "one row per supplier")
        self.assertEqual(ctx["query_contract"]["output_grain"], "one row per supplier")

    def test_one_to_many_join_is_flagged_for_single_supplier_grain(self):
        # Existing Model A schema does not require central_table in logic_signature/query_contract.
        # The guard should infer suppliers from the selected outer alias and child->parent FK.
        ctx = {
            "question": "Tìm nhà cung cấp đang hoạt động.",
            "output_grain": "per supplier",
            "logic_signature": {"grain": "per supplier"},
            "fks": ["products(supplier_id) -> suppliers(supplier_id)"],
            "query_contract": {"output_grain": "per supplier"},
        }
        tree = {"SelectStmt": {
            "fromClause": [{"JoinExpr": {
                "larg": {"RangeVar": {"relname": "suppliers", "alias": {"aliasname": "s"}}},
                "rarg": {"RangeVar": {"relname": "products", "alias": {"aliasname": "p"}}},
            }}],
            "targetList": [
                {"ResTarget": {"val": {"ColumnRef": {"fields": [{"String": {"sval": "s"}}, {"String": {"sval": "supplier_id"}}]}}}},
                {"ResTarget": {"val": {"ColumnRef": {"fields": [{"String": {"sval": "s"}}, {"String": {"sval": "supplier_name"}}]}}}},
            ],
            "distinctClause": [], "groupClause": [],
        }}
        info = {"features": {"joins": 1}}
        self.assertEqual(rv._direct_from_relations(tree), [("suppliers", "s"), ("products", "p")])
        self.assertIn("one_to_many_join_may_duplicate_output_grain",
                      rv.one_to_many_join_grain_issues(ctx, tree, info))
        tree["SelectStmt"]["distinctClause"] = [{}]
        self.assertEqual(rv.one_to_many_join_grain_issues(ctx, tree, info), [])

    def test_contract_null_filter_and_threshold_detection_ent024(self):
        ctx = make_ctx(
            question=("Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, "
                      "số đơn delivered và tổng total_amount chỉ của đơn delivered. "
                      "Giữ người có ít nhất 5 đơn delivered."),
            expected_output_columns=["employee_id", "assigned_orders", "delivered_orders", "delivered_order_value"])
        wrong = ("SELECT employee_id, COUNT(order_id) AS assigned_orders, "
                 "SUM(CASE WHEN status='delivered' THEN 1 ELSE 0 END) AS delivered_orders, "
                 "SUM(CASE WHEN status='delivered' THEN total_amount ELSE 0 END) AS delivered_order_value "
                 "FROM orders GROUP BY employee_id HAVING COUNT(order_id)>=5 ORDER BY employee_id")
        issues = rv.explicit_semantic_contract_issues(ctx, wrong)
        self.assertIn("explicit_null_exclusion_missing", issues)
        self.assertIn("conditional_having_threshold_missing_delivered_filter", issues)


if __name__ == "__main__":
    unittest.main()
