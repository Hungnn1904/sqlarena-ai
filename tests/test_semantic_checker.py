import unittest

from semantic_checker import check_semantic_consistency


class SemanticCheckerTests(unittest.TestCase):
    def test_rejects_empty_output_and_missing_question_literal(self):
        result = check_semantic_consistency(
            question_text="Find employees in the 'Sales' department.",
            answer_sql="SELECT name FROM Employee",
            seed_sql="INSERT INTO Department VALUES (1, 'Engineering');",
            topic="WHERE_FILTER",
            output=[],
        )

        self.assertFalse(result["is_consistent"])
        self.assertEqual(len(result["issues"]), 2)

    def test_window_topic_requires_ranking_window_function(self):
        invalid = check_semantic_consistency(
            "List employees", "SELECT * FROM Employee", "", "WINDOW_FUNCTION", [{"id": 1}]
        )
        valid = check_semantic_consistency(
            "Rank employees",
            "SELECT DENSE_RANK() OVER (ORDER BY salary DESC) AS position FROM Employee",
            "",
            "WINDOW_FUNCTION",
            [{"position": 1}],
        )

        self.assertFalse(invalid["is_consistent"])
        self.assertTrue(valid["is_consistent"])


if __name__ == "__main__":
    unittest.main()
