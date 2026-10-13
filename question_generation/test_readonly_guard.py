"""Focused checks for the validator boundary. No database connection."""
import unittest
from db_readonly import check_sql
from question_specs import SQL


class ReadOnlyGuardTests(unittest.TestCase):
    def test_all_curated_questions_are_accepted(self):
        for n,sql in SQL.items():
            with self.subTest(question=n):
                check_sql(sql)

    def test_mutations_and_side_effects_are_rejected(self):
        for sql in [
            'DELETE FROM orders', 'SELECT 1; DELETE FROM orders;',
            'WITH gone AS (DELETE FROM orders RETURNING *) SELECT * FROM gone',
            "SELECT nextval('orders_order_id_seq')", "SELECT pg_read_file('secret')",
            'SELECT public.sum(amount) FROM payments', 'SELECT 1 INTO unexpected',
            'SELECT * FROM orders FOR UPDATE', 'SELECT 1 -- comment',
            'SELECT 1 /* comment */', 'SELECT 1\n\\gexec',
            "SELECT set_config('transaction_read_only','off',true)",
        ]:
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):
                    check_sql(sql)

    def test_literals_are_not_mistaken_for_operations(self):
        check_sql("SELECT 'DELETE; UPDATE -- literal' AS label")


if __name__=='__main__':
    unittest.main()
