"""Question-only regressions for the New folder v2 project."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import validator as v
from test_model_a import CANDIDATE, REQUEST, REFS, SCHEMA

QUESTION = {**{k: val for k, val in CANDIDATE.items() if k != "reference_sql"},
            "output_columns": ["customer_id"]}
WORLD = {"tables": [{"table": name, "columns": [{"name": c, "type": kind, "nullable": False}
          for c, kind in cols.items()]} for name, cols in SCHEMA.items()]}


class QuestionOnlyTests(unittest.TestCase):
    def test_valid_question_not_semantic_pass(self):
        report = v.validate_question(QUESTION, REQUEST, SCHEMA, REFS, [])
        self.assertTrue(report["passed_basic"])
        self.assertEqual(report["execution"]["status"], "not_applicable")
        self.assertEqual(report["review_disposition"], "NEEDS_HUMAN")
        self.assertIsNone(report["semantic_valid"])

    def test_reject_answers_missing_fields_and_hallucinated_metadata(self):
        for changes in ({"reference_sql": "SELECT 1"}, {"extra": {"answer": "SELECT 1"}},
                        {"question": "SELECT customer_id FROM customers"},
                        {"required_columns": {"customers": ["fake"]}}, {"tables_used": ["fake"]},
                        {"required_columns": {}}, {"difficulty": "hard"}, {"source_question_ids": ["fake"]}):
            with self.subTest(changes=changes):
                self.assertFalse(v.validate_question({**QUESTION, **changes}, REQUEST, SCHEMA, REFS, [])["passed_basic"])

    def test_old_drafts_without_reference_and_duplicates_without_sql(self):
        corpus = main.corpus_from({"sources": [], "drafts": [{"draft_id": 10, "question": QUESTION["question"],
            "validation_report": {"candidate_metadata": QUESTION}}]})
        self.assertNotIn("reference_sql", corpus[0])
        self.assertFalse(v.validate_question(QUESTION, REQUEST, SCHEMA, REFS, corpus)["passed_basic"])

    def test_schema_text_only_question_tables(self):
        text = main.render_schema_text(WORLD, ["orders"])
        self.assertIn("public.orders", text)
        self.assertIn("order_id: integer NOT NULL", text)
        self.assertNotIn("public.customers", text)

    def test_single_generation_call_no_answer_execution_no_dry_run_insert(self):
        config = main.load_config()
        data = {"schema": SCHEMA, "sources": [], "drafts": [], "blockers": []}
        context = {"world_schema": WORLD, "rules_source": {}, "user_request": REQUEST}
        with patch.object(main, "fingerprint", return_value={}), patch.object(main, "checkpoint"), \
             patch.object(main, "build_context", return_value=(context, ["customers"], REFS)), \
             patch.object(main, "inspect_database", return_value=data), \
             patch.object(main, "generate", return_value=copy.deepcopy(QUESTION)) as generate, \
             patch.object(v, "execute_readonly", side_effect=AssertionError("No answer execution")), \
             patch.object(main, "insert_draft") as insert, patch("builtins.print"):
            session = main.run_session(config, data, {"path": "mock", "sha256": "mock"}, REQUEST,
                                       Path("unused.json"), dry_run=True)
        self.assertEqual(generate.call_count, 1)
        insert.assert_not_called()
        self.assertEqual(session["status"], "completed")
        self.assertEqual(session["saved_count"], 0)
        self.assertNotIn("reference_sql", session["successes"][0]["candidate"])
        self.assertIn("public.customers", session["successes"][0]["schema_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
