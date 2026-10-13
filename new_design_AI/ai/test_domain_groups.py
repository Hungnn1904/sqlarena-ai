"""Topic group planning, real FK evidence, explicit business-dependency guards."""
import copy
import json
import unittest
from unittest.mock import patch

import main
import context_policy as policy
import validator as v
from test_question_only import QUESTION
from test_model_a import REFS


class DomainGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = main.load_config()
        cls.rules = main.read_rules(cls.config)
        cls.data = main.inspect_database(cls.config, cls.rules)
        cls.request = {"count": 5, "difficulty": "medium", "skill": "S2", "domain": "Finance",
                       "preferred_tables": [], "extra": "", "allowed_domains": sorted(policy.DOMAIN_GROUPS),
                       "allowed_skills": [f"S{i}" for i in range(1, 7)]}

    def group_request(self, index=0, **changes):
        request = {**self.request, **changes}
        context, tables, refs = main.build_context(self.data, self.rules, request, index)
        local = {**request, "context_tables": tables, "context_group": context["world_schema"]["context_group"],
                 "fk_relations": context["world_schema"]["fk_relations"]}
        return context, local, refs

    def payment_question(self):
        return {**copy.deepcopy(QUESTION), "question": "Voi moi thanh toan thanh cong co hoan tien, "
                "tra payment_id va tong refund_amount cua cac hoan tien completed.",
                "business_goal": "Hoan tien hoan tat theo thanh toan thanh cong", "business_domain": "Finance",
                "difficulty": "medium", "primary_skill_group": "S3", "skills": ["S3"],
                "tables_used": ["payments", "refunds"],
                "required_columns": {"payments": ["payment_id", "payment_status"],
                                     "refunds": ["payment_id", "refund_amount", "refund_status"]},
                "output_columns": ["payment_id", "total_refund"],
                "table_roles": {"payments": "Select successful payment IDs", "refunds": "Sum completed refunds"},
                "join_relations": [{"table_name": "refunds", "columns": ["payment_id"],
                                    "referenced_table": "payments", "referenced_columns": ["payment_id"]}],
                "logic_signature": {"analysis_goal": "completed refunds of successful attempts",
                                    "output_grain": "payment", "filter_pattern": "successful and completed",
                                    "aggregation_pattern": "sum refunds"}}

    def test_all_topic_groups_are_fk_connected_on_actual_enterprise_schema(self):
        for domain, groups in policy.DOMAIN_GROUPS.items():
            for name, tables, primary, _ in groups:
                with self.subTest(group=name):
                    self.assertTrue(set(tables).issubset(self.data["schema"]))
                    self.assertTrue(set(primary).issubset(tables))
                    self.assertTrue(policy.connected_tables(tables, self.data["world"]["fk_relations"]))

    def test_finance_rotates_payment_and_expense_groups_without_warehouse_scope(self):
        groups = [self.group_request(i)[1]["context_group"] for i in range(4)]
        self.assertEqual([g["id"] for g in groups], ["payment_refunds", "operating_costs"] * 2)
        self.assertTrue(all(g["min_tables"] == 2 and "warehouses" not in g["tables"] for g in groups))

    def test_unrestricted_rotates_all_topics_not_all_sixteen_tables(self):
        groups = [self.group_request(i, domain=None)[1]["context_group"] for i in range(5)]
        self.assertEqual({g["domain"] for g in groups}, set(policy.DOMAIN_GROUPS))
        self.assertTrue(all(2 <= len(g["tables"]) <= 5 for g in groups))

    def test_preferences_keep_chosen_topic_and_expand_to_connected_group(self):
        _, local, _ = self.group_request(preferred_tables=["refunds"])
        self.assertIn("payments", local["context_tables"])
        with self.assertRaises(ValueError):
            self.group_request(preferred_tables=["warehouses"])

    def test_medium_s3_has_multitable_policy_but_s1_still_declares_one(self):
        _, local, _ = self.group_request(skill="S3")
        self.assertEqual(local["context_group"]["min_tables"], 2)
        _, local, _ = self.group_request(skill="S1", difficulty="easy")
        self.assertEqual(local["context_group"]["max_tables"], 1)
        self.assertGreaterEqual(len(local["context_tables"]), 2)

    def test_references_remain_five_same_difficulty_and_out_of_scope_goals_not_sent(self):
        context, local, refs = self.group_request()
        self.assertEqual(len(set(refs)), 5)
        self.assertTrue(all(q["difficulty"] == "medium" for q in context["source_references"]))
        prompt = main.build_prompt(context, [])
        self.assertIn('"context_group"', prompt)
        self.assertIn('"fk_relations"', prompt)
        self.assertIn('"join_relations"', prompt)
        self.assertNotIn("INSERT INTO br_validation_violations", prompt)
        for q in context["source_references"]:
            if not q["scope_compatible"]:
                self.assertNotIn(q.get("business_goal_to_avoid", "never-match"), prompt)

    def test_valid_multitable_question_is_still_needs_human(self):
        _, local, refs = self.group_request(skill="S3")
        candidate = {**self.payment_question(), "source_question_ids": refs}
        report = v.validate_question(candidate, local, self.data["schema"], refs, [])
        self.assertTrue(report["passed_basic"], report["errors"])
        self.assertEqual(report["review_disposition"], "NEEDS_HUMAN")
        self.assertIsNone(report["semantic_valid"])

    def test_reject_single_table_medium_even_when_all_columns_exist(self):
        _, local, refs = self.group_request(skill="S3")
        candidate = {**self.payment_question(), "source_question_ids": refs, "question": "Tong tien hoan tat.",
                     "tables_used": ["refunds"], "required_columns": {"refunds": ["refund_amount"]},
                     "table_roles": {"refunds": "refund amount"}, "join_relations": []}
        report = v.validate_question(candidate, local, self.data["schema"], refs, [])
        self.assertFalse(report["passed_basic"])
        self.assertTrue(any("generation policy" in error for error in report["errors"]))

    def test_fake_fk_missing_join_key_extra_role_and_unused_join_are_rejected(self):
        _, local, refs = self.group_request(skill="S3")
        base = {**self.payment_question(), "source_question_ids": refs}
        variations = [
            {"join_relations": [{"table_name": "refunds", "columns": ["refund_id"],
                                 "referenced_table": "payments", "referenced_columns": ["payment_id"]}]},
            {"join_relations": []}, {"table_roles": {"payments": "filter"}},
            {"required_columns": {"payments": ["payment_status"], "refunds": ["payment_id", "refund_amount"]}},
            {"business_domain": "Human Resources"},
        ]
        for change in variations:
            with self.subTest(change=change):
                self.assertFalse(v.validate_question({**base, **change}, local, self.data["schema"], refs, [])["passed_basic"])

    def test_reverse_join_direction_uses_same_real_fk_not_fake_relationship(self):
        _, local, refs = self.group_request(skill="S3")
        candidate = {**self.payment_question(), "source_question_ids": refs,
            "join_relations": [{"table_name": "payments", "columns": ["payment_id"],
                                "referenced_table": "refunds", "referenced_columns": ["payment_id"]}]}
        report = v.validate_question(candidate, local, self.data["schema"], refs, [])
        self.assertTrue(report["passed_basic"], report["errors"])

    def test_delivery_and_payment_conditions_require_actual_status_columns(self):
        candidate = {**self.payment_question(), "question": "Khach hang co don hang da nhan hang va da thanh toan",
            "tables_used": ["orders", "payments"], "required_columns": {
                "orders": ["order_id", "customer_id"], "payments": ["payment_id", "order_id"]}}
        with self.assertRaises(ValueError):
            policy.check_question_dependencies(candidate, self.data["schema"])
        candidate["required_columns"]["payments"].append("payment_status")
        with self.assertRaises(ValueError):
            policy.check_question_dependencies(candidate, self.data["schema"])
        candidate["required_columns"]["orders"].append("status")
        self.assertIsInstance(policy.check_question_dependencies(candidate, self.data["schema"]), dict)

    def test_normalization_adds_only_proven_fk_keys_and_preserves_declared_metadata(self):
        _, local, refs = self.group_request(skill="S3")
        raw = self.payment_question()
        raw["required_columns"]["payments"].remove("payment_id")
        before = copy.deepcopy(raw)
        candidate, note = main.normalize_candidate(raw, self.data["schema"], refs,
            local["context_tables"], local["fk_relations"])
        self.assertEqual(raw, before)
        self.assertIn("payment_id", candidate["required_columns"]["payments"])
        self.assertEqual(note["join_keys_added_by_code"], {"payments": ["payment_id"]})
        raw["join_relations"][0]["columns"] = ["invented"]
        candidate, note = main.normalize_candidate(raw, self.data["schema"], refs,
            local["context_tables"], local["fk_relations"])
        self.assertEqual(note["join_keys_added_by_code"], {})
        self.assertNotIn("payment_id", candidate["required_columns"]["payments"])

    def test_ollama_receives_required_question_schema_not_unconstrained_json(self):
        with patch.object(main, "ollama_request", return_value={"response": "{}"}) as request:
            main.generate(self.config, "question probe")
        schema = request.call_args.args[2]["format"]
        self.assertIn("title", schema["required"])
        self.assertIn("question", schema["required"])
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("reference_sql", schema["properties"])

    def test_default_address_condition_requires_default_flag(self):
        candidate = {**self.payment_question(), "question": "Khach hang co dia chi mac dinh",
            "tables_used": ["customers", "customer_addresses"],
            "required_columns": {"customers": ["customer_id"], "customer_addresses": ["customer_id", "city"]}}
        with self.assertRaises(ValueError):
            policy.check_question_dependencies(candidate, self.data["schema"])
        candidate["required_columns"]["customer_addresses"].append("is_default")
        self.assertIsInstance(policy.check_question_dependencies(candidate, self.data["schema"]), dict)

    def test_expense_total_requires_amount_and_ambiguous_success_is_review_warning(self):
        candidate = {**self.payment_question(), "question": "Tong hop chi phi theo thang", "tables_used": ["operating_expenses"],
                     "required_columns": {"operating_expenses": ["expense_id", "expense_date"]}}
        with self.assertRaises(ValueError):
            policy.check_question_dependencies(candidate, self.data["schema"])
        candidate["required_columns"]["operating_expenses"].append("amount")
        self.assertIsInstance(policy.check_question_dependencies(candidate, self.data["schema"]), dict)
        candidate = {**self.payment_question(), "question": "Khach hang co don hang thanh cong", "tables_used": ["orders"],
                     "required_columns": {"orders": ["order_id", "customer_id"]}}
        self.assertTrue(policy.check_question_dependencies(candidate, self.data["schema"])["review_notes"])

    def test_department_manager_condition_cannot_use_only_approver_join(self):
        candidate = {**self.payment_question(), "question": "Chi phi phong ban co truong phong thuoc phong ban duoc quan ly",
            "tables_used": ["operating_expenses", "departments", "employees"],
            "required_columns": {"operating_expenses": ["amount", "department_id"],
                                 "departments": ["department_id", "manager_employee_id"],
                                 "employees": ["employee_id", "department_id"]},
            "join_relations": [{"table_name": "employees", "columns": ["department_id"],
                                "referenced_table": "departments", "referenced_columns": ["department_id"]}]}
        with self.assertRaises(ValueError):
            policy.check_question_dependencies(candidate, self.data["schema"])
        candidate["join_relations"].append({"table_name": "departments", "columns": ["manager_employee_id"],
            "referenced_table": "employees", "referenced_columns": ["employee_id"]})
        self.assertIsInstance(policy.check_question_dependencies(candidate, self.data["schema"]), dict)

    def test_composite_address_fk_requires_both_columns(self):
        context, local, refs = self.group_request(domain="Sales & Orders")
        fk = next(f for f in local["fk_relations"] if f["name"] == "fk_orders_shipping_address_customer")
        candidate = {**self.payment_question(), "business_domain": "Sales & Orders", "tables_used": ["orders", "customer_addresses"],
            "required_columns": {"orders": ["shipping_address_id", "customer_id"],
                                 "customer_addresses": ["address_id", "customer_id"]},
            "table_roles": {"orders": "shipping link", "customer_addresses": "shipping address"},
            "join_relations": [{k:fk[k] for k in ("table_name", "columns", "referenced_table", "referenced_columns")}]}
        self.assertIsInstance(policy.check_group_usage(candidate, local), dict)
        candidate["required_columns"]["orders"].remove("customer_id")
        with self.assertRaises(ValueError):
            policy.check_group_usage(candidate, local)

    def test_actual_bad_drafts_27_29_30_trigger_dependency_guards(self):
        with main.connect(self.config, "ARENA") as db:
            rows = db.execute('SELECT draft_id,validation_report FROM draft.question_drafts WHERE draft_id IN (27,29,30)').fetchall()
        self.assertEqual(len(rows), 3)
        for row in rows:
            with self.subTest(draft=row["draft_id"]):
                with self.assertRaises(ValueError):
                    policy.check_question_dependencies(row["validation_report"]["candidate_metadata"], self.data["schema"])

    def test_one_table_s1_is_allowed_and_schema_text_does_not_include_context_neighbors(self):
        context, local, refs = self.group_request(domain="Customer Management", difficulty="easy", skill="S1")
        candidate = {**copy.deepcopy(QUESTION), "source_question_ids": refs,
                     "table_roles": {"customers": "customer IDs"}, "join_relations": []}
        result = v.validate_question(candidate, local, self.data["schema"], refs, [])
        self.assertTrue(result["passed_basic"], result["errors"])
        text = main.render_schema_text(context["world_schema"], candidate["tables_used"])
        self.assertIn("public.customers", text)
        self.assertNotIn("public.orders", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
