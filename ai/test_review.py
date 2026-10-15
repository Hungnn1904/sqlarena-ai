"""Unit test cho review.py: khong can PostgreSQL hay Ollama (dataset/solver gia lap)."""

import unittest
from datetime import date
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
    return lambda prompt, seed, temperature: (next(it), {})


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
        return rv.review_draft(ctx or make_ctx(), datasets, scripted(sqls), k, kw.pop("retries", 0), **kw)

    def test_approved_creates_testcase_per_dataset(self):
        out = self.run_review([Q] * 3, {Q: ROWS})
        self.assertEqual(out["status"], "approved")
        self.assertEqual(out["reference_sql"], Q)
        self.assertEqual(out["testcases"][0]["expected_rows"], [["1", "10.5"], ["2", "7"]])
        self.assertEqual(out["testcases"][0]["compare_mode"], "unordered")

    def test_zero_valid_follows_config(self):
        bad = "SELECT x AS x FROM missing"
        self.assertEqual(self.run_review([bad] * 3, {}, )["status"], "rejected")
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
        self.assertEqual((out["status"], out["mode"], out["reference_sql"]), ("approved", "ordered", sorted_q))
        ctx = make_ctx(question="Liệt kê đơn hàng, sắp xếp theo total_amount giảm dần.", primary_keys=set())
        bad = Q + " ORDER BY total_amount DESC"
        out = self.run_review([bad] * 3, {bad: ROWS}, ctx=ctx)
        self.assertEqual(out["reasons"], ["order_tiebreaker_missing"])

    def test_retry_uses_feedback(self):
        prompts = []

        def solver(prompt, seed, temperature):
            prompts.append(prompt)
            return ("DELETE FROM orders" if len(prompts) == 1 else Q), {}
        out = rv.review_draft(make_ctx(), [FakeDataset("enterprise/base", {Q: ROWS})], solver, 1, 1)
        self.assertEqual(out["status"], "approved")
        self.assertIn("PREVIOUS ATTEMPT WAS REJECTED", prompts[1])
        self.assertNotIn("PREVIOUS ATTEMPT", prompts[0])


class Prompt(unittest.TestCase):
    def test_prompt_hides_everything_but_question_and_schema(self):
        prompt = rv.build_solver_prompt(make_ctx(schema_text="public.orders\n  - order_id: integer NOT NULL"))
        self.assertIn("ALLOWED TABLES", prompt)
        self.assertIn("Liệt kê đơn hàng", prompt)
        self.assertNotIn("difficulty", prompt.lower().replace("difficulty_", ""))


if __name__ == "__main__":
    unittest.main()
