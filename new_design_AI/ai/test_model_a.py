"""Offline checks plus explicit optional read-only integration checks."""

import copy
import json
import sys
import unittest
import tempfile
from pathlib import Path
import urllib.error
from unittest.mock import patch

import main
import validator as v


SCHEMA = {"customers": {"customer_id": "integer", "full_name": "text", "status": "text"},
          "orders": {"order_id": "integer", "customer_id": "integer", "total_amount": "numeric"}}
REFS = [f"ENT-{i:03}" for i in range(1, 6)]
REQUEST = {"count": 1, "difficulty": "easy", "skill": "S1", "domain": "Customer Management",
           "context_tables": ["customers", "orders"], "preferred_tables": [], "extra": "",
           "allowed_domains": ["Customer Management"], "allowed_skills": [f"S{i}" for i in range(1, 7)]}
CANDIDATE = {"title": "Khach hang", "question": "Liet ke ma khach hang theo ma tang dan.",
             "difficulty": "easy", "primary_skill_group": "S1", "skills": ["S1"],
             "business_domain": "Customer Management", "business_goal": "Danh sach khach hang",
             "difficulty_reason": "Loc truc tiep mot bang.",
             "logic_signature": {"output_grain": "customer", "analysis_goal": "customer roster",
                                 "filter_pattern": "none", "aggregation_pattern": "none"},
             "tables_used": ["customers"], "required_columns": {"customers": ["customer_id"]},
             "reference_sql": "SELECT customer_id FROM customers ORDER BY customer_id",
             "source_question_ids": REFS}


class ValidatorTests(unittest.TestCase):
    def validate(self, candidate=None, corpus=(), status="executed_with_rows", request=None):
        return v.validate(candidate or copy.deepcopy(CANDIDATE), request or REQUEST, SCHEMA, REFS,
                          list(corpus), {}, executor=lambda *_: {
                              "status": status, "row_count": 0 if status == "executed_empty" else 2})

    def test_basic_pass_is_not_semantic_approval(self):
        result = self.validate()
        self.assertTrue(result["passed_basic"])
        self.assertIsNone(result["semantic_valid"])
        self.assertFalse(result["model_b_reviewed"])

    def test_empty_kept(self):
        self.assertTrue(self.validate(status="executed_empty")["passed_basic"])

    def test_not_run_kept_with_warning(self):
        self.assertTrue(self.validate(status="not_run")["passed_basic"])
        self.assertEqual(v.execute_readonly("SELECT 1", {"user": ""}, SCHEMA)["status"], "not_run")

    def test_execution_error_timeout_rejected(self):
        for status in ("execution_error", "timeout"):
            self.assertFalse(self.validate(status=status)["passed_basic"])

    def test_required_json(self):
        for key in CANDIDATE:
            value = copy.deepcopy(CANDIDATE)
            value.pop(key)
            self.assertFalse(self.validate(value)["passed_basic"], key)

    def test_unsafe_sql(self):
        queries = ["SELECT 1; SELECT 2", "DELETE FROM customers", "SELECT * INTO x FROM customers",
                   "WITH d AS (DELETE FROM customers RETURNING *) SELECT * FROM d",
                   "SELECT pg_sleep(1)", "SELECT nextval('x')", "SELECT set_config('x','y',false)",
                   "SELECT public.count(customer_id) FROM customers", "SELECT * FROM pg_catalog.pg_authid",
                   "SELECT customer_id FROM customers FOR UPDATE", "COPY customers TO PROGRAM 'x'",
                   "SELECT 'x'::regclass", "SELECT dblink('x','y')", "SELECT lo_import('x')"]
        for sql in queries:
            candidate = copy.deepcopy(CANDIDATE)
            candidate["reference_sql"] = sql
            self.assertFalse(self.validate(candidate)["passed_basic"], sql)

    def test_metadata_not_trusted(self):
        for sql in ("SELECT nonexistent FROM customers", "SELECT c.bad FROM customers c",
                    "SELECT c.customer_id FROM orders c", "SELECT * FROM invented",
                    "SELECT customer_id FROM customers c JOIN orders o ON c.customer_id=o.customer_id"):
            candidate = copy.deepcopy(CANDIDATE)
            candidate["reference_sql"] = sql
            self.assertFalse(self.validate(candidate)["passed_basic"], sql)

    def test_cte_subquery_correlated_and_union_scope(self):
        queries = ["WITH x AS (SELECT customer_id AS id FROM customers) SELECT x.id FROM x ORDER BY id",
                   "SELECT z.id FROM (SELECT customer_id AS id FROM customers) z",
                   "SELECT c.customer_id FROM customers c WHERE EXISTS "
                   "(SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id)",
                   "SELECT customer_id AS id FROM customers UNION ALL SELECT customer_id FROM orders ORDER BY id",
                   "WITH RECURSIVE x(n) AS (SELECT customer_id FROM customers UNION ALL "
                   "SELECT n+1 FROM x WHERE n<5) SELECT n FROM x",
                   "SELECT c.customer_id,count(o.order_id) AS n FROM customers c "
                   "LEFT JOIN orders o USING(customer_id) GROUP BY c.customer_id ORDER BY n"]
        for sql in queries:
            binder = v.SQLSchema(SCHEMA)
            self.assertTrue(binder.query(v.parse_select(sql)), sql)
        for sql in ("WITH x AS (SELECT customer_id AS id FROM customers) SELECT x.customer_id FROM x",
                    "SELECT z.id FROM (SELECT bad AS id FROM customers) z"):
            with self.assertRaises(ValueError):
                v.SQLSchema(SCHEMA).query(v.parse_select(sql))

    def test_mismatch_skill_difficulty_references(self):
        for field, value in (("difficulty", "hard"), ("primary_skill_group", "S6"),
                             ("source_question_ids", ["fake"]), ("business_domain", "Finance")):
            candidate = copy.deepcopy(CANDIDATE)
            candidate[field] = value
            self.assertFalse(self.validate(candidate)["passed_basic"])

    def test_duplicate_exact_and_threshold(self):
        source = {**CANDIDATE, "id": "ENT-001", "origin": "core"}
        self.assertFalse(self.validate(corpus=[source])["passed_basic"])
        candidate = copy.deepcopy(CANDIDATE)
        candidate["question"] = "Khach hang co ma nho hon 500."
        candidate["reference_sql"] = "SELECT customer_id FROM customers WHERE customer_id < 500"
        source["reference_sql"] = "SELECT customer_id FROM customers WHERE customer_id < 10"
        source["logic_signature"] = {}
        result = self.validate(candidate, [source])
        self.assertTrue(result["duplicate"]["logic_duplicate"])

    def test_same_table_is_not_duplicate(self):
        source = {**CANDIDATE, "id": "old", "origin": "draft", "question": "Thong ke khach hang",
                  "logic_signature": {}, "reference_sql": "SELECT count(*) AS n FROM customers"}
        self.assertTrue(self.validate(corpus=[source])["passed_basic"])

    def test_lexical_suspicion_only(self):
        source = {**CANDIDATE, "id": 1, "origin": "draft", "question": CANDIDATE["question"] + " them.",
                  "reference_sql": "SELECT count(*) AS n FROM customers", "logic_signature": {}}
        result = v.detect_duplicate(CANDIDATE, [source], .2, .1)
        self.assertTrue(result["suspected_duplicate"])
        self.assertFalse(result["exact_duplicate"])
        self.assertFalse(result["logic_duplicate"])


class CLITests(unittest.TestCase):
    def test_input_reprompts_and_cancel(self):
        data = {"schema": SCHEMA, "skills": [{"skill_id": "S1", "name": "SELECT"}],
                "sources": [{"primary_business_domain": "Customer Management"}]}
        answers = iter(["bad", "0", "2", "1", "1", "1", "bad", "customers", "", "y"])
        result = main.prompt_input(data, input_fn=lambda _: next(answers), print_fn=lambda _: None)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["preferred_tables"], ["customers"])
        answers = iter(["1", "1", "1", "1", "", "", "n"])
        self.assertIsNone(main.prompt_input(data, lambda _: next(answers), lambda _: None))

    def test_rules_actual_and_missing(self):
        config = main.load_config()
        rules = main.read_rules(config)
        self.assertEqual(set(rules["skills"]), {f"S{i}" for i in range(1, 7)})
        with self.assertRaises(ValueError):
            main.read_rules({**config, "RULES_PATH": "missing.md"})

    def test_real_core_readonly_and_reference_rotation(self):
        config = main.load_config()
        rules = main.read_rules(config)
        data = main.inspect_database(config, rules)
        self.assertEqual(len(data["sources"]), 50)
        self.assertFalse(data["blockers"])
        for difficulty in ("easy", "medium", "hard"):
            request = {**REQUEST, "difficulty": difficulty, "domain": None}
            sets = []
            for index in range(3):
                context, tables, refs = main.build_context(data, rules, request, index)
                self.assertEqual(len(set(refs)), 5)
                self.assertTrue(all(q["difficulty"] == difficulty for q in context["source_references"]))
                self.assertLess(len(tables), 16)
                self.assertNotIn("reference_sql", json.dumps(context["source_references"]))
                sets.append(tuple(refs))
            self.assertGreater(len(set(sets)), 1)

    def test_retry_bounded_without_database_writes(self):
        config = {**main.load_config(), "MAX_RETRIES": 1}
        data = {"schema": SCHEMA, "sources": [], "drafts": []}
        context = {"world_schema": {}, "source_references": [{"source_id": r} for r in REFS],
                   "user_request": REQUEST}
        session = {}
        with patch.object(main, "fingerprint", return_value={}), \
             patch.object(main, "checkpoint"), \
             patch.object(main, "build_context", return_value=(context, ["customers"], REFS)), \
             patch.object(main, "generate", side_effect=ValueError("bad JSON")) as generate, \
             patch.object(main, "insert_draft") as insert, patch("builtins.print"):
            session = main.run_session(config, data, {"path": "mock", "sha256": "mock"}, REQUEST,
                                       main.HERE / "outputs" / "mock.json")
        self.assertEqual(generate.call_count, 2)
        insert.assert_not_called()
        self.assertEqual(len(session["successes"]), 0)
        self.assertEqual(len(session["failures"]), 1)
        self.assertEqual(session["status"], "partial")

    def test_output_unique_and_complete(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(main, "HERE", Path(folder)):
            first, second = main.create_output(), main.create_output()
            self.assertNotEqual(first, second)
            main.checkpoint(first, {"status": "completed", "successes": [{"draft_id": 123}]})
            self.assertEqual(json.loads(first.read_text())["successes"][0]["draft_id"], 123)
            self.assertEqual(second.read_text().strip(), "{}")

    def test_superuser_execution_is_blocked_before_ai_sql(self):
        config = main.load_config()
        with main.connect(config, "CATALOG") as conn:
            with self.assertRaises(ValueError):
                v.verify_readonly(conn, SCHEMA)

    def test_ollama_missing_model_and_invalid_json(self):
        config = main.load_config()
        with patch.object(main, "ollama_request", return_value={"models": []}):
            with self.assertRaisesRegex(ValueError, "ollama pull"):
                main.check_ollama(config)
        for response in ({"response": "not JSON"}, {"response": "[]"},
                         {"response": "{}", "done_reason": "length"},
                         {"response": "{}", "prompt_eval_count": config["OLLAMA_CONTEXT_SIZE"]}):
            with patch.object(main, "ollama_request", return_value=response):
                with self.assertRaises(ValueError):
                    main.generate(config, "test")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaisesRegex(ValueError, "ollama serve"):
                main.ollama_request(config, "/api/tags")

    def test_insert_mapping_commits_pending_only(self):
        from unittest.mock import MagicMock
        config = main.load_config()
        database = MagicMock()
        database.__enter__.return_value = database
        database.execute.return_value.fetchone.return_value = {"draft_id": 9}
        with patch.object(main, "connect", return_value=database):
            identifier = main.insert_draft(config, {"world": {"world_id": "enterprise_v1"}}, CANDIDATE,
                {"passed_basic": True}, {"world_schema": {"tables": [{"table": "customers", "columns": [
                    {"name": "customer_id", "type": "integer", "nullable": False}]}]}, "rules_source": {}}, REFS, 0)
        self.assertEqual(identifier, 9)
        values = database.execute.call_args.args[1]
        self.assertEqual(values[main.DRAFT_FIELDS.index("status")], "pending")
        self.assertNotIn("reference_sql", main.DRAFT_FIELDS)
        self.assertEqual(values[main.DRAFT_FIELDS.index("compare_mode")], "unordered")
        self.assertEqual(values[main.DRAFT_FIELDS.index("schema_text")], "public.customers\n  - customer_id: integer NOT NULL")
        self.assertEqual(values[main.DRAFT_FIELDS.index("parent_ids")].obj, REFS)
        self.assertEqual(values[main.DRAFT_FIELDS.index("depth")], 1)
        database.__exit__.assert_called_once()

    def test_insert_failure_not_reported_success_or_retried(self):
        import psycopg
        config = {**main.load_config(), "MAX_RETRIES": 2}
        data = {"schema": SCHEMA, "sources": [], "drafts": [], "blockers": []}
        report = {"passed_basic": True, "errors": [], "execution": {"status": "not_run"}}
        context = {"world_schema": {}, "source_references": [{"source_id": r} for r in REFS],
                   "user_request": REQUEST}
        with patch.object(main, "fingerprint", return_value={}), patch.object(main, "checkpoint"), \
             patch.object(main, "build_context", return_value=(context, ["customers"], REFS)), \
             patch.object(main, "inspect_database", return_value=data), \
             patch.object(main, "generate", return_value=CANDIDATE) as generate, \
             patch.object(main, "validate_question", return_value=report), \
             patch.object(main, "insert_draft", side_effect=psycopg.OperationalError("lost connection")) as insert, \
             patch("builtins.print"):
            session = main.run_session(config, data, {"path": "mock", "sha256": "mock"}, REQUEST,
                                       main.HERE / "outputs" / "mock.json")
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(insert.call_count, 1)
        self.assertEqual(len(session["successes"]), 0)
        self.assertIn("insert_error", session["failures"][0]["attempts"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
