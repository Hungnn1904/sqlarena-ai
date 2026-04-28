from __future__ import annotations

import re
import sqlite3
import threading
import time


_FORBIDDEN_PATTERN = re.compile(
    r"\b(DROP|TRUNCATE|ATTACH|DETACH)\b",
    re.IGNORECASE,
)

_DANGEROUS_PRAGMA_PATTERN = re.compile(
    r"\bPRAGMA\s+(?!query_only\b)",
    re.IGNORECASE,
)

_ROW_LIMIT = 100
_TIMEOUT_SECONDS = 5.0


def _is_forbidden(sql: str) -> bool:
    if _FORBIDDEN_PATTERN.search(sql):
        return True
    if _DANGEROUS_PRAGMA_PATTERN.search(sql):
        return True
    return False


def _split_statements(sql: str) -> list[str]:
    parts = sql.split(";")
    return [p.strip() for p in parts if p.strip()]


def _execute_statements(conn: sqlite3.Connection, sql: str) -> None:
    for stmt in _split_statements(sql):
        conn.execute(stmt)


def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchmany(_ROW_LIMIT)
    return [dict(zip(columns, row)) for row in rows]


def verify_in_sandbox(ddl_sql: str, seed_sql: str, answer_sql: str) -> dict:
    answer_stripped = answer_sql.strip()

    if _is_forbidden(answer_stripped):
        return {
            "valid": False,
            "output": [],
            "row_count": 0,
            "error": "Forbidden operation detected in answer SQL",
            "duration_ms": 0,
        }

    result: dict = {}
    exception_holder: list[Exception] = []

    def _run():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = None
        try:
            conn.execute("PRAGMA journal_mode=OFF")
            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("PRAGMA query_only=OFF")

            if ddl_sql and ddl_sql.strip():
                _execute_statements(conn, ddl_sql)

            if seed_sql and seed_sql.strip():
                _execute_statements(conn, seed_sql)
            conn.commit()

            start_ns = time.perf_counter_ns()
            cursor = conn.execute(answer_stripped)
            rows = _rows_to_dicts(cursor)
            elapsed_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

            result.update({
                "valid": True,
                "output": rows,
                "row_count": len(rows),
                "error": None,
                "duration_ms": int(elapsed_ms),
            })
        except sqlite3.Error as exc:
            result.update({
                "valid": False,
                "output": [],
                "row_count": 0,
                "error": str(exc),
                "duration_ms": 0,
            })
        except Exception as exc:
            exception_holder.append(exc)
        finally:
            conn.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=_TIMEOUT_SECONDS)

    if thread.is_alive():
        return {
            "valid": False,
            "output": [],
            "row_count": 0,
            "error": f"Query execution timed out after {int(_TIMEOUT_SECONDS)}s",
            "duration_ms": int(_TIMEOUT_SECONDS * 1000),
        }

    if exception_holder:
        return {
            "valid": False,
            "output": [],
            "row_count": 0,
            "error": f"Unexpected error: {exception_holder[0]}",
            "duration_ms": 0,
        }

    if not result:
        return {
            "valid": False,
            "output": [],
            "row_count": 0,
            "error": "Execution thread produced no result",
            "duration_ms": 0,
        }

    return result
