import unittest

from excel_schema_sync import build_generated_schema, parse_database_schema, schema_from_excel_row
from schema_loader import generate_seed


class ExcelSchemaSyncTests(unittest.TestCase):
    def test_parses_multiple_tables_and_normalizes_types(self):
        tables = parse_database_schema(
            "Person (personId int, lastName varchar) | "
            "Address (addressId int, personId bigint, city text)"
        )

        self.assertEqual(tables[0]["name"], "Person")
        self.assertEqual(tables[0]["columns"][0], {"name": "personId", "type": "INTEGER"})
        self.assertEqual(tables[1]["columns"][2], {"name": "city", "type": "VARCHAR"})

    def test_parses_types_with_parameters(self):
        tables = parse_database_schema(
            "CITY (ID NUMBER, NAME VARCHAR2(17), AMOUNT DECIMAL(10,2))"
        )

        self.assertEqual(
            tables[0]["columns"],
            [
                {"name": "ID", "type": "DECIMAL"},
                {"name": "NAME", "type": "VARCHAR"},
                {"name": "AMOUNT", "type": "DECIMAL"},
            ],
        )

    def test_merges_case_insensitively_but_keeps_different_id_names(self):
        rows = [
            {"id": 1, "excel_row": 2, "database_schema": "Employee (id int, salary int)"},
            {
                "id": 2,
                "excel_row": 3,
                "database_schema": "employee (id1 bigint, id2 int, salary decimal)",
            },
        ]

        schema, report = build_generated_schema(rows)

        self.assertEqual(list(schema["tables"]), ["Employee"])
        self.assertEqual(
            list(schema["tables"]["Employee"]["columns"]), ["id", "salary", "id1", "id2"]
        )
        self.assertEqual(schema["tables"]["Employee"]["columns"]["salary"], "DECIMAL")
        self.assertEqual(len(report["type_conflicts"]), 1)

    def test_reports_invalid_rows_without_stopping_merge(self):
        rows = [
            {"id": 1, "excel_row": 2, "database_schema": "not a schema"},
            {"id": 2, "excel_row": 3, "database_schema": "Scores (id int, score decimal)"},
        ]

        schema, report = build_generated_schema(rows)

        self.assertIn("Scores", schema["tables"])
        self.assertEqual(report["rows_parsed"], 1)
        self.assertEqual(len(report["parse_errors"]), 1)

    def test_builds_schema_for_one_excel_row(self):
        row = {
            "id": "LC-SQL-0175",
            "excel_row": 2,
            "database_schema": (
                "Person (personId int, lastName varchar, firstName varchar) | "
                "Address (addressId int, personId int, city varchar, state varchar)"
            ),
        }

        schema = schema_from_excel_row(row)

        self.assertEqual(list(schema["tables"]), ["Person", "Address"])

        seed = generate_seed(schema, rows_per_table=3)
        self.assertIn("(1, 'Last 1', 'Name 1')", seed)
        self.assertIn("(1, 2, 'Ha Noi', 'North')", seed)
        self.assertNotIn("'value_1', 'value_1', 'value_1'", seed)


if __name__ == "__main__":
    unittest.main()
