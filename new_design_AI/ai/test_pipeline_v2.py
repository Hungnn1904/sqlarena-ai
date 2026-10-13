"""Tests for the v2 pipeline changes (feasibility, blueprint, derived metadata, actionable retry).
Offline only: no database, no Ollama. Run: python -m unittest discover -s ai -p "test_*.py" -v"""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import validator as v
from test_model_a import CANDIDATE, REFS, REQUEST, SCHEMA

RULES_FILE = "question_create/enterprise_50_question_rules_v1.md"


def world_fixture():
    cols = lambda *names: [{"name": n, "postgres_type": "text", "nullable": False} for n in names]
    tables = [{"table": "customers", "columns": cols("customer_id", "full_name", "status"),
               "primary_key": ["customer_id"], "constraints": []},
              {"table": "orders", "columns": cols("order_id", "customer_id", "total_amount", "status"),
               "primary_key": ["order_id"], "constraints": []},
              {"table": "refunds", "columns": cols("refund_id", "order_id", "amount"),
               "primary_key": ["refund_id"], "constraints": []}]
    fks = [{"table_name": "orders", "referenced_table": "customers"},
           {"table_name": "refunds", "referenced_table": "orders"}]
    schema = {t["table"]: {c["name"]: "text" for c in t["columns"]} for t in tables}
    sources = [{"question_id": f"ENT-{i:03}", "title": f"t{i}", "difficulty": "easy", "primary_skill_group": "S1",
                "primary_business_domain": "Customer Management",
                "metadata": {"tables_used": ["customers", "orders"] if i == 1 else ["customers"],
                             "business_goal": f"goal {i}", "output_grain": "row", "logic_signature": {}}}
               for i in range(1, 7)]
    world = {"dialect": "postgresql", "fk_relations": fks, "allowed_sql_features": ["select"],
             "schema_description": {"tables": tables},
             "business_rules": {"rules": [], "precedence": "p", "alignment_notes": "n"}}
    return {"world": world, "schema": schema, "sources": sources}


RULES = {"definitions": {"easy": "E", "medium": "M", "hard": "H"}, "principle": "P",
         "classification": "- S1: loc truc tiep\n- S2: noi bang", "quality": "Q", "path": "p", "sha256": "x"}


class FeasibilityTests(unittest.TestCase):
    def test_actual_rules_matrix_makes_s1_easy_only(self):
        rules = main.read_rules({"RULES_PATH": RULES_FILE})
        pairs = main.feasible_pairs(rules)
        self.assertEqual(pairs["S1"], {"easy"})
        self.assertEqual(pairs["S6"], {"hard"})
        with self.assertRaises(ValueError):
            main.check_feasible(rules, {"skill": "S1", "difficulty": "medium"})
        main.check_feasible(rules, {"skill": "S3", "difficulty": "medium"})

    def test_menu_hides_skills_not_defined_for_difficulty(self):
        data = {"schema": SCHEMA, "sources": [{"primary_business_domain": "Customer Management"}],
                "skills": [{"skill_id": "S1", "name": "SELECT"}, {"skill_id": "S3", "name": "GROUP BY"}]}
        feasible = {"S1": {"easy"}, "S3": {"easy", "medium"}}
        shown = []
        # difficulty=2 (medium); skill menu must contain only S3, so "1" selects S3.
        answers = iter(["1", "2", "1", "1", "", "", "y"])
        result = main.prompt_input(data, lambda _: next(answers), shown.append, feasible=feasible)
        self.assertEqual(result["skill"], "S3")
        self.assertFalse(any("S1 - SELECT" in line for line in shown))


class BlueprintTests(unittest.TestCase):
    def test_topic_context_is_not_limited_to_source_question_tables(self):
        data = world_fixture()
        base = {"difficulty": "easy", "domain": None, "preferred_tables": [], "extra": ""}
        for index in range(4):
            self.assertGreaterEqual(len(main.select_tables(data, {**base, "skill": "S1"}, index)), 2)
        data["sources"] = [{**q, "primary_skill_group": "S2", "metadata": {**q["metadata"], "tables_used": ["customers"]}}
                           for q in data["sources"]]
        self.assertGreaterEqual(len(main.select_tables(data, {**base, "skill": "S2"}, 0)), 2)

    def test_prompt_states_contract_and_asks_for_question_metadata_only(self):
        data = world_fixture()
        request = {"count": 1, "difficulty": "easy", "skill": "S1", "domain": None, "preferred_tables": [],
                   "extra": "", "allowed_domains": ["Customer Management"], "allowed_skills": ["S1"]}
        context, tables, refs = main.build_context(data, RULES, request, 0)
        prompt = main.build_prompt({**context, "user_request": {**request, "context_tables": tables}},
                                   ["FIX: use one table"])
        self.assertIn("FORBIDDEN: JOIN", prompt)
        self.assertIn("ALLOWED TABLES", prompt)
        self.assertIn("Do not write an SQL answer", prompt)
        self.assertIn("FIX: use one table", prompt)
        self.assertNotIn("Rejected prior goal", prompt)
        self.assertEqual(prompt.count("OUTPUT OBJECT"), 1)
        fields = json.loads(prompt.split("OUTPUT OBJECT (replace placeholders):\n")[1])
        self.assertIn("tables_used", fields)
        self.assertIn("required_columns", fields)
        self.assertIn("output_columns", fields)
        self.assertNotIn("reference_sql", fields)

    def test_prompt_tolerates_minimal_context(self):
        prompt = main.build_prompt({"world_schema": {}, "source_references": [{"source_id": r} for r in REFS],
                                    "user_request": REQUEST}, [])
        self.assertIn("customers", prompt)


class NormalizationTests(unittest.TestCase):
    def test_does_not_mutate_and_sets_references_from_code(self):
        raw = copy.deepcopy(CANDIDATE)
        raw.pop("source_question_ids")
        before = copy.deepcopy(raw)
        candidate, note = main.normalize_candidate(raw, SCHEMA, REFS, ["customers", "orders"])
        self.assertEqual(raw, before)
        self.assertEqual(candidate["source_question_ids"], REFS)
        self.assertIn("source_question_ids", note["set_by_code"])

    def test_missing_column_metadata_is_not_invented(self):
        raw = {k: val for k, val in CANDIDATE.items() if k not in {"reference_sql", "required_columns"}}
        candidate, note = main.normalize_candidate(raw, SCHEMA, REFS, ["customers"])
        self.assertFalse(note["derived_from_sql"])
        self.assertNotIn("required_columns", candidate)

    def test_model_declaration_is_preserved_and_invalid_columns_rejected(self):
        raw = {**CANDIDATE, "tables_used": ["orders"], "required_columns": {"orders": ["x"]}, "output_columns": ["order_id"]}
        raw.pop("reference_sql")
        candidate, note = main.normalize_candidate(raw, SCHEMA, REFS, ["customers"])
        self.assertEqual(candidate["tables_used"], ["orders"])
        self.assertEqual(note["declared_by_model"]["tables_used"], ["orders"])
        self.assertFalse(v.validate_question(candidate, REQUEST, SCHEMA, REFS, [])["passed_basic"])

    def test_derive_from_real_ast(self):  # needs pglast (real run on the user's machine)
        tables, columns = v.derive_sql_metadata(
            "SELECT customer_id FROM customers ORDER BY customer_id", SCHEMA)
        self.assertEqual(tables, ["customers"])
        self.assertIn("customer_id", columns["customers"])
        self.assertIsNone(v.derive_sql_metadata("SELECT nope FROM customers", SCHEMA))


class FeedbackTests(unittest.TestCase):
    def test_hints_are_actionable_and_mention_allowed_tables(self):
        lines = v.repair_hints(["schema: Bang ngoai context/schema: order_items",
                                "metadata: S1 khong phai trong tam loc/chon truc tiep (dang dung: aggregate)."],
                               {"context_tables": ["orders"]})
        text = "\n".join(lines)
        self.assertIn("FIX:", text)
        self.assertIn("Allowed tables are exactly: orders", text)
        self.assertIn("WITHOUT JOIN", text)

    def test_retry_gets_fix_lines_and_tried_goals_not_priming(self):
        prompts = []
        report = {"passed_basic": False, "execution": {"status": "not_run"},
                  "errors": ["metadata: S1 khong phai trong tam loc/chon truc tiep (dang dung: aggregate)."]}
        config = {**{"MAX_RETRIES": 2, "MODEL_NAME": "m", "OLLAMA_HOST": "h", "STATEMENT_TIMEOUT_MS": 1,
                     "DUPLICATE_HIGH": .85, "DUPLICATE_REVIEW": .65, "MAX_RESULT_ROWS": 1, "ENTERPRISE_DB_USER": ""}}
        context = {"world_schema": {"tables": [{"table": "customers", "columns": [{"name": "status"}, {"name": "full_name"}]}]},
                   "source_references": [{"source_id": r} for r in REFS], "user_request": REQUEST}
        data = {"schema": SCHEMA, "sources": [], "drafts": []}

        def fake_generate(config, prompt, smoke=False):
            prompts.append(prompt)
            return copy.deepcopy(CANDIDATE)
        with patch.object(main, "fingerprint", return_value={}), patch.object(main, "checkpoint"), \
             patch.object(main, "build_context", return_value=(context, ["customers"], REFS)), \
             patch.object(main, "generate", side_effect=fake_generate), \
             patch.object(main, "validate_question", return_value=report), patch.object(main, "insert_draft") as insert, \
             patch.object(main, "connection_config", return_value={}), patch("builtins.print"):
            session = main.run_session(config, data, {"path": "mock", "sha256": "mock"}, REQUEST,
                                       main.HERE / "outputs" / "mock.json")
        insert.assert_not_called()
        self.assertEqual(len(prompts), 3)
        self.assertNotIn("PREVIOUS ATTEMPT FAILED", prompts[0])
        self.assertIn("FIX:", prompts[1])
        self.assertIn("Goals already tried", prompts[1])
        self.assertIn("Suggested new focus columns", prompts[1])
        self.assertNotIn("Rejected prior goal", prompts[2])
        self.assertEqual(session["status"], "partial")


if __name__ == "__main__":
    unittest.main(verbosity=2)
