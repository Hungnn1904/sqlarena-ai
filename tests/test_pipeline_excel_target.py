import unittest

from pipeline import load_excel_target


class ExcelTargetTests(unittest.TestCase):
    def test_null_preserving_join_maps_to_left_join(self):
        schema, difficulty, topic, row = load_excel_target(
            "Master_SQL_Dataset_All_Sources_2_1.xlsx", "LC-SQL-0175"
        )

        self.assertEqual(row["id"], "LC-SQL-0175")
        self.assertEqual(difficulty, "easy")
        self.assertEqual(topic, "JOIN_LEFT")
        self.assertEqual(list(schema["tables"]), ["Person", "Address"])

    def test_top_three_per_group_maps_to_window_function(self):
        schema, difficulty, topic, row = load_excel_target(
            "Master_SQL_Dataset_All_Sources_2_1.xlsx", "LC-SQL-0185"
        )

        self.assertEqual(row["id"], "LC-SQL-0185")
        self.assertEqual(difficulty, "hard")
        self.assertEqual(topic, "WINDOW_FUNCTION")
        self.assertEqual(list(schema["tables"]), ["Employee", "Department"])


if __name__ == "__main__":
    unittest.main()
