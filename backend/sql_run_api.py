"""Small SELECT-only API for SQLArena's first backend slice."""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, time as datetime_time
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


SQL_API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SQL_API_ROOT.parent
configured_env = os.environ.get("SQLARENA_ENV_FILE")
env_paths = ([Path(configured_env)] if configured_env else
             [REPO_ROOT / ".env", SQL_API_ROOT / ".env", REPO_ROOT / "ai" / ".env"])
for env_path in env_paths:
    for key, value in dotenv_values(env_path).items():
        if value is not None:
            os.environ.setdefault(key, value)

TIMEOUT_MS = int(os.environ.get("STATEMENT_TIMEOUT_MS", "10000"))
MAX_RESULT_ROWS = int(os.environ.get("MAX_RESULT_ROWS", "100000"))


def db_config(prefix: str) -> dict:
    return {
        "host": os.environ[f"{prefix}_DB_HOST"],
        "port": int(os.environ[f"{prefix}_DB_PORT"]),
        "dbname": os.environ[f"{prefix}_DB_NAME"],
        "user": os.environ[f"{prefix}_DB_USER"],
        "password": os.environ[f"{prefix}_DB_PASSWORD"],
        "row_factory": dict_row,
    }


@contextmanager
def connection(prefix: str):
    with psycopg.connect(**db_config(prefix)) as conn:
        yield conn


def json_value(value):
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, (datetime, date, datetime_time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f") if value else "0"
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    raise TypeError(f"Unsupported PostgreSQL value: {type(value).__name__}")


def stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def guard_select(sql: str) -> str:
    text = sql.strip()
    if not text:
        raise ValueError("SQL is empty")
    if "--" in text or "/*" in text or "*/" in text:
        raise ValueError("SQL comments are not accepted")
    if text.endswith(";"):
        text = text[:-1].rstrip()
    if ";" in text:
        raise ValueError("Only one SQL statement is accepted")
    if not re.match(r"^(SELECT|WITH)\b", text, flags=re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are accepted")
    forbidden = r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|CALL|DO|SET|RESET|GRANT|REVOKE|VACUUM|ANALYZE|REFRESH)\b"
    if re.search(forbidden, text, flags=re.IGNORECASE):
        raise ValueError("Only read-only SELECT queries are accepted")
    return text


def run_on_enterprise(sql: str) -> dict:
    with connection("ENTERPRISE") as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL TRANSACTION READ ONLY")
                cur.execute("SELECT set_config('statement_timeout', %s, true)", (f"{TIMEOUT_MS}ms",))
                cur.execute("SET LOCAL search_path = public")
                cur.execute(sql)
                columns = [item.name for item in cur.description]
                raw_rows = cur.fetchmany(MAX_RESULT_ROWS + 1)
                if len(raw_rows) > MAX_RESULT_ROWS:
                    raise ValueError(f"Result exceeds {MAX_RESULT_ROWS} rows")
                rows = [{name: json_value(value) for name, value in item.items()} for item in raw_rows]
                return {"columns": columns, "rows": rows, "row_count": len(rows)}


def get_question(question_id: str, include_expected: bool = False) -> dict | None:
    fields = "question_id,title,question_text,difficulty,primary_skill_group,primary_business_domain,skills,metadata"
    if include_expected:
        fields += ",expected_result"
    with connection("ARENA") as conn:
        return conn.execute(
            f"SELECT {fields} FROM core.source_questions WHERE question_id=%s",
            (question_id,),
        ).fetchone()


def question_schema(metadata: dict) -> list[dict]:
    tables = metadata.get("tables_used", [])
    if not tables:
        return []
    with connection("ENTERPRISE") as conn:
        rows = conn.execute(
            """SELECT table_name,column_name,data_type,is_nullable,ordinal_position
               FROM information_schema.columns
               WHERE table_schema='public' AND table_name=ANY(%s)
               ORDER BY table_name,ordinal_position""",
            (tables,),
        ).fetchall()
    by_table = {table: [] for table in tables}
    for row in rows:
        by_table[row["table_name"]].append({
            "name": row["column_name"],
            "type": row["data_type"],
            "nullable": row["is_nullable"] == "YES",
        })
    return [{"table": table, "columns": by_table[table]} for table in tables]


def compare_result(actual: dict, expected: dict) -> bool:
    if actual["columns"] != expected.get("columns", []):
        return False
    actual_rows = actual["rows"]
    expected_rows = expected.get("rows", [])
    if expected.get("compare_mode") == "ordered":
        return actual_rows == expected_rows
    return Counter(stable(row) for row in actual_rows) == Counter(stable(row) for row in expected_rows)


def find_user(user_id: int) -> dict | None:
    with connection("ARENA") as conn:
        return conn.execute(
            "SELECT user_id,username,display_name,role,status FROM app.users WHERE user_id=%s",
            (user_id,),
        ).fetchone()


def get_progress(user_id: int) -> list[dict]:
    with connection("ARENA") as conn:
        return conn.execute(
            """
            WITH attempts AS (
                SELECT question_id, COUNT(*) AS attempt_count
                FROM app.submissions
                WHERE user_id = %s
                GROUP BY question_id
            ), first_pass AS (
                SELECT DISTINCT ON (question_id)
                       question_id, submitted_at AS first_passed_at
                FROM app.submissions
                WHERE user_id = %s AND submission_status = 'passed'
                ORDER BY question_id, submitted_at, submission_id
            )
            SELECT q.question_id,
                   CASE
                       WHEN fp.question_id IS NOT NULL THEN 'passed'
                       WHEN a.question_id IS NOT NULL THEN 'attempted'
                       ELSE 'not_started'
                   END AS status,
                   fp.first_passed_at,
                   COALESCE(a.attempt_count, 0) AS attempt_count
            FROM core.source_questions q
            LEFT JOIN attempts a ON a.question_id = q.question_id
            LEFT JOIN first_pass fp ON fp.question_id = q.question_id
            ORDER BY q.question_id
            """,
            (user_id, user_id),
        ).fetchall()


def get_weekly_questions(set_id: int) -> list[str]:
    with connection("ARENA") as conn:
        rows = conn.execute(
            "SELECT question_id FROM app.weekly_set_questions WHERE set_id=%s",
            (set_id,),
        ).fetchall()
    return [row["question_id"] for row in rows]


def get_current_weekly_set(user_id: int) -> dict | None:
    with connection("ARENA") as conn:
        weekly_set = conn.execute(
            """
            SELECT set_id, set_name, starts_at, ends_at, status
            FROM app.weekly_sets
            WHERE status = 'published'
              AND NOW() >= starts_at AND NOW() < ends_at
            ORDER BY starts_at DESC
            LIMIT 1
            """
        ).fetchone()
        if not weekly_set:
            return None

        rows = conn.execute(
            """
            WITH attempts AS (
                SELECT question_id, COUNT(*)::INTEGER AS attempt_count
                FROM app.submissions
                WHERE user_id = %s
                GROUP BY question_id
            ), first_pass AS (
                SELECT DISTINCT ON (question_id)
                       question_id, submitted_at AS first_passed_at
                FROM app.submissions
                WHERE user_id = %s AND submission_status = 'passed'
                ORDER BY question_id, submitted_at, submission_id
            )
            SELECT q.question_id, q.title, q.question_text, q.difficulty,
                   q.primary_skill_group, q.primary_business_domain,
                   q.skills, q.metadata->'tables_used' AS tables_used,
                   wsq.position,
                   CASE
                       WHEN fp.question_id IS NOT NULL THEN 'passed'
                       WHEN a.question_id IS NOT NULL THEN 'attempted'
                       ELSE 'not_started'
                   END AS status,
                   fp.first_passed_at,
                   COALESCE(a.attempt_count, 0) AS attempt_count
            FROM app.weekly_set_questions wsq
            JOIN core.source_questions q ON q.question_id = wsq.question_id
            LEFT JOIN attempts a ON a.question_id = q.question_id
            LEFT JOIN first_pass fp ON fp.question_id = q.question_id
            WHERE wsq.set_id = %s
            ORDER BY wsq.position
            """,
            (user_id, user_id, weekly_set["set_id"]),
        ).fetchall()
        stats = conn.execute(
            """
            SELECT COUNT(s.submission_id)::INTEGER AS submission_count,
                   COUNT(*) FILTER (WHERE s.submission_status = 'passed')::INTEGER
                       AS passed_submission_count,
                   COUNT(DISTINCT s.question_id) FILTER (WHERE s.submission_status = 'passed')::INTEGER
                       AS passed_question_count
            FROM app.submissions s
            JOIN app.weekly_set_questions wsq
              ON wsq.set_id = %s AND wsq.question_id = s.question_id
            WHERE s.user_id = %s
              AND s.submitted_at >= %s
              AND s.submitted_at < %s
            """,
            (weekly_set["set_id"], user_id, weekly_set["starts_at"], weekly_set["ends_at"]),
        ).fetchone()
    submission_count = stats["submission_count"] or 0
    return {
        **weekly_set,
        "questions": rows,
        "count": len(rows),
        "passed_question_count": stats["passed_question_count"] or 0,
        "submission_count": submission_count,
        "passed_submission_count": stats["passed_submission_count"] or 0,
        "accuracy_percent": round(
            (stats["passed_submission_count"] or 0) * 100 / submission_count
        ) if submission_count else 0,
    }


def save_submission(user_id: int, question_id: str, sql: str, result: dict | None,
                    passed: bool, error: str | None, runtime_ms: int | None) -> int:
    submission_status = "passed" if passed else "failed"
    execution_status = "passed" if result is not None and error is None else "error"
    with connection("ARENA") as conn:
        with conn.transaction():
            submission = conn.execute(
                """INSERT INTO app.submissions
                   (user_id,question_id,submitted_sql,submission_status,score,
                    execution_status,result_json,error_message,runtime_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING submission_id""",
                (user_id, question_id, sql, submission_status, 100 if passed else 0,
                 execution_status, Jsonb(result) if result else None, error, runtime_ms),
            ).fetchone()
    return submission["submission_id"]


class SqlRequest(BaseModel):
    question_id: str
    sql: str = Field(min_length=1)
    user_id: int = 1


app = FastAPI(title="SQLArena SELECT API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    user = find_user(1)
    if not user:
        raise HTTPException(503, "learner_demo is missing")
    return {"ok": True, "database": "sqlarena_db", "test_user": user}


@app.get("/api/users")
def users():
    with connection("ARENA") as conn:
        rows = conn.execute(
            """SELECT user_id, username, display_name, role, status
               FROM app.users
               WHERE status = 'active'
               ORDER BY user_id"""
        ).fetchall()
    return {"items": rows, "count": len(rows)}


@app.get("/api/progress")
def progress(user_id: int = 1):
    user = find_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    items = get_progress(user_id)
    return {
        "user": user,
        "items": items,
        "passed_count": sum(item["status"] == "passed" for item in items),
        "attempted_count": sum(item["status"] == "attempted" for item in items),
    }


@app.get("/api/weekly-sets/current")
def current_weekly_set(user_id: int = 1):
    if not find_user(user_id):
        raise HTTPException(404, "User not found")
    weekly_set = get_current_weekly_set(user_id)
    if not weekly_set:
        raise HTTPException(404, "No active weekly set found")
    return weekly_set


@app.get("/api/progress/skills")
def skill_progress(user_id: int = 1):
    if not find_user(user_id):
        raise HTTPException(404, "User not found")
    labels = {
        "S1": "SELECT / WHERE / ORDER BY",
        "S2": "JOIN / LEFT JOIN / SELF JOIN",
        "S3": "GROUP BY / HAVING / aggregate",
        "S4": "Subquery / EXISTS / NOT EXISTS",
        "S5": "CTE / window functions",
        "S6": "Recursive / history / inventory",
    }
    with connection("ARENA") as conn:
        rows = conn.execute(
            """
            WITH weekly_set AS (
                SELECT set_id, starts_at, ends_at
                FROM app.weekly_sets
                WHERE status = 'published'
                  AND NOW() >= starts_at AND NOW() < ends_at
                ORDER BY starts_at DESC
                LIMIT 1
            ), weekly_questions AS (
                SELECT q.question_id, q.primary_skill_group, ws.starts_at, ws.ends_at
                FROM core.source_questions q
                JOIN app.weekly_set_questions wsq ON wsq.question_id = q.question_id
                JOIN weekly_set ws ON ws.set_id = wsq.set_id
            ), first_pass AS (
                SELECT DISTINCT ON (s.question_id) s.question_id
                FROM app.submissions s
                JOIN weekly_questions wq ON wq.question_id = s.question_id
                WHERE s.user_id = %s
                  AND s.submission_status = 'passed'
                  AND s.submitted_at >= wq.starts_at
                  AND s.submitted_at < wq.ends_at
                ORDER BY s.question_id, s.submitted_at, s.submission_id
            )
            SELECT wq.primary_skill_group AS skill_group,
                   COUNT(*)::INTEGER AS total_questions,
                   COUNT(fp.question_id)::INTEGER AS passed_questions
            FROM weekly_questions wq
            LEFT JOIN first_pass fp ON fp.question_id = wq.question_id
            GROUP BY wq.primary_skill_group
            ORDER BY wq.primary_skill_group
            """,
            (user_id,),
        ).fetchall()
    items = [
        {
            **row,
            "label": labels.get(row["skill_group"], row["skill_group"]),
            "percent": round(row["passed_questions"] * 100 / row["total_questions"])
            if row["total_questions"] else 0,
        }
        for row in rows
    ]
    return {"scope": "current_weekly_set", "items": items}


@app.get("/api/leaderboard/weekly")
def weekly_leaderboard(set_id: int | None = None):
    with connection("ARENA") as conn:
        weekly_set = conn.execute(
            """
            SELECT set_id, set_name, starts_at, ends_at, status
            FROM app.weekly_sets
            WHERE (%s::bigint IS NULL AND status = 'published'
                   AND NOW() >= starts_at AND NOW() < ends_at)
               OR set_id = %s::bigint
            ORDER BY starts_at DESC
            LIMIT 1
            """,
            (set_id, set_id),
        ).fetchone()
        if not weekly_set:
            raise HTTPException(404, "No active weekly set found")
        rows = conn.execute(
            """
            WITH first_pass AS (
                SELECT DISTINCT ON (s.user_id, s.question_id)
                       s.user_id, s.question_id, s.submitted_at AS first_passed_at
                FROM app.submissions s
                JOIN app.weekly_set_questions wsq
                  ON wsq.question_id = s.question_id
                 AND wsq.set_id = %s
                WHERE s.submission_status = 'passed'
                  AND s.submitted_at >= %s
                  AND s.submitted_at < %s
                ORDER BY s.user_id, s.question_id, s.submitted_at, s.submission_id
            ), scores AS (
                SELECT user_id, COUNT(*)::INTEGER AS correct_count,
                       MAX(first_passed_at) AS completed_at
                FROM first_pass
                GROUP BY user_id
            )
            SELECT ROW_NUMBER() OVER (ORDER BY sc.correct_count DESC, sc.completed_at, sc.user_id) AS rank,
                   sc.user_id, u.username, u.display_name,
                   sc.correct_count, sc.completed_at
            FROM scores sc
            JOIN app.users u ON u.user_id = sc.user_id
            ORDER BY rank
            """,
            (weekly_set["set_id"], weekly_set["starts_at"], weekly_set["ends_at"]),
        ).fetchall()
    return {
        "set": weekly_set,
        "total_questions": len(get_weekly_questions(weekly_set["set_id"])),
        "items": rows,
    }


@app.get("/api/leaderboard/monthly")
def monthly_leaderboard(year: int | None = None, month: int | None = None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    try:
        month_start = date(year, month, 1)
    except ValueError as exc:
        raise HTTPException(400, "Invalid year or month") from exc
    next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)

    with connection("ARENA") as conn:
        rows = conn.execute(
            """
            WITH monthly_questions AS (
                SELECT DISTINCT wsq.question_id
                FROM app.weekly_sets ws
                JOIN app.weekly_set_questions wsq ON wsq.set_id = ws.set_id
                WHERE ws.status = 'published'
                  AND ws.starts_at < %s
                  AND ws.ends_at > %s
            ), first_pass AS (
                SELECT DISTINCT ON (s.user_id, s.question_id)
                       s.user_id, s.question_id,
                       s.submitted_at AS first_passed_at
                FROM app.submissions s
                JOIN monthly_questions mq ON mq.question_id = s.question_id
                WHERE s.submission_status = 'passed'
                  AND s.submitted_at >= %s
                  AND s.submitted_at < %s
                ORDER BY s.user_id, s.question_id, s.submitted_at, s.submission_id
            ), scores AS (
                SELECT user_id, COUNT(*)::INTEGER AS correct_count,
                       MAX(first_passed_at) AS completed_at
                FROM first_pass
                GROUP BY user_id
            )
            SELECT ROW_NUMBER() OVER (ORDER BY sc.correct_count DESC,
                                      sc.completed_at, sc.user_id) AS rank,
                   sc.user_id, u.username, u.display_name,
                   sc.correct_count, sc.completed_at
            FROM scores sc
            JOIN app.users u ON u.user_id = sc.user_id
            WHERE u.status = 'active'
            ORDER BY rank
            """,
            (next_month, month_start, month_start, next_month),
        ).fetchall()
        total_questions = conn.execute(
            """
            SELECT COUNT(DISTINCT wsq.question_id)::INTEGER AS total_questions
            FROM app.weekly_sets ws
            JOIN app.weekly_set_questions wsq ON wsq.set_id = ws.set_id
            WHERE ws.status = 'published'
              AND ws.starts_at < %s
              AND ws.ends_at > %s
            """,
            (next_month, month_start),
        ).fetchone()["total_questions"]
    return {
        "period": {"year": year, "month": month},
        "total_questions": total_questions,
        "items": rows,
    }


@app.get("/api/questions")
def questions():
    with connection("ARENA") as conn:
        rows = conn.execute(
            """SELECT question_id,title,question_text,difficulty,primary_skill_group,
                      primary_business_domain,skills,metadata->'tables_used' AS tables_used
               FROM core.source_questions ORDER BY question_id"""
        ).fetchall()
    return {"items": rows, "count": len(rows)}


@app.get("/api/questions/{question_id}")
def question(question_id: str):
    row = get_question(question_id)
    if not row:
        raise HTTPException(404, "Question not found")
    metadata = row.pop("metadata") or {}
    return {**row, "metadata": metadata, "schema": question_schema(metadata)}


@app.post("/api/run")
def run(request: SqlRequest):
    if not find_user(request.user_id):
        raise HTTPException(404, "User not found")
    if not get_question(request.question_id):
        raise HTTPException(404, "Question not found")
    try:
        sql = guard_select(request.sql)
        return {"passed_policy": True, "saved": False, **run_on_enterprise(sql)}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/submissions")
def submit(request: SqlRequest):
    user = find_user(request.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    question = get_question(request.question_id, include_expected=True)
    if not question:
        raise HTTPException(404, "Question not found")
    try:
        sql = guard_select(request.sql)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    result = None
    error = None
    passed = False
    started = time.perf_counter()
    try:
        result = run_on_enterprise(sql)
        passed = compare_result(result, question["expected_result"])
        if not passed:
            error = "Result does not match expected_result"
    except Exception as exc:
        error = str(exc)
    runtime_ms = round((time.perf_counter() - started) * 1000)
    submission_id = save_submission(request.user_id, request.question_id, sql, result, passed, error, runtime_ms)
    return {
        "submission_id": submission_id,
        "passed": passed,
        "saved": True,
        "error": error,
        "runtime_ms": runtime_ms,
        "row_count": result["row_count"] if result else None,
    }
