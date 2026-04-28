import json
import random
from pathlib import Path


_FIRST_NAMES = ["An", "Binh", "Cuong", "Dung", "Giang", "Ha", "Hung", "Lan", "Mai", "Nam",
                "Phuong", "Quang", "Son", "Thao", "Trung", "Van", "Yen", "Long", "Hoa", "Minh"]
_LAST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Dang", "Bui", "Do", "Ngo"]
_DEPARTMENTS = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations", "Legal", "R&D"]
_ROLES = ["Engineer", "Manager", "Analyst", "Director", "Coordinator", "Specialist", "Lead", "Associate"]
_PRODUCT_CATEGORIES = {1: "Electronics", 2: "Clothing", 3: "Food", 4: "Books", 5: "Sports"}
_PRICE_RANGES = {1: (50, 2000), 2: (10, 300), 3: (1, 50), 4: (5, 100), 5: (15, 500)}

_TYPE_MAP = {
    "INTEGER": "INTEGER",
    "VARCHAR": "TEXT",
    "TEXT": "TEXT",
    "DECIMAL": "REAL",
    "FLOAT": "REAL",
    "DOUBLE": "REAL",
    "BOOLEAN": "INTEGER",
    "DATE": "TEXT",
    "DATETIME": "TEXT",
    "TIMESTAMP": "TEXT",
}

_FK_HINTS = {
    "department_id": ("departments", "id"),
    "category_id": (None, None),
    "product_id": ("products", "product_id"),
}


def load_schema(path: str = "schema.json") -> dict:
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Schema file not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "tables" not in data:
        raise ValueError("Schema JSON must have a top-level 'tables' key")
    return data


def _sqlite_type(col_type: str) -> str:
    upper = col_type.upper()
    for key, val in _TYPE_MAP.items():
        if key in upper:
            return val
    return "TEXT"


def _is_pk(col_type: str) -> bool:
    return "PRIMARY KEY" in col_type.upper()


def generate_ddl(schema: dict) -> str:
    statements = []
    for table_name, table_def in schema["tables"].items():
        cols = table_def.get("columns", {})
        col_defs = []
        fk_clauses = []
        for col_name, col_type in cols.items():
            upper = col_type.upper()
            if _is_pk(upper):
                sqlite_col_type = _sqlite_type(upper.replace("PRIMARY KEY", "").strip())
                col_defs.append(f"    {col_name} {sqlite_col_type} PRIMARY KEY")
            else:
                col_defs.append(f"    {col_name} {_sqlite_type(col_type)}")
            if col_name in _FK_HINTS and _FK_HINTS[col_name][0] is not None:
                ref_table, ref_col = _FK_HINTS[col_name]
                if ref_table in schema["tables"] and ref_table != table_name:
                    fk_clauses.append(
                        f"    FOREIGN KEY ({col_name}) REFERENCES {ref_table}({ref_col})"
                    )
        all_defs = col_defs + fk_clauses
        body = ",\n".join(all_defs)
        statements.append(f"CREATE TABLE IF NOT EXISTS {table_name} (\n{body}\n);")
    return "\n\n".join(statements)


def _gen_employee_row(idx: int, dept_ids: list[int]) -> dict:
    name = f"{random.choice(_LAST_NAMES)} {random.choice(_FIRST_NAMES)}"
    return {
        "id": idx,
        "name": name,
        "department_id": random.choice(dept_ids) if dept_ids else 1,
        "role": random.choice(_ROLES),
    }


def _gen_department_row(idx: int) -> dict:
    dept_name = _DEPARTMENTS[(idx - 1) % len(_DEPARTMENTS)]
    return {"id": idx, "name": dept_name}


def _gen_product_row(idx: int) -> dict:
    cat_id = (idx % len(_PRODUCT_CATEGORIES)) + 1
    low, high = _PRICE_RANGES[cat_id]
    price = round(random.uniform(low, high), 2)
    stock = random.randint(0, 500)
    return {"product_id": idx, "category_id": cat_id, "price": price, "stock": stock}


def _gen_sale_row(idx: int, product_ids: list[int]) -> dict:
    return {
        "sale_id": idx,
        "product_id": random.choice(product_ids) if product_ids else 1,
        "quantity": random.randint(1, 50),
    }


def _gen_inventory_row(product_id: int) -> dict:
    return {"product_id": product_id, "quantity": random.randint(0, 300)}


def _build_insert(table: str, cols: list[str], rows: list[dict]) -> str:
    col_list = ", ".join(cols)
    value_lines = []
    for row in rows:
        vals = []
        for c in cols:
            v = row.get(c)
            if v is None:
                vals.append("NULL")
            elif isinstance(v, str):
                escaped = v.replace("'", "''")
                vals.append(f"'{escaped}'")
            else:
                vals.append(str(v))
        value_lines.append(f"    ({', '.join(vals)})")
    values_block = ",\n".join(value_lines)
    return f"INSERT INTO {table} ({col_list}) VALUES\n{values_block};"


_GENERATORS = {
    "departments": _gen_department_row,
    "employees": _gen_employee_row,
    "products": _gen_product_row,
    "sales": _gen_sale_row,
    "inventory": _gen_inventory_row,
}


def generate_seed(schema: dict, rows_per_table: int = 5) -> str:
    random.seed(42)
    generated: dict[str, list[dict]] = {}
    statements = []

    table_order = _topological_sort(schema)

    for table_name in table_order:
        table_def = schema["tables"].get(table_name)
        if table_def is None:
            continue
        cols = list(table_def.get("columns", {}).keys())
        rows = []

        if table_name == "departments":
            for i in range(1, rows_per_table + 1):
                rows.append(_gen_department_row(i))

        elif table_name == "employees":
            dept_ids = [r["id"] for r in generated.get("departments", [])]
            for i in range(1, rows_per_table + 1):
                rows.append(_gen_employee_row(i, dept_ids))

        elif table_name == "products":
            for i in range(1, rows_per_table + 1):
                rows.append(_gen_product_row(i))

        elif table_name == "sales":
            product_ids = [r["product_id"] for r in generated.get("products", [])]
            for i in range(1, rows_per_table + 1):
                rows.append(_gen_sale_row(i, product_ids))

        elif table_name == "inventory":
            product_ids = [r["product_id"] for r in generated.get("products", [])]
            for pid in product_ids:
                rows.append(_gen_inventory_row(pid))

        else:
            for i in range(1, rows_per_table + 1):
                row = {}
                for col, col_type in table_def["columns"].items():
                    if _is_pk(col_type):
                        row[col] = i
                    else:
                        row[col] = f"value_{i}"
                rows.append(row)

        if rows:
            generated[table_name] = rows
            statements.append(_build_insert(table_name, cols, rows))

    return "\n\n".join(statements)


def _topological_sort(schema: dict) -> list[str]:
    dependency_map = {
        "employees": ["departments"],
        "sales": ["products"],
        "inventory": ["products"],
    }
    tables = list(schema["tables"].keys())
    visited = set()
    result = []

    def visit(name: str):
        if name in visited:
            return
        visited.add(name)
        for dep in dependency_map.get(name, []):
            if dep in schema["tables"]:
                visit(dep)
        result.append(name)

    for t in tables:
        visit(t)
    return result
