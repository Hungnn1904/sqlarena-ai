import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from excel_loader import load_excel_rows


TABLE_START_PATTERN = re.compile(r"([A-Za-z_][\w$]*)\s*\(")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][\w$]*$")

TYPE_ALIASES = {
    "INT": "INTEGER",
    "INTEGER": "INTEGER",
    "SMALLINT": "INTEGER",
    "BIGINT": "INTEGER",
    "TINYINT": "INTEGER",
    "NUMBER": "DECIMAL",
    "NUMERIC": "DECIMAL",
    "DECIMAL": "DECIMAL",
    "REAL": "DECIMAL",
    "FLOAT": "DECIMAL",
    "DOUBLE": "DECIMAL",
    "CHAR": "VARCHAR",
    "NCHAR": "VARCHAR",
    "VARCHAR": "VARCHAR",
    "VARCHAR2": "VARCHAR",
    "NVARCHAR": "VARCHAR",
    "TEXT": "VARCHAR",
    "STRING": "VARCHAR",
    "BOOL": "BOOLEAN",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "DATETIME": "DATETIME",
    "TIMESTAMP": "DATETIME",
}

TYPE_PRIORITY = {
    "BOOLEAN": 1,
    "INTEGER": 2,
    "DECIMAL": 3,
    "DATE": 4,
    "DATETIME": 5,
    "VARCHAR": 6,
}


def normalize_type(raw_type: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", raw_type.upper())
    cleaned = re.sub(r"\b(UNSIGNED|NULL|NOT NULL|DEFAULT\s+\S+)\b", "", cleaned)
    tokens = re.findall(r"[A-Z]+", cleaned)
    for token in tokens:
        if token in TYPE_ALIASES:
            return TYPE_ALIASES[token]
    return "VARCHAR"


def _split_top_level(value: str, separator: str = ",") -> list[str]:
    parts = []
    start = 0
    depth = 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == separator and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def _extract_table_definitions(schema_text: str) -> list[tuple[str, str]]:
    definitions = []
    position = 0
    while True:
        match = TABLE_START_PATTERN.search(schema_text, position)
        if match is None:
            break
        depth = 1
        index = match.end()
        while index < len(schema_text) and depth:
            if schema_text[index] == "(":
                depth += 1
            elif schema_text[index] == ")":
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f"unclosed table definition for '{match.group(1)}'")
        definitions.append((match.group(1), schema_text[match.end():index - 1]))
        position = index
    return definitions


def parse_database_schema(schema_text: str) -> list[dict[str, Any]]:
    if not schema_text or not str(schema_text).strip():
        raise ValueError("database_schema is empty")

    definitions = _extract_table_definitions(str(schema_text))
    if not definitions:
        raise ValueError("no table definition found")

    tables = []
    for table_name, column_text in definitions:
        columns = []
        for raw_column in _split_top_level(column_text):
            parts = raw_column.strip().strip("`[]\"").split()
            if len(parts) < 2:
                raise ValueError(
                    f"invalid column definition '{raw_column.strip()}' in table '{table_name}'"
                )
            column_name = parts[0].strip("`[]\"")
            if not IDENTIFIER_PATTERN.match(column_name):
                raise ValueError(f"invalid column name '{column_name}' in table '{table_name}'")
            columns.append({"name": column_name, "type": normalize_type(" ".join(parts[1:]))})
        if not columns:
            raise ValueError(f"table '{table_name}' has no columns")
        tables.append({"name": table_name, "columns": columns})
    return tables


def _choose_type(existing: str, incoming: str) -> str:
    return max((existing, incoming), key=lambda value: TYPE_PRIORITY.get(value, 99))


def build_generated_schema(rows: list[dict[str, Any]]) -> tuple[dict, dict]:
    tables: OrderedDict[str, dict[str, Any]] = OrderedDict()
    table_keys: dict[str, str] = {}
    report = {
        "rows_processed": len(rows),
        "rows_parsed": 0,
        "tables_added": 0,
        "columns_added": 0,
        "type_conflicts": [],
        "parse_errors": [],
    }

    for row in rows:
        try:
            parsed_tables = parse_database_schema(str(row.get("database_schema") or ""))
        except ValueError as exc:
            report["parse_errors"].append(
                {"excel_row": row.get("excel_row"), "id": row.get("id"), "error": str(exc)}
            )
            continue

        report["rows_parsed"] += 1
        for parsed_table in parsed_tables:
            incoming_name = parsed_table["name"]
            table_key = incoming_name.casefold()
            table_name = table_keys.get(table_key)
            if table_name is None:
                table_name = incoming_name
                table_keys[table_key] = table_name
                tables[table_name] = {"columns": OrderedDict(), "_column_keys": {}}
                report["tables_added"] += 1

            table = tables[table_name]
            for incoming_column in parsed_table["columns"]:
                incoming_column_name = incoming_column["name"]
                column_key = incoming_column_name.casefold()
                column_name = table["_column_keys"].get(column_key)
                if column_name is None:
                    table["_column_keys"][column_key] = incoming_column_name
                    table["columns"][incoming_column_name] = incoming_column["type"]
                    report["columns_added"] += 1
                    continue

                existing_type = table["columns"][column_name]
                incoming_type = incoming_column["type"]
                if existing_type != incoming_type:
                    chosen_type = _choose_type(existing_type, incoming_type)
                    report["type_conflicts"].append(
                        {
                            "excel_row": row.get("excel_row"),
                            "id": row.get("id"),
                            "table": table_name,
                            "column": column_name,
                            "existing_type": existing_type,
                            "incoming_type": incoming_type,
                            "chosen_type": chosen_type,
                        }
                    )
                    table["columns"][column_name] = chosen_type

    output_tables = OrderedDict()
    for table_name, table in tables.items():
        output_tables[table_name] = {"columns": table["columns"]}
    return {"tables": output_tables}, report


def schema_from_excel_row(row: dict[str, Any]) -> dict:
    schema, report = build_generated_schema([row])
    if report["parse_errors"]:
        raise ValueError(report["parse_errors"][0]["error"])
    return schema


def sync_excel_schema(
    excel_path: str,
    output_path: str = "schema.generated.json",
    report_path: str = "schema.generated.report.json",
    limit: int | None = None,
) -> tuple[dict, dict]:
    rows = list(load_excel_rows(excel_path, limit=limit))
    schema, report = build_generated_schema(rows)
    Path(output_path).write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(report_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return schema, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a JSON schema from the Excel dataset")
    parser.add_argument("excel_path", nargs="?", default="Master_SQL_Dataset_All_Sources_2_1.xlsx")
    parser.add_argument("--output", default="schema.generated.json")
    parser.add_argument("--report", default="schema.generated.report.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    schema, report = sync_excel_schema(
        args.excel_path, output_path=args.output, report_path=args.report, limit=args.limit
    )
    print(
        f"Processed {report['rows_processed']} rows: "
        f"{len(schema['tables'])} tables, {report['columns_added']} columns, "
        f"{len(report['type_conflicts'])} type conflicts, "
        f"{len(report['parse_errors'])} parse errors."
    )


if __name__ == "__main__":
    main()
