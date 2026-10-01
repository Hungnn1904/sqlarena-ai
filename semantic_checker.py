import re


def check_semantic_consistency(
    question_text: str,
    answer_sql: str,
    seed_sql: str,
    topic: str,
    output: list,
) -> dict:
    issues = []
    sql_upper = answer_sql.upper()

    if not output:
        issues.append("Answer SQL returns an empty result on the generated seed data")

    if topic == "JOIN_LEFT" and not re.search(r"\bLEFT\s+(?:OUTER\s+)?JOIN\b", sql_upper):
        issues.append("JOIN_LEFT topic requires a LEFT JOIN in answer_sql")

    if topic == "WINDOW_FUNCTION":
        if " OVER " not in f" {sql_upper} ":
            issues.append("WINDOW_FUNCTION topic requires an OVER clause")
        if not re.search(r"\b(ROW_NUMBER|RANK|DENSE_RANK|NTILE)\s*\(", sql_upper):
            issues.append("WINDOW_FUNCTION topic requires a ranking window function")

    literals = {
        value.strip().casefold()
        for value in re.findall(r"['\"]([^'\"]{2,50})['\"]", question_text)
        if value.strip()
    }
    seed_lower = seed_sql.casefold()
    missing_literals = sorted(value for value in literals if value not in seed_lower)
    if missing_literals:
        issues.append(
            "Question references values absent from seed data: " + ", ".join(missing_literals)
        )

    return {"is_consistent": not issues, "issues": issues}
