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


def diagnose_mismatch(actual: dict, expected: dict, compare_mode_override: str | None = None) -> dict:
    exp_cols = expected.get("columns") or []
    act_cols = actual.get("columns") or []
    if act_cols != exp_cols:
        return {
            "reason_code": "COLUMN_MISMATCH",
            "hint": f"Sai tên hoặc thứ tự cột: cần {exp_cols}, nhưng truy vấn trả về {act_cols}.",
        }
    expected_rows = _normalize_expected_rows(expected)
    actual_rows = actual.get("rows") or []
    exp_count = expected.get("row_count", len(expected_rows))
    act_count = actual.get("row_count", len(actual_rows))
    if act_count != exp_count:
        return {
            "reason_code": "ROW_COUNT_DIFF",
            "hint": f"Lệch số dòng kết quả: cần {exp_count} dòng, nhưng trả về {act_count} dòng (kiểm tra lại điều kiện WHERE / JOIN / GROUP BY).",
        }
    mode = compare_mode_override or expected.get("compare_mode") or "unordered"
    unordered_match = Counter(stable_json(r) for r in actual_rows) == Counter(stable_json(r) for r in expected_rows)
    if mode == "ordered" and unordered_match:
        return {
            "reason_code": "ORDER_MISMATCH",
            "hint": "Dữ liệu đúng nhưng sai thứ tự sắp xếp! Hãy kiểm tra lại mệnh đề ORDER BY.",
        }
    return {
        "reason_code": "VALUE_MISMATCH",
        "hint": "Giá trị dữ liệu trong các dòng chưa khớp với đáp án chuẩn (kiểm tra công thức tính toán hoặc xử lý NULL).",
    }


def _walk_plan_nodes(plan_node: dict, out: list[dict], warnings: list[str]) -> None:
    node_type = plan_node.get("Node Type", "Plan")
    rel = plan_node.get("Relation Name") or plan_node.get("Alias") or "-"
    actual_rows = plan_node.get("Actual Rows", 0)
    out.append({
        "node_type": node_type,
        "relation_name": rel,
        "startup_cost": plan_node.get("Startup Cost", 0),
        "total_cost": plan_node.get("Total Cost", 0),
        "plan_rows": plan_node.get("Plan Rows", 0),
        "actual_rows": actual_rows,
        "actual_total_time_ms": plan_node.get("Actual Total Time", 0),
        "filter": plan_node.get("Filter") or plan_node.get("Hash Cond") or plan_node.get("Sort Key"),
    })
    if node_type == "Seq Scan" and actual_rows and actual_rows > 100:
        warnings.append(f"Quét tuần tự (Seq Scan) trên bảng '{rel}' ({actual_rows} dòng) — cân nhắc lọc sớm hoặc dùng cột có Index.")
    for child in plan_node.get("Plans") or []:
        _walk_plan_nodes(child, out, warnings)


def explain_query(conn: Connection, question_id: int, raw_sql: str) -> dict:
    q_row = q1(conn, "SELECT question_id FROM live.questions WHERE question_id=:q", q=question_id)
    if not q_row:
        raise not_found("Không tìm thấy câu hỏi")
    try:
        clean_sql = guard_select(raw_sql)
    except ValueError as exc:
        raise bad_request(str(exc))
    try:
        with enterprise_connection() as econn:
            with econn.cursor() as cur:
                cur.execute("SET LOCAL TRANSACTION READ ONLY")
                cur.execute("SET LOCAL statement_timeout = 3000")
                cur.execute(f"EXPLAIN (ANALYZE, COSTS, FORMAT JSON) {clean_sql}")
                raw = cur.fetchone()[0]
                plan_list = raw if isinstance(raw, list) else json.loads(raw)
                top = plan_list[0] if plan_list else {}
                root_plan = top.get("Plan") or {}
                nodes: list[dict] = []
                warnings: list[str] = []
                if root_plan:
                    _walk_plan_nodes(root_plan, nodes, warnings)
                return {
                    "question_id": question_id,
                    "planning_time_ms": top.get("Planning Time", 0),
                    "execution_time_ms": top.get("Execution Time", 0),
                    "total_cost": root_plan.get("Total Cost", 0),
                    "plan_nodes": nodes,
                    "warnings": warnings,
                }
    except Exception as exc:
        raise bad_request(str(exc))


def question_submissions(conn: Connection, user_id: int | None, question_id: int) -> dict:
    if not user_id:
        return {"items": []}
    rows = q(
        conn,
        """SELECT submission_id, question_id, submitted_sql, submission_status,
                  execution_status, score, runtime_ms, error_message, submitted_at
           FROM live.submissions
           WHERE user_id = :u AND question_id = :q
           ORDER BY submitted_at DESC
           LIMIT 15""",
        u=user_id,
        q=question_id,
    )
    return {"items": rows}


def ai_coach_assist(
    conn: Connection, question_id: int, raw_sql: str, mode: str = "review", prompt: str | None = None
) -> dict:
    q_row = q1(
        conn,
        """SELECT question_id, title, question, difficulty, skill_ids, tables_used, compare_mode
           FROM live.questions WHERE question_id=:q""",
        q=question_id,
    )
    if not q_row:
        raise not_found("Không tìm thấy câu hỏi")

    tables = q_row.get("tables_used") or ["employees"]
    primary_tbl = tables[0] if tables else "employees"
    join_tbl = tables[1] if len(tables) > 1 else None
    up_sql = (raw_sql or "").upper()
    skills = set(q_row.get("skill_ids") or [])
    tc_row = q1(
        conn,
        "SELECT expected_result FROM live.test_cases WHERE question_id=:q ORDER BY test_id LIMIT 1",
        q=question_id,
    )
    exp = tc_row["expected_result"] if tc_row else {}
    if isinstance(exp, str):
        exp = json.loads(exp)
    exp_cols = exp.get("columns") or ["*"]
    col_str = ", ".join(exp_cols)

    # Skeleton SQL template tailored to question metadata
    skel_lines = [f"SELECT {col_str}", f"FROM {primary_tbl} t1"]
    if join_tbl:
        skel_lines.append(f"JOIN {join_tbl} t2 ON t1.<fk_id> = t2.<pk_id>")
    if 2 in skills or "COUNT" in q_row["question"].upper() or "TỔNG" in q_row["question"].upper():
        skel_lines.append(f"GROUP BY {exp_cols[0]}")
    if q_row.get("compare_mode") == "ORDER_SENSITIVE":
        skel_lines.append(f"ORDER BY {exp_cols[0]} ASC")
    suggested_sql = "\n".join(skel_lines) + ";"

    if mode == "nl2sql":
        user_intent = (prompt or q_row["question"]).strip()
        return {
            "question_id": question_id,
            "mode": "nl2sql",
            "headline": "✨ AI Text-to-SQL Blueprint (Chuẩn Schema Thực Tế)",
            "clean_score": 92,
            "insights": [
                f"Ý định phân tích: \"{user_intent[:140]}\"",
                f"Bảng mục tiêu cần kết nối: {', '.join(tables)}",
                f"Đầu ra chuẩn ({len(exp_cols)} cột): {col_str}",
                "Mẹo thời đại AI: Khi viết prompt cho AI sinh SQL, luôn chỉ rõ tên cột output và chế độ sắp xếp (ORDER BY) để tránh sai lệch schema.",
            ],
            "suggested_sql": suggested_sql,
            "interview_q": None,
            "interview_answer": None,
        }

    if mode == "interview":
        if 5 in skills:
            iq = f"Nếu bảng {', '.join(tables)} tăng lên 50 triệu dòng, hàm cửa sổ (Window Function) hoặc CTE trong bài '{q_row['title']}' sẽ gây nghẽn ở bước nào?"
            ia = "Window Function yêu cầu bước Sort trên Partition Key. Để tối ưu ở quy mô 50M dòng, cần đánh Composite B-Tree Index theo đúng thứ tự (PARTITION BY col, ORDER BY col) nhằm chuyển Sort sang Index Scan."
        elif len(tables) > 1 or 3 in skills:
            iq = f"Khi JOIN giữa {', '.join(tables)}, nếu xuất hiện bản ghi NULL hoặc nhân bản (fan-out) làm sai lệch phép cộng/đếm, bạn xử lý thế nào?"
            ia = "Sử dụng LEFT JOIN kết hợp COALESCE(SUM(...), 0) nếu cần giữ bản ghi gốc có giá trị 0, hoặc gom nhóm (Pre-aggregate) trong CTE trước khi JOIN để chống hiện tượng fan-out nhân bản dòng."
        else:
            iq = f"Làm sao để tối ưu truy vấn trên bảng {primary_tbl} đạt thời gian phản hồi < 10ms mà không quét toàn bảng (Seq Scan)?"
            ia = f"Tạo Covering Index (CREATE INDEX ON {primary_tbl} (<filter_col>) INCLUDE ({', '.join(exp_cols[:2])})) để PostgreSQL thực hiện Index-Only Scan mà không cần đọc Heap Page."
        return {
            "question_id": question_id,
            "mode": "interview",
            "headline": "🎙️ Phỏng vấn Data Engineer Thực Chiến (AI Mock Interviewer)",
            "clean_score": 95,
            "insights": [
                f"Chủ đề trọng tâm: {q_row['title']} (Độ khó Lv.{q_row['difficulty']})",
                "Trong phỏng vấn thực tế thời đại AI, nhà tuyển dụng không chỉ chấm đúng kết quả mà còn hỏi sâu về Index, Edge Cases (NULL/Ties) và Chi phí thực thi (Query Cost).",
            ],
            "suggested_sql": suggested_sql,
            "interview_q": iq,
            "interview_answer": ia,
        }

    # Default mode == "review"
    score = 88
    insights: list[str] = []
    if "SELECT *" in up_sql:
        score -= 15
        insights.append(f"⚠️ Tránh dùng `SELECT *`: Bài toán yêu cầu chính xác các cột `{col_str}`. Chỉ lấy đúng cột giúp giảm I/O và khớp Test Case.")
    else:
        insights.append(f"✅ Cấu trúc SELECT rõ ràng: Đã chủ động chọn lọc cột hướng tới `{col_str}`.")

    missing_tbls = [t for t in tables if t.upper() not in up_sql]
    if missing_tbls:
        score -= 18
        insights.append(f"🔍 Thiếu bảng liên kết: Đề bài cần dữ liệu từ `{', '.join(missing_tbls)}`. Hãy kiểm tra khóa ngoại để JOIN đầy đủ.")
    else:
        insights.append(f"✅ Đã tham chiếu đầy đủ bảng dữ liệu mục tiêu (`{', '.join(tables)}`).")

    if q_row.get("compare_mode") == "ORDER_SENSITIVE" and "ORDER BY" not in up_sql:
        score -= 12
        insights.append("📐 Chế độ chấm `ORDER_SENSITIVE`: Bạn cần thêm mệnh đề `ORDER BY` để đảm bảo thứ tự dòng khớp 100% với bộ chấm.")

    if 5 in skills and "OVER" not in up_sql and "WITH " not in up_sql:
        score -= 10
        insights.append("💡 Gợi ý nâng cao: Bài này thuộc nhóm CTE & Window Functions (`S5`). Hãy cân nhắc dùng `WITH ... AS (...)` hoặc `OVER (PARTITION BY ...)` để code mạch lạc hơn.")

    return {
        "question_id": question_id,
        "mode": "review",
        "headline": f"🤖 AI Code Review · Điểm Clean SQL: {max(score, 45)}/100",
        "clean_score": max(score, 45),
        "insights": insights,
        "suggested_sql": suggested_sql,
        "interview_q": None,
        "interview_answer": None,
    }



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
            diag = (
                {"reason_code": "PASSED", "hint": "Khớp hoàn toàn với đáp án chuẩn."}
                if tc_ok
                else diagnose_mismatch(result, exp, q_row["compare_mode"])
            )
            exp_norm_rows = _normalize_expected_rows(exp)
            test_details.append({
                "test_id": tc["test_id"],
                "dataset_ref": tc["dataset_ref"],
                "type": tc["type"],
                "passed": tc_ok,
                "expected_rows": exp.get("row_count"),
                "actual_rows": result["row_count"],
                "reason_code": diag["reason_code"],
                "diagnostic_hint": diag["hint"],
                "expected_columns": exp.get("columns") or [],
                "actual_columns": result["columns"],
                "expected_preview": exp_norm_rows[:5] if not tc.get("is_hidden") else [],
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
    solved_q = totals["solved_questions"] or 0
    acc_pct = round(passed_sub * 100 / total_sub) if total_sub else 0

    xp_row = q1(
        conn,
        """SELECT COALESCE(SUM(qq.difficulty * 120), 0)::int AS base_xp,
                  COALESCE(MIN(s.runtime_ms), 999) AS fastest_ms
           FROM (
             SELECT DISTINCT ON (question_id) question_id, runtime_ms
             FROM live.submissions
             WHERE user_id=:u AND submission_status='passed'
             ORDER BY question_id, runtime_ms ASC
           ) s
           JOIN live.questions qq USING (question_id)""",
        u=user_id,
    )
    xp = (xp_row["base_xp"] if xp_row else 0) + passed_sub * 15
    tiers = [
        (0, 1, "SQL Explorer", 300),
        (300, 2, "Junior Data Analyst", 700),
        (700, 3, "Analytics Engineer", 1200),
        (1200, 4, "AI-Native Data Engineer", 2000),
        (2000, 5, "Principal Data Architect", 3500),
    ]
    lvl, lvl_title, next_xp = 1, "SQL Explorer", 300
    for min_x, lv, title, nx in tiers:
        if xp >= min_x:
            lvl, lvl_title, next_xp = lv, title, nx

    badges = [
        {"id": "first_blood", "icon": "⚡", "name": "First Query Passed", "desc": "Giải thành công bài SQL đầu tiên", "unlocked": solved_q >= 1},
        {"id": "speed_demon", "icon": "🚀", "name": "Sub-15ms Optimizer", "desc": "Truy vấn thực thi dưới 15ms trên Sandbox", "unlocked": (xp_row["fastest_ms"] if xp_row else 999) <= 15 and solved_q >= 1},
        {"id": "join_master", "icon": "🔗", "name": "Multi-Table Architect", "desc": "Hoàn thành ít nhất 3 bài truy vấn chuẩn", "unlocked": solved_q >= 3},
        {"id": "high_precision", "icon": "🎯", "name": "AI-Era Precision", "desc": "Đạt tỷ lệ chính xác >= 70%", "unlocked": acc_pct >= 70 and total_sub >= 2},
        {"id": "weekly_champion", "icon": "👑", "name": "Full-Stack Data Pro", "desc": "Chinh phục >= 6 thử thách SQL", "unlocked": solved_q >= 6},
    ]
    weakest = min(skill_items, key=lambda x: (x["percent"], -x["total_questions"])) if skill_items else None
    ai_rec = {
        "focus_skill": f"{weakest['code']} · {weakest['name']}" if weakest else "S3 · JOIN & Subquery",
        "percent": weakest["percent"] if weakest else 0,
        "advice": (
            f"AI Coach nhận thấy kỹ năng {weakest['code']} ({weakest['name']}) đang ở mức {weakest['percent']}%. "
            "Hãy ưu tiên luyện 1–2 bài thuộc nhóm này và bật chế độ '🤖 AI Coach → Phỏng vấn AI' để nắm vững cách tối ưu truy vấn thực chiến!"
        ) if weakest else "Hãy bắt đầu với bài Dễ (Difficulty 1) và dùng AI Coach để kiểm tra Execution Plan.",
    }
    return {
        "weekly_set": s,
        "summary": {
            "total_submissions": total_sub,
            "passed_submissions": passed_sub,
            "solved_questions": solved_q,
            "attempted_questions": totals["attempted_questions"] or 0,
            "accuracy_percent": acc_pct,
        },
        "career": {
            "xp": xp,
            "level": lvl,
            "level_title": lvl_title,
            "next_level_xp": next_xp,
            "progress_percent": min(100, round(xp * 100 / max(next_xp, 1))),
            "badges": badges,
            "ai_recommendation": ai_rec,
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
