"""Use Cases: Thực thi SQL Read-Only Sandbox, Chấm bài (Grading), Tiến độ Kỹ năng & Bảng xếp hạng Tuần/Tháng."""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, time as datetime_time
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import Connection

from ..db import ex, q, q1
from ..errors import ApiError, bad_request, not_found

TIMEOUT_MS = int(os.environ.get("STATEMENT_TIMEOUT_MS", "10000"))
MAX_RESULT_ROWS = int(os.environ.get("MAX_RESULT_ROWS", "100000"))


def _enterprise_conninfo() -> dict:
    return {
        "host": os.environ.get("ENTERPRISE_DB_HOST", "localhost"),
        "port": int(os.environ.get("ENTERPRISE_DB_PORT", "5432")),
        "dbname": os.environ.get("ENTERPRISE_DB_NAME", "enterprise_db"),
        "user": os.environ.get("ENTERPRISE_DB_USER", "sqlarena_ai_ro"),
        "password": os.environ.get("ENTERPRISE_DB_PASSWORD", "sqlarena_ro"),
        "row_factory": dict_row,
    }


@contextmanager
def enterprise_connection():
    with psycopg.connect(**_enterprise_conninfo()) as conn:
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
    return str(value)


def stable_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def guard_select(sql: str) -> str:
    text = (sql or "").strip()
    if not text:
        raise ValueError("Truy vấn SQL đang để trống")
    if "--" in text or "/*" in text or "*/" in text:
        raise ValueError("Không chấp nhận comment SQL (-- hoặc /* */)")
    if text.endswith(";"):
        text = text[:-1].rstrip()
    if ";" in text:
        raise ValueError("Chỉ chấp nhận 1 câu lệnh SQL duy nhất")
    if not re.match(r"^(SELECT|WITH)\b", text, flags=re.IGNORECASE):
        raise ValueError("Chỉ chấp nhận câu lệnh SELECT hoặc WITH")
    forbidden = r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|CALL|DO|SET|RESET|GRANT|REVOKE|VACUUM|ANALYZE|REFRESH)\b"
    if re.search(forbidden, text, flags=re.IGNORECASE):
        raise ValueError("Sandbox chỉ cho phép truy vấn đọc (SELECT)")
    return text


def execute_sandbox_sql(sql: str) -> dict:
    with enterprise_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL TRANSACTION READ ONLY")
                cur.execute("SELECT set_config('statement_timeout', %s, true)", (f"{TIMEOUT_MS}ms",))
                cur.execute("SET LOCAL search_path = public")
                cur.execute(sql)
                columns = [item.name for item in cur.description]
                raw_rows = cur.fetchmany(MAX_RESULT_ROWS + 1)
                if len(raw_rows) > MAX_RESULT_ROWS:
                    raise ValueError(f"Kết quả vượt quá giới hạn {MAX_RESULT_ROWS} dòng")
                rows = [{name: json_value(value) for name, value in item.items()} for item in raw_rows]
                return {"columns": columns, "rows": rows, "row_count": len(rows)}


def _normalize_expected_rows(expected: dict) -> list[dict]:
    cols = expected.get("columns") or []
    raw_rows = expected.get("rows") or []
    if not raw_rows:
        return []
    if isinstance(raw_rows[0], dict):
        return [{k: json_value(v) for k, v in r.items()} for r in raw_rows]
    # Trường hợp rows lưu dạng list-of-lists (từ promote pipeline của Hưng)
    return [{col: json_value(val) for col, val in zip(cols, r)} for r in raw_rows]


def compare_result(actual: dict, expected: dict, compare_mode_override: str | None = None) -> bool:
    exp_cols = expected.get("columns") or []
    if actual["columns"] != exp_cols:
        return False
    actual_rows = actual["rows"]
    expected_rows = _normalize_expected_rows(expected)
    mode = compare_mode_override or expected.get("compare_mode") or "unordered"
    if mode == "ordered":
        return [stable_json(r) for r in actual_rows] == [stable_json(r) for r in expected_rows]
    return Counter(stable_json(row) for row in actual_rows) == Counter(stable_json(row) for row in expected_rows)


def run_query(conn: Connection, user_id: int, question_id: int, raw_sql: str) -> dict:
    q_row = q1(conn, "SELECT question_id FROM live.questions WHERE question_id=:q", q=question_id)
    if not q_row:
        raise not_found("Không tìm thấy câu hỏi")
    try:
        clean_sql = guard_select(raw_sql)
        res = execute_sandbox_sql(clean_sql)
        return {"passed_policy": True, "saved": False, **res}
    except Exception as exc:
        raise bad_request(str(exc))


def submit_query(conn: Connection, user_id: int, question_id: int, raw_sql: str) -> dict:
    q_row = q1(
        conn,
        """SELECT q.question_id, q.compare_mode,
                  (SELECT i.set_id FROM live.weekly_set_items i JOIN live.weekly_sets s USING (set_id)
                   WHERE i.question_id=q.question_id AND s.status='published' LIMIT 1) AS active_set_id
           FROM live.questions q
           WHERE q.question_id=:q""",
        q=question_id,
    )
    if not q_row:
        raise not_found("Không tìm thấy câu hỏi")
    tcs = q(
        conn,
        "SELECT test_id, dataset_ref, type, expected_result, is_hidden FROM live.test_cases WHERE question_id=:q ORDER BY test_id",
        q=question_id,
    )
    if not tcs:
        raise ApiError(409, "MISSING_TEST_CASES", "Câu hỏi chưa có bộ test case chuẩn để chấm")
    try:
        clean_sql = guard_select(raw_sql)
    except ValueError as exc:
        raise bad_request(str(exc))

    result = None
    error = None
    passed = False
    test_details = []
    started = time.perf_counter()
    try:
        result = execute_sandbox_sql(clean_sql)
        all_ok = True
        for tc in tcs:
            exp = tc["expected_result"] if isinstance(tc["expected_result"], dict) else json.loads(tc["expected_result"])
            tc_ok = compare_result(result, exp, q_row["compare_mode"])
            test_details.append({
                "test_id": tc["test_id"],
                "dataset_ref": tc["dataset_ref"],
                "type": tc["type"],
                "passed": tc_ok,
                "expected_rows": exp.get("row_count"),
                "actual_rows": result["row_count"],
            })
            if not tc_ok:
                all_ok = False
        passed = all_ok
        if not passed:
            error = "Kết quả truy vấn chưa khớp với expected_result của bộ test case"
    except Exception as exc:
        error = str(exc)

    runtime_ms = round((time.perf_counter() - started) * 1000)
    sub_status = "passed" if passed else ("error" if result is None else "failed")
    exec_status = "passed" if result is not None and error is None else "error"
    sub_row = q1(
        conn,
        """INSERT INTO live.submissions
           (user_id, question_id, set_id, submitted_sql, submission_status, execution_status, score, result_json, error_message, runtime_ms)
           VALUES (:u, :q, :s, :sql, :st, :est, :sc, CAST(:res AS jsonb), :err, :rt)
           RETURNING submission_id, submitted_at""",
        u=user_id,
        q=question_id,
        s=q_row["active_set_id"],
        sql=clean_sql,
        st=sub_status,
        est=exec_status,
        sc=100 if passed else 0,
        res=json.dumps(result, ensure_ascii=False) if result else None,
        err=error,
        rt=runtime_ms,
    )
    # Cập nhật pass_rate trên live.questions
    ex(
        conn,
        """UPDATE live.questions
           SET pass_rate = (
             SELECT ROUND(COUNT(*) FILTER (WHERE submission_status='passed')::numeric / GREATEST(COUNT(*), 1), 4)
             FROM live.submissions WHERE question_id=:q
           )
           WHERE question_id=:q""",
        q=question_id,
    )
    return {
        "submission_id": sub_row["submission_id"],
        "question_id": question_id,
        "passed": passed,
        "submission_status": sub_status,
        "score": 100 if passed else 0,
        "saved": True,
        "error": error,
        "runtime_ms": runtime_ms,
        "row_count": result["row_count"] if result else None,
        "columns": result["columns"] if result else [],
        "rows": result["rows"][:100] if result else [],
        "test_cases": test_details,
        "submitted_at": sub_row["submitted_at"],
    }


def user_progress(conn: Connection, user_id: int) -> dict:
    s = q1(conn, "SELECT set_id, title, week_start FROM live.weekly_sets WHERE status='published' LIMIT 1")
    skills = q(
        conn,
        """WITH wk_q AS (
             SELECT qq.question_id, unnest(qq.skill_ids) AS skill_id
             FROM live.weekly_set_items i
             JOIN live.weekly_sets ws USING (set_id)
             JOIN live.questions qq USING (question_id)
             WHERE ws.status='published' AND NOT i.is_voided
           ), solved_q AS (
             SELECT DISTINCT question_id
             FROM live.submissions
             WHERE user_id=:u AND submission_status='passed'
           )
           SELECT sk.skill_id, sk.code, sk.name, sk.category,
                  COUNT(DISTINCT wq.question_id) AS total_questions,
                  COUNT(DISTINCT wq.question_id) FILTER (WHERE sq.question_id IS NOT NULL) AS passed_questions
           FROM core.skills sk
           LEFT JOIN wk_q wq ON wq.skill_id = sk.skill_id
           LEFT JOIN solved_q sq ON sq.question_id = wq.question_id
           WHERE sk.is_active
           GROUP BY sk.skill_id, sk.code, sk.name, sk.category
           ORDER BY sk.skill_id""",
        u=user_id,
    )
    skill_items = [
        {
            **r,
            "percent": round(r["passed_questions"] * 100 / r["total_questions"]) if r["total_questions"] else 0,
        }
        for r in skills
    ]
    recent = q(
        conn,
        """SELECT s.submission_id, s.question_id, qq.title AS question_title, qq.difficulty,
                  s.submission_status, s.score, s.runtime_ms, s.submitted_at, s.error_message
           FROM live.submissions s
           JOIN live.questions qq USING (question_id)
           WHERE s.user_id=:u
           ORDER BY s.submitted_at DESC
           LIMIT 20""",
        u=user_id,
    )
    totals = q1(
        conn,
        """SELECT count(*) AS total_submissions,
                  count(*) FILTER (WHERE submission_status='passed') AS passed_submissions,
                  count(DISTINCT question_id) FILTER (WHERE submission_status='passed') AS solved_questions,
                  count(DISTINCT question_id) AS attempted_questions
           FROM live.submissions
           WHERE user_id=:u""",
        u=user_id,
    )
    total_sub = totals["total_submissions"] or 0
    passed_sub = totals["passed_submissions"] or 0
    return {
        "weekly_set": s,
        "summary": {
            "total_submissions": total_sub,
            "passed_submissions": passed_sub,
            "solved_questions": totals["solved_questions"] or 0,
            "attempted_questions": totals["attempted_questions"] or 0,
            "accuracy_percent": round(passed_sub * 100 / total_sub) if total_sub else 0,
        },
        "skills": skill_items,
        "recent_submissions": recent,
    }


def weekly_leaderboard(conn: Connection, set_id: int | None = None) -> dict:
    if set_id is not None:
        ws = q1(conn, "SELECT set_id, title, week_start, status, published_at, closed_at FROM live.weekly_sets WHERE set_id=:s", s=set_id)
    else:
        ws = q1(conn, "SELECT set_id, title, week_start, status, published_at, closed_at FROM live.weekly_sets WHERE status='published' ORDER BY week_start DESC LIMIT 1")
    if not ws:
        raise not_found("Chưa có bộ đề tuần đang mở")
    total_q = q1(conn, "SELECT count(*) AS n FROM live.weekly_set_items WHERE set_id=:s AND NOT is_voided", s=ws["set_id"])["n"]
    rows = q(
        conn,
        """WITH valid_items AS (
             SELECT question_id FROM live.weekly_set_items WHERE set_id=:s AND NOT is_voided
           ), first_pass AS (
             SELECT DISTINCT ON (sub.user_id, sub.question_id)
                    sub.user_id, sub.question_id, sub.submitted_at AS first_passed_at, sub.runtime_ms
             FROM live.submissions sub
             JOIN valid_items vi USING (question_id)
             WHERE sub.submission_status = 'passed'
             ORDER BY sub.user_id, sub.question_id, sub.submitted_at, sub.submission_id
           ), scores AS (
             SELECT user_id,
                    COUNT(*)::int AS correct_count,
                    COUNT(*)::int * 100 AS total_score,
                    MAX(first_passed_at) AS completed_at,
                     COALESCE(AVG(runtime_ms)::int, 0) AS avg_runtime_ms
             FROM first_pass
             GROUP BY user_id
           )
           SELECT ROW_NUMBER() OVER (ORDER BY sc.correct_count DESC, sc.completed_at ASC, sc.user_id ASC)::int AS rank,
                  sc.user_id, u.username, COALESCE(u.display_name, u.username) AS display_name,
                  sc.correct_count, sc.total_score, sc.completed_at, sc.avg_runtime_ms
           FROM scores sc
           JOIN live.users u USING (user_id)
           WHERE u.status = 'active'
           ORDER BY rank""",
        s=ws["set_id"],
    )
    return {
        "set": ws,
        "total_questions": total_q,
        "items": rows,
    }


def monthly_leaderboard(conn: Connection, year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    y = year or today.year
    m = month or today.month
    try:
        m_start = date(y, m, 1)
    except ValueError:
        raise bad_request("Năm hoặc tháng không hợp lệ")
    next_m = date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

    total_q = q1(
        conn,
        """SELECT COUNT(DISTINCT i.question_id)::int AS n
           FROM live.weekly_sets ws
           JOIN live.weekly_set_items i USING (set_id)
           WHERE ws.status IN ('published', 'closed')
             AND ws.week_start >= :ms AND ws.week_start < :nm
             AND NOT i.is_voided""",
        ms=m_start,
        nm=next_m,
    )["n"]

    rows = q(
        conn,
        """WITH monthly_q AS (
             SELECT DISTINCT i.question_id
             FROM live.weekly_sets ws
             JOIN live.weekly_set_items i USING (set_id)
             WHERE ws.status IN ('published', 'closed')
               AND ws.week_start >= :ms AND ws.week_start < :nm
               AND NOT i.is_voided
           ), first_pass AS (
             SELECT DISTINCT ON (sub.user_id, sub.question_id)
                    sub.user_id, sub.question_id, sub.submitted_at AS first_passed_at, sub.runtime_ms
             FROM live.submissions sub
             JOIN monthly_q mq USING (question_id)
             WHERE sub.submission_status = 'passed'
             ORDER BY sub.user_id, sub.question_id, sub.submitted_at, sub.submission_id
           ), scores AS (
             SELECT user_id,
                    COUNT(*)::int AS correct_count,
                    COUNT(*)::int * 100 AS total_score,
                    MAX(first_passed_at) AS completed_at,
                    COALESCE(AVG(runtime_ms)::int, 0) AS avg_runtime_ms
             FROM first_pass
             GROUP BY user_id
           )
           SELECT ROW_NUMBER() OVER (ORDER BY sc.correct_count DESC, sc.completed_at ASC, sc.user_id ASC)::int AS rank,
                  sc.user_id, u.username, COALESCE(u.display_name, u.username) AS display_name,
                  sc.correct_count, sc.total_score, sc.completed_at, sc.avg_runtime_ms
           FROM scores sc
           JOIN live.users u USING (user_id)
           WHERE u.status = 'active'
           ORDER BY rank""",
        ms=m_start,
        nm=next_m,
    )
    return {
        "period": {"year": y, "month": m},
        "total_questions": total_q,
        "items": rows,
    }
