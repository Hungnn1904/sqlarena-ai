from __future__ import annotations


_TOPIC_POOL = [
    {
        "topic": "SELECT_BASIC",
        "subtopics": ["column selection", "alias", "DISTINCT", "literal values"],
        "difficulty_weight": {"easy": 0.6, "medium": 0.3, "hard": 0.1},
        "common_mistakes": [
            "Forgetting DISTINCT when duplicates need to be removed",
            "Confusing column alias scope in WHERE clause",
        ],
    },
    {
        "topic": "WHERE_FILTER",
        "subtopics": ["comparison operators", "BETWEEN", "IN", "LIKE", "IS NULL"],
        "difficulty_weight": {"easy": 0.5, "medium": 0.35, "hard": 0.15},
        "common_mistakes": [
            "Using = NULL instead of IS NULL",
            "LIKE pattern anchor omission (missing % wildcard)",
        ],
    },
    {
        "topic": "JOIN_INNER",
        "subtopics": ["two-table join", "multi-table join", "join condition"],
        "difficulty_weight": {"easy": 0.4, "medium": 0.4, "hard": 0.2},
        "common_mistakes": [
            "Cartesian product from missing ON clause",
            "Ambiguous column name without table prefix",
        ],
    },
    {
        "topic": "JOIN_LEFT",
        "subtopics": ["LEFT JOIN", "finding unmatched rows", "NULL filtering after LEFT JOIN"],
        "difficulty_weight": {"easy": 0.2, "medium": 0.5, "hard": 0.3},
        "common_mistakes": [
            "Moving LEFT JOIN filter to WHERE (converts to INNER JOIN)",
            "Expecting non-NULL for unmatched rows",
        ],
    },
    {
        "topic": "GROUP_BY",
        "subtopics": ["single column grouping", "multi-column grouping", "non-aggregated columns"],
        "difficulty_weight": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        "common_mistakes": [
            "Selecting non-aggregated column not in GROUP BY",
            "Confusing GROUP BY column order with ORDER BY",
        ],
    },
    {
        "topic": "HAVING",
        "subtopics": ["filter on aggregate", "HAVING vs WHERE", "combined HAVING and WHERE"],
        "difficulty_weight": {"easy": 0.1, "medium": 0.5, "hard": 0.4},
        "common_mistakes": [
            "Using WHERE to filter aggregate result instead of HAVING",
            "Repeating aggregate expression incorrectly in HAVING",
        ],
    },
    {
        "topic": "SUBQUERY",
        "subtopics": ["scalar subquery", "IN subquery", "EXISTS", "correlated subquery"],
        "difficulty_weight": {"easy": 0.0, "medium": 0.4, "hard": 0.6},
        "common_mistakes": [
            "Correlated subquery referencing wrong outer alias",
            "Using = instead of IN for multi-row subquery result",
        ],
    },
    {
        "topic": "AGGREGATE",
        "subtopics": ["COUNT", "SUM", "AVG", "MIN", "MAX", "COUNT DISTINCT"],
        "difficulty_weight": {"easy": 0.4, "medium": 0.4, "hard": 0.2},
        "common_mistakes": [
            "COUNT(*) vs COUNT(column) difference with NULLs",
            "AVG ignoring NULL rows",
        ],
    },
    {
        "topic": "ORDER_LIMIT",
        "subtopics": ["ASC/DESC", "multi-column order", "LIMIT", "OFFSET pagination"],
        "difficulty_weight": {"easy": 0.5, "medium": 0.35, "hard": 0.15},
        "common_mistakes": [
            "Default sort direction assumption",
            "OFFSET without ORDER BY producing non-deterministic results",
        ],
    },
    {
        "topic": "WINDOW_FUNCTION",
        "subtopics": ["ROW_NUMBER", "RANK", "DENSE_RANK", "LAG/LEAD", "PARTITION BY", "running total"],
        "difficulty_weight": {"easy": 0.0, "medium": 0.1, "hard": 0.9},
        "common_mistakes": [
            "Confusing RANK and DENSE_RANK gap behavior",
            "Missing ORDER BY inside OVER clause",
            "Applying window function in WHERE (must use subquery/CTE)",
        ],
    },
    {
        "topic": "CASE_WHEN",
        "subtopics": ["simple CASE", "searched CASE", "CASE in aggregation", "CASE in ORDER BY"],
        "difficulty_weight": {"easy": 0.1, "medium": 0.5, "hard": 0.4},
        "common_mistakes": [
            "Missing ELSE branch causing NULL for unmatched rows",
            "CASE evaluated left-to-right short-circuit not understood",
        ],
    },
    {
        "topic": "NULL_HANDLING",
        "subtopics": ["IS NULL / IS NOT NULL", "COALESCE", "NULLIF", "NULL in aggregates"],
        "difficulty_weight": {"easy": 0.3, "medium": 0.4, "hard": 0.3},
        "common_mistakes": [
            "Arithmetic with NULL always returns NULL",
            "NULL != NULL comparison returns NULL not TRUE",
        ],
    },
]

_DIFFICULTY_CONFIG = {
    "easy": {
        "max_joins": 1,
        "allow_subquery": False,
        "allow_aggregation": True,
        "aggregation_whitelist": ["COUNT", "SUM"],
        "allow_window": False,
        "max_tables": 2,
    },
    "medium": {
        "max_joins": 2,
        "allow_subquery": True,
        "subquery_type": "simple",
        "allow_aggregation": True,
        "aggregation_whitelist": ["COUNT", "SUM", "AVG", "MIN", "MAX"],
        "allow_window": False,
        "max_tables": 3,
    },
    "hard": {
        "max_joins": 3,
        "allow_subquery": True,
        "subquery_type": "correlated",
        "allow_aggregation": True,
        "aggregation_whitelist": ["COUNT", "SUM", "AVG", "MIN", "MAX"],
        "allow_window": True,
        "max_tables": 4,
    },
}

_FEW_SHOT_EXAMPLES: dict[tuple[str, str], str] = {
    ("SELECT_BASIC", "easy"): (
        "Q: List the names and roles of all employees.\n"
        "A: SELECT name, role FROM employees;"
    ),
    ("WHERE_FILTER", "easy"): (
        "Q: Find all employees whose role is 'Manager'.\n"
        "A: SELECT * FROM employees WHERE role = 'Manager';"
    ),
    ("JOIN_INNER", "easy"): (
        "Q: Show each employee's name along with their department name.\n"
        "A: SELECT e.name, d.name AS department\n"
        "   FROM employees e\n"
        "   JOIN departments d ON e.department_id = d.id;"
    ),
    ("JOIN_INNER", "medium"): (
        "Q: List products along with their total quantity sold. Show only products that have sales.\n"
        "A: SELECT p.product_id, SUM(s.quantity) AS total_sold\n"
        "   FROM products p\n"
        "   JOIN sales s ON p.product_id = s.product_id\n"
        "   GROUP BY p.product_id;"
    ),
    ("JOIN_LEFT", "medium"): (
        "Q: List all products and their total quantity sold. Include products with no sales (show 0).\n"
        "A: SELECT p.product_id, COALESCE(SUM(s.quantity), 0) AS total_sold\n"
        "   FROM products p\n"
        "   LEFT JOIN sales s ON p.product_id = s.product_id\n"
        "   GROUP BY p.product_id;"
    ),
    ("GROUP_BY", "easy"): (
        "Q: Count the number of employees in each department.\n"
        "A: SELECT department_id, COUNT(*) AS headcount\n"
        "   FROM employees\n"
        "   GROUP BY department_id;"
    ),
    ("GROUP_BY", "medium"): (
        "Q: Find the average product price per category.\n"
        "A: SELECT category_id, AVG(price) AS avg_price\n"
        "   FROM products\n"
        "   GROUP BY category_id;"
    ),
    ("HAVING", "medium"): (
        "Q: Find departments with more than 2 employees.\n"
        "A: SELECT department_id, COUNT(*) AS headcount\n"
        "   FROM employees\n"
        "   GROUP BY department_id\n"
        "   HAVING COUNT(*) > 2;"
    ),
    ("HAVING", "hard"): (
        "Q: Find categories where the total stock is above the average stock across all categories.\n"
        "A: SELECT category_id, SUM(stock) AS total_stock\n"
        "   FROM products\n"
        "   GROUP BY category_id\n"
        "   HAVING SUM(stock) > (SELECT AVG(cat_stock) FROM\n"
        "       (SELECT SUM(stock) AS cat_stock FROM products GROUP BY category_id));"
    ),
    ("SUBQUERY", "medium"): (
        "Q: Find employees who work in the same department as 'Nguyen An'.\n"
        "A: SELECT name FROM employees\n"
        "   WHERE department_id = (\n"
        "       SELECT department_id FROM employees WHERE name = 'Nguyen An'\n"
        "   ) AND name != 'Nguyen An';"
    ),
    ("SUBQUERY", "hard"): (
        "Q: Find products whose price is above the average price of their category.\n"
        "A: SELECT p1.product_id, p1.price\n"
        "   FROM products p1\n"
        "   WHERE p1.price > (\n"
        "       SELECT AVG(p2.price) FROM products p2\n"
        "       WHERE p2.category_id = p1.category_id\n"
        "   );"
    ),
    ("AGGREGATE", "easy"): (
        "Q: How many employees are there in total?\n"
        "A: SELECT COUNT(*) AS total_employees FROM employees;"
    ),
    ("AGGREGATE", "medium"): (
        "Q: What is the most expensive product price?\n"
        "A: SELECT MAX(price) AS max_price FROM products;"
    ),
    ("ORDER_LIMIT", "easy"): (
        "Q: List the 3 most expensive products.\n"
        "A: SELECT product_id, price FROM products ORDER BY price DESC LIMIT 3;"
    ),
    ("WINDOW_FUNCTION", "hard"): (
        "Q: Rank employees within each department by their ID.\n"
        "A: SELECT name, department_id,\n"
        "          RANK() OVER (PARTITION BY department_id ORDER BY id) AS dept_rank\n"
        "   FROM employees;"
    ),
    ("CASE_WHEN", "medium"): (
        "Q: Label each product as 'Expensive' if price > 500, 'Moderate' if 100-500, else 'Cheap'.\n"
        "A: SELECT product_id, price,\n"
        "          CASE\n"
        "              WHEN price > 500 THEN 'Expensive'\n"
        "              WHEN price >= 100 THEN 'Moderate'\n"
        "              ELSE 'Cheap'\n"
        "          END AS price_label\n"
        "   FROM products;"
    ),
    ("NULL_HANDLING", "medium"): (
        "Q: List all employees, replacing NULL role with 'Unknown'.\n"
        "A: SELECT name, COALESCE(role, 'Unknown') AS role FROM employees;"
    ),
    ("NULL_HANDLING", "hard"): (
        "Q: Find employees whose role is not set (NULL).\n"
        "A: SELECT * FROM employees WHERE role IS NULL;"
    ),
}

_DEFAULT_EXAMPLE = (
    "Q: List all records from the employees table.\n"
    "A: SELECT * FROM employees;"
)


def get_topic_pool() -> list[dict]:
    return [dict(t) for t in _TOPIC_POOL]


def get_difficulty_config(difficulty: str) -> dict:
    key = difficulty.lower()
    if key not in _DIFFICULTY_CONFIG:
        raise ValueError(f"Unknown difficulty '{difficulty}'. Valid values: easy, medium, hard")
    return dict(_DIFFICULTY_CONFIG[key])


def get_few_shot_example(topic: str, difficulty: str) -> str:
    key = (topic.upper(), difficulty.lower())
    if key in _FEW_SHOT_EXAMPLES:
        return _FEW_SHOT_EXAMPLES[key]

    topic_only = topic.upper()
    for (t, d), example in _FEW_SHOT_EXAMPLES.items():
        if t == topic_only:
            return example

    return _DEFAULT_EXAMPLE
