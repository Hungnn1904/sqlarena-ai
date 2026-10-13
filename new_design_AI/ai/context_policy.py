"""Topic-specific schema neighborhoods; no SQL generation or database writes."""

import re
import unicodedata


DOMAIN_GROUPS = {
    "Customer Management": [
        ("customer_orders", ["customers", "customer_addresses", "orders"],
         ["customers", "customer_addresses"], "Customer profiles, addresses and purchasing behavior."),
    ],
    "Finance": [
        ("payment_refunds", ["customers", "orders", "payments", "refunds"],
         ["payments", "refunds"], "Payments, successful/failed attempts, refunds and financial amounts. "
         "Do not propose warehouse managers or unrelated employee hierarchy."),
        ("operating_costs", ["operating_expenses", "departments", "employees"],
         ["operating_expenses"], "Expense amounts, categories, dates, departments and approvers. "
         "Employee/department attributes must support an expense analysis, not a standalone HR goal."),
    ],
    "Human Resources": [
        ("organization", ["employees", "departments"], ["employees", "departments"],
         "Department membership, designated managers and employee reporting hierarchy."),
        ("salary_history", ["employees", "departments", "salary_history"], ["salary_history", "employees"],
         "Employee pay, salary changes over effective dates and department comparisons."),
    ],
    "Product & Inventory": [
        ("product_catalog", ["products", "categories", "suppliers"], ["products", "categories"],
         "Products, categories, suppliers, prices and cost margins."),
        ("stock_movements", ["products", "warehouses", "inventory_transactions", "order_items", "orders"],
         ["inventory_transactions"], "Stock changes and running inventory by product and warehouse; "
         "imports, sales, returns and adjustments are distinct transaction types."),
        ("warehouse_managers", ["warehouses", "employees", "departments"], ["warehouses"],
         "Warehouse managers, designated department managers and their department membership."),
    ],
    "Sales & Orders": [
        ("order_details", ["customers", "customer_addresses", "orders", "order_items", "products"],
         ["orders", "order_items"], "Customer orders, delivery addresses, order lines and product sales."),
        ("order_timeline", ["orders", "order_status_history", "employees", "warehouses"],
         ["orders", "order_status_history"], "Order lifecycle, status history, assigned staff and fulfillment warehouses."),
    ],
}


def fk_graph(tables, relations):
    graph = {t: set() for t in tables}
    for fk in relations:
        a, b = fk["table_name"], fk["referenced_table"]
        if a in graph and b in graph and a != b:
            graph[a].add(b)
            graph[b].add(a)
    return graph


def connected_tables(tables, relations):
    if not tables:
        return False
    graph = fk_graph(tables, relations)
    seen, pending = set(), [tables[0]]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(graph[node] - seen)
    return seen == set(tables)


def choose_context_group(data, request, index):
    minimum = 2 if request["skill"] == "S2" or request["difficulty"] == "medium" else 1
    domains = [request["domain"]] if request.get("domain") else sorted(
        set(request.get("allowed_domains", DOMAIN_GROUPS)) & set(DOMAIN_GROUPS))
    preferred = set(request.get("preferred_tables", []))
    candidates = {}
    for domain in domains:
        choices = []
        for name, names, primary, focus in DOMAIN_GROUPS.get(domain, []):
            tables = sorted(set(names) & set(data["schema"]))
            anchors = sorted(set(primary) & set(tables))
            if anchors and len(tables) >= minimum and preferred.issubset(tables) and connected_tables(
                    tables, data["world"]["fk_relations"]):
                choices.append({"id": name, "domain": domain, "tables": tables,
                                "primary_tables": anchors, "focus": focus, "min_tables": minimum,
                                "max_tables": 1 if request["skill"] == "S1" else len(tables)})
        if choices:
            candidates[domain] = choices
    if not candidates:
        raise ValueError("No FK-connected topic group fits the selected domain/preferred tables. "
                         "Choose compatible preferred tables or leave them blank; the domain is not changed silently.")
    available = sorted(candidates)
    domain = available[index % len(available)]
    choices = candidates[domain]
    return choices[(index // len(available)) % len(choices)]


def folded(text):
    text = text.lower().replace("\u0111", "d")
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text)
                            if not unicodedata.combining(c)).split())


def check_question_dependencies(candidate, schema):
    """Narrow explicit-language guards, not a general natural-language SQL proof."""
    text = folded(candidate["question"])
    used, required = set(candidate["tables_used"]), candidate["required_columns"]
    rules = [
        (r"quan ly kho", {"warehouses": ["manager_employee_id"], "employees": ["employee_id"]}),
        (r"truong phong (?:duoc )?chi dinh", {"departments": ["manager_employee_id"], "employees": ["employee_id"]}),
        (r"thanh toan thanh cong", {"payments": ["payment_status"]}),
        (r"da thanh toan", {"payments": ["payment_status"]}),
        (r"ten khach hang", {"customers": ["full_name"]}),
        (r"ten san pham", {"products": ["product_name"]}),
        (r"ten (?:phong ban|phong)", {"departments": ["department_name"]}),
        (r"dia chi mac dinh", {"customer_addresses": ["is_default"]}),
        (r"(?:ton kho|ton hien tai)", {"inventory_transactions": ["quantity_change"]}),
    ]
    if "orders" in used and re.search(r"khach hang|nguoi mua", text):
        rules.append((r"khach hang|nguoi mua", {"orders": ["customer_id"]}))
    if "orders" in used and re.search(r"delivered|shipped|cancelled|pending|da giao|nhan hang", text):
        rules.append((r"delivered|shipped|cancelled|pending|da giao|nhan hang", {"orders": ["status"]}))
    if "refunds" in used and re.search(r"(?:moi|tung) thanh toan", text):
        rules.append((r"(?:moi|tung) thanh toan", {"refunds": ["payment_id"]}))
    if "operating_expenses" in used:
        rules.append((r"tong (?:hop )?chi phi|tong so tien chi|trung binh chi phi", {"operating_expenses": ["amount"]}))
    matched = []
    for pattern, dependencies in rules:
        if not re.search(pattern, text):
            continue
        matched.append(pattern)
        for table, columns in dependencies.items():
            # Skip guards for a different world/fixture, not missing context tables.
            if table not in schema or not all(c in schema[table] for c in columns):
                continue
            if table not in used or not set(columns).issubset(required.get(table, [])):
                raise ValueError(f"Question requires {table}.{','.join(columns)} but tables_used/required_columns "
                                 "omit it. Rewrite the question within the provided topic group or declare the real dependency.")
    manager_link = {"table_name": "departments", "columns": ["manager_employee_id"],
                    "referenced_table": "employees", "referenced_columns": ["employee_id"]}
    if re.search(r"truong phong.*?(?:chi dinh|phong ban duoc quan ly)", text) and "join_relations" in candidate:
        if not any(matching_fk(link, [manager_link]) for link in candidate["join_relations"]):
            raise ValueError("Designated department manager requires the departments.manager_employee_id "
                             "to employees.employee_id relationship, not just an approver or membership join.")
    notes = []
    if "orders" in used and "don hang thanh cong" in text and not re.search(
            r"pending|processing|shipped|delivered|cancelled|thanh toan thanh cong", text):
        notes.append("Ambiguous successful-order definition: specify an actual order status or successful payment condition.")
    return {"matched_guards": matched, "review_notes": notes,
            "limitation": "Explicit phrase checks only; human semantic review still required."}


def matching_fk(relation, allowed):
    keys = ("table_name", "columns", "referenced_table", "referenced_columns")
    if not isinstance(relation, dict) or not all(k in relation for k in keys):
        return None
    reverse = {"table_name": relation["referenced_table"], "columns": relation["referenced_columns"],
               "referenced_table": relation["table_name"], "referenced_columns": relation["columns"]}
    return next((fk for fk in allowed if all(fk.get(k) == relation[k] for k in keys) or
                 all(fk.get(k) == reverse[k] for k in keys)), None)


def check_group_usage(candidate, request):
    group = request.get("context_group")
    if not group:
        return "No group contract supplied (legacy validation call)."
    tables = candidate["tables_used"]
    if not group["min_tables"] <= len(tables) <= group["max_tables"]:
        raise ValueError(f"This generation policy requires {group['min_tables']}..{group['max_tables']} question tables; "
                         "table count is a diversity policy, not a difficulty score.")
    if candidate["business_domain"] != group["domain"]:
        raise ValueError(f"Topic group is {group['domain']}; do not invent a different domain label.")
    if not set(tables) & set(group["primary_tables"]):
        raise ValueError("Question must use a primary topic table, not only supporting tables.")
    roles = candidate.get("table_roles")
    if not isinstance(roles, dict) or set(roles) != set(tables) or not all(
            isinstance(role, str) and role.strip() for role in roles.values()):
        raise ValueError("table_roles must explain a concrete role for every question table and no other tables.")
    declared = candidate.get("join_relations")
    if not isinstance(declared, list):
        raise ValueError("join_relations must be an array of actual FK relationships; [] for one table.")
    allowed = request.get("fk_relations", [])
    chosen = []
    keys = ("table_name", "columns", "referenced_table", "referenced_columns")
    for relation in declared:
        if not isinstance(relation, dict) or not all(k in relation for k in keys):
            raise ValueError("join_relations entries need table_name, columns, referenced_table, referenced_columns.")
        match = matching_fk(relation, allowed)
        if not match or match["table_name"] not in tables or match["referenced_table"] not in tables:
            raise ValueError("join_relations must be real FKs between declared question tables; do not invent joins.")
        for table, columns in ((match["table_name"], match["columns"]),
                               (match["referenced_table"], match["referenced_columns"])):
            if not set(columns).issubset(candidate["required_columns"][table]):
                raise ValueError(f"required_columns omits join key(s) of {table}: {columns}")
        chosen.append(match)
    if not connected_tables(tables, chosen):
        raise ValueError("Declared join_relations do not connect all question tables; include required bridge tables.")
    return {"group": group["id"], "tables": tables, "fk_evidence_count": len(chosen),
            "limitation": "Roles and FK declarations are evidence, not proof that every table is needed."}
