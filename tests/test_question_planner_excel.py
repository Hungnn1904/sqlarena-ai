import json
import unittest

from question_planner import plan_question


class CapturingLLM:
    def __init__(self):
        self.prompt = ""
        self.expect_json = False

    def generate(self, task_type, prompt, expect_json=False):
        self.prompt = prompt
        self.expect_json = expect_json
        return json.dumps(
            {
                "intent": "List every person and include null address fields when missing.",
                "target_skill": "JOIN_LEFT",
                "schema_tables": ["Person", "Address"],
                "trap_strategy": "Using INNER JOIN would remove people without addresses.",
                "ambiguity_risk": "low",
                "difficulty": "easy",
            }
        )


class QuestionPlannerExcelTests(unittest.TestCase):
    def test_source_reference_is_included_in_planner_prompt(self):
        llm = CapturingLLM()
        schema = {
            "tables": {
                "Person": {"columns": {"personId": "INTEGER"}},
                "Address": {"columns": {"personId": "INTEGER", "city": "VARCHAR"}},
            }
        }
        source = {
            "domain": "People and addresses",
            "target_skill": "JOIN_LEFT",
            "required_edge_cases": ["An unmatched person must remain visible"],
        }

        blueprint = plan_question("easy", "JOIN_LEFT", schema, llm, source_context=source)

        self.assertEqual(blueprint.target_skill, "JOIN_LEFT")
        self.assertIn("An unmatched person must remain visible", llm.prompt)
        self.assertIn("do not invent filters", llm.prompt)
        self.assertTrue(llm.expect_json)

    def test_gateway_error_is_reported_before_json_parsing(self):
        class FailingLLM:
            def generate(self, task_type, prompt, expect_json=False):
                return "ERROR: NVIDIA LLM failed after retries"

        schema = {"tables": {"Employee": {"columns": {"id": "INTEGER"}}}}

        with self.assertRaisesRegex(ValueError, "question planning failed"):
            plan_question("hard", "WINDOW_FUNCTION", schema, FailingLLM())


if __name__ == "__main__":
    unittest.main()
