import unittest

from novelty_checker import check_novelty


class NoveltyCheckerTests(unittest.TestCase):
    SOURCE = (
        "Write a solution to report the first name, last name, city, and state of each "
        "person. If an address is not present, report null instead."
    )

    def test_rejects_close_paraphrase(self):
        result = check_novelty(
            "Show the first name, last name, city, and state of each person. "
            "If an address is not present, report null instead.",
            self.SOURCE,
        )

        self.assertFalse(result["is_novel"])

    def test_accepts_different_analytical_goal(self):
        result = check_novelty(
            "Find the IDs of people who do not have any recorded address.",
            self.SOURCE,
        )

        self.assertTrue(result["is_novel"])


if __name__ == "__main__":
    unittest.main()
