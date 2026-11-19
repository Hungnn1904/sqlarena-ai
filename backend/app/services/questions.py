"""Câu hỏi đã xuất bản (live.questions): API cho người học + quản trị (list/detail/retire/restore/source/manual)."""
import json
import re

from sqlalchemy import Connection

from ..db import ex, q, q1
from ..errors import bad_request, conflict, not_found
from ..pipeline import engine as eng
from . import audit, submissions, weekly


def _skills(conn: Connection) -> dict[int, dict]:
    return {r["skill_id"]: r for r in q(conn, "SELECT skill_id, code, name FROM core.skills")}


def dataset_schema(conn: Connection) -> dict:
    w = q1(conn, "SELECT name, dataset_version, schema_description, fk_relations FROM core.worlds WHERE is_active ORDER BY world_id LIMIT 1")
    if not w:
        raise not_found("Chưa có world")
    refs = {}
    for fk in w["fk_relations"]:
        for c, rc in zip(fk["columns"], fk["referenced_columns"]):
            refs[(fk["table_name"], c)] = f"{fk['referenced_table']}.{rc}"
    tables = []
    for t in w["schema_description"]["tables"]:
        pk = set(t.get("primary_key") or [])
        tables.append({"name": t["table"], "columns": [{"name": c["name"], "type": c["postgres_type"], "nullable": c["nullable"],
                                                         "pk": c["name"] in pk, **({"references": refs[(t["table"], c["name"])]} if (t["table"], c["name"]) in refs else {})}
                                                        for c in t["columns"]]})
    return {"name": w["name"], "version": w["dataset_version"], "tables": tables}


def admin_list(conn: Connection, status, difficulty, skill_id, search, page: int, size: int, unassigned_only: bool = False) -> dict:
    conds, p = [], {}
    if unassigned_only:
        conds.append("q.status='ready'")
        conds.append("NOT EXISTS (SELECT 1 FROM live.weekly_set_items wsi WHERE wsi.question_id = q.question_id)")
    if status:
        conds.append("q.status=:st"); p["st"] = status
    if difficulty:
        conds.append("q.difficulty=:d"); p["d"] = difficulty
    if skill_id:
        conds.append("q.skill_ids @> ARRAY[:s]::int[]"); p["s"] = skill_id
    if search and search.strip():
        tokens = [tok for tok in search.strip().split() if tok]
        for idx, tok in enumerate(tokens):
            key = f"tk_{idx}"
            esc = tok.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            p[key] = f"%{esc}%"
            conds.append(
                f"""(
                  ('#' || q.question_id::text) ILIKE :{key} ESCAPE '\\'
                  OR q.title ILIKE :{key} ESCAPE '\\'
                  OR q.question ILIKE :{key} ESCAPE '\\'
                  OR array_to_string(q.tables_used, ' ') ILIKE :{key} ESCAPE '\\'
                  OR q.status ILIKE :{key} ESCAPE '\\'
                  OR EXISTS (
                    SELECT 1 FROM live.weekly_set_items wsi
                    JOIN live.weekly_sets ws USING (set_id)
                    WHERE wsi.question_id = q.question_id
                      AND ws.status = 'published'
                      AND ('SQL' || wsi.position::text) ILIKE :{key} ESCAPE '\\'
                  )
                )"""
            )
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = q1(conn, f"SELECT count(*) AS n FROM live.questions q {where}", **p)["n"]
    has_groups_tbl = bool(conn.execute(q1.__globals__["text"]("SELECT to_regclass('live.question_group_items') IS NOT NULL")).scalar())
    group_col_sql = (
        "ARRAY(SELECT gi.group_id FROM live.question_group_items gi WHERE gi.question_id = q.question_id ORDER BY gi.group_id) AS group_ids"
        if has_groups_tbl
        else "ARRAY[]::int[] AS group_ids"
    )
    rows = q(
        conn,
        f"""SELECT q.question_id, q.title, q.difficulty, q.skill_ids, q.tables_used, q.status,
                   q.is_source, q.is_flagged, q.pass_rate, q.source_draft_id, q.created_at, q.retired_at,
                   d.job_id, j.topic AS job_topic,
                   COALESCE(d.blueprint->'candidate'->>'business_domain', d.blueprint->>'business_domain') AS blueprint_domain,
                   (SELECT i.set_id FROM live.weekly_set_items i WHERE i.question_id = q.question_id LIMIT 1) AS weekly_set_id,
                   (SELECT i.position FROM live.weekly_set_items i
                    JOIN live.weekly_sets ws ON ws.set_id = i.set_id
                    WHERE i.question_id = q.question_id AND ws.status = 'published'
                    ORDER BY ws.week_start DESC, ws.set_id DESC LIMIT 1) AS weekly_position,
                   {group_col_sql}
            FROM live.questions q
            LEFT JOIN draft.question_drafts d ON d.draft_id = q.source_draft_id
            LEFT JOIN draft.generation_jobs j ON j.job_id = d.job_id
            {where}
            ORDER BY q.question_id DESC LIMIT :l OFFSET :o""",
        l=size,
        o=(page - 1) * size,
        **p,
    )
    smap = _skills(conn)
    items = []
    for r in rows:
        domain_category, topic = weekly._infer_domain_and_topic(r["tables_used"], r["job_topic"], r["blueprint_domain"])
        sids = r["skill_ids"] or []
        items.append({
            **r,
            "tables_used": r["tables_used"] or [],
            "source_type": "ai_generated" if r["source_draft_id"] is not None else "seed",
            "job_id": r["job_id"],
            "job_topic": r["job_topic"],
            "topic": topic,
            "domain_category": domain_category,
            "weekly_position": r["weekly_position"],
            "in_weekly_set": r["weekly_set_id"] is not None,
            "in_published_set": r["weekly_position"] is not None,
            "group_ids": list(r["group_ids"] or []),
            "skill_codes": [smap[i]["code"] for i in sids if i in smap],
            "skills": [smap[i]["name"] for i in sids if i in smap],
        })
    return {"items": items, "total": total, "page": page, "page_size": size}


def admin_detail(conn: Connection, question_id: int) -> dict:
    r = q1(
        conn,
        """SELECT q.*, d.job_id, j.topic AS job_topic,
                  COALESCE(d.blueprint->'candidate'->>'business_domain', d.blueprint->>'business_domain') AS blueprint_domain,
                  (SELECT i.position FROM live.weekly_set_items i
                   JOIN live.weekly_sets ws ON ws.set_id = i.set_id
                   WHERE i.question_id = q.question_id AND ws.status = 'published'
                   ORDER BY ws.week_start DESC, ws.set_id DESC LIMIT 1) AS weekly_position
           FROM live.questions q
           LEFT JOIN draft.question_drafts d ON d.draft_id = q.source_draft_id
           LEFT JOIN draft.generation_jobs j ON j.job_id = d.job_id
           WHERE q.question_id=:i""",
        i=question_id,
    )
    if not r:
        raise not_found("Không tìm thấy câu hỏi")
    tests = q(conn, "SELECT test_id, dataset_ref, dataset_version, type, is_hidden, expected_result->>'row_count' AS row_count, "
                    "expected_result->>'result_hash' AS result_hash, expected_result->>'compare_mode' AS compare_mode FROM live.test_cases WHERE question_id=:i ORDER BY test_id", i=question_id)
    skill_rows = [s for s in q(conn, "SELECT skill_id, code, name FROM core.skills WHERE skill_id = ANY(:s)", s=list(r["skill_ids"] or []))]
    domain_category, topic = weekly._infer_domain_and_topic(r["tables_used"], r["job_topic"], r["blueprint_domain"])
    r["skills"] = skill_rows
    r["skill_codes"] = [s["code"] for s in skill_rows]
    r["source_type"] = "ai_generated" if r["source_draft_id"] is not None else "seed"
    r["domain_category"] = domain_category
    r["topic"] = topic
    r["test_cases"] = tests
    r["weekly"] = q1(conn, "SELECT i.set_id, i.position, i.is_voided, s.status AS set_status FROM live.weekly_set_items i JOIN live.weekly_sets s USING (set_id) "
                           "WHERE i.question_id=:i", i=question_id)
    return r


def retire(conn: Connection, admin: dict, question_id: int, reason: str) -> dict:
    n = ex(conn, "UPDATE live.questions SET status='retired', retired_at=now(), retire_reason=:r WHERE question_id=:i AND status <> 'retired'", r=reason, i=question_id)
    if n == 0:
        cur = q1(conn, "SELECT status FROM live.questions WHERE question_id=:i", i=question_id)
        if not cur:
            raise not_found("Không tìm thấy câu hỏi")
        raise conflict("INVALID_STATE", "Câu hỏi đã retired")
    ex(conn, "INSERT INTO live.admin_overrides (admin_id, question_id, action, note) VALUES (:a, :q, 'retire', :n)", a=admin["user_id"], q=question_id, n=reason)
    effect = weekly.on_question_retired(conn, question_id)
    audit.log(conn, admin["user_id"], "question.retire", "question", question_id, {"reason": reason, "weekly_effect": effect})
    return {**admin_detail(conn, question_id), "weekly_effect": effect}


def restore(conn: Connection, admin: dict, question_id: int, note: str | None) -> dict:
    cur = q1(conn, "SELECT status FROM live.questions WHERE question_id=:i FOR UPDATE", i=question_id)
    if not cur:
        raise not_found("Không tìm thấy câu hỏi")
    if cur["status"] != "retired":
        raise conflict("INVALID_STATE", f"Chỉ câu hỏi retired mới restore được (hiện: {cur['status']})")
    # Hợp đồng v7: chỉ restore nếu chưa từng gán vào bộ đề (UNIQUE(question_id) ⇒ còn dòng item là đã từng gán).
    if q1(conn, "SELECT 1 AS x FROM live.weekly_set_items WHERE question_id=:i", i=question_id):
        raise conflict("QUESTION_ALREADY_USED", "Câu hỏi đã từng được gán vào bộ đề; không restore được")
    ex(conn, "UPDATE live.questions SET status='ready', retired_at=NULL, retire_reason=NULL WHERE question_id=:i", i=question_id)
    ex(conn, "INSERT INTO live.admin_overrides (admin_id, question_id, action, note) VALUES (:a, :q, 'restore', :n)", a=admin["user_id"], q=question_id, n=note)
    audit.log(conn, admin["user_id"], "question.restore", "question", question_id, {"note": note})
    return admin_detail(conn, question_id)


def set_source(conn: Connection, admin: dict, question_id: int, is_source: bool) -> dict:
    if not ex(conn, "UPDATE live.questions SET is_source=:s WHERE question_id=:i", s=is_source, i=question_id):
        raise not_found("Không tìm thấy câu hỏi")
    audit.log(conn, admin["user_id"], "question.source", "question", question_id, {"is_source": is_source})
    return admin_detail(conn, question_id)


def create_manual(conn: Connection, admin: dict, payload: dict) -> dict:
    w = q1(conn, "SELECT world_id, dataset_version, schema_description FROM core.worlds WHERE is_active ORDER BY world_id LIMIT 1")
    if not w:
        raise not_found("Chưa có world hoạt động")
    valid_skills = set(_skills(conn).keys())
    skill_ids = list(dict.fromkeys(payload["skill_ids"]))
    if not skill_ids or any(sid not in valid_skills for sid in skill_ids):
        raise bad_request("Danh sách skill_ids không hợp lệ", {"skill_ids": skill_ids})
    try:
        clean_sql = submissions.guard_select(payload["reference_sql"])
        exec_res = submissions.execute_sandbox_sql(clean_sql)
    except Exception as exc:
        raise bad_request(f"reference_sql không hợp lệ: {exc}")
    rc = exec_res["row_count"]
    if rc <= 0:
        raise bad_request("reference_sql phải trả về ít nhất 1 dòng dữ liệu trên Enterprise DB")

    cols = exec_res["columns"]
    from .order_spec import sync_question_order_contract

    synced_question, mode = sync_question_order_contract(
        payload["question"].strip(),
        clean_sql,
        payload.get("compare_mode"),
        cols,
    )
    schema_tables = [t["table"] for t in (w["schema_description"] or {}).get("tables", [])]
    tables_used = [t for t in schema_tables if re.search(rf"\b{re.escape(t)}\b", clean_sql, flags=re.IGNORECASE)]
    schema_txt = f"-- Bảng sử dụng: {', '.join(tables_used)}" if tables_used else "-- Truy vấn thủ công"

    qrow = q1(
        conn,
        """INSERT INTO live.questions
           (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text, status, is_source)
           VALUES (:w, :t, :q, :sql, :m, :d, :sk, :tu, :st, 'ready', false)
           RETURNING question_id""",
        w=w["world_id"],
        t=payload["title"].strip(),
        q=synced_question,
        sql=clean_sql,
        m=mode,
        d=payload["difficulty"],
        sk=skill_ids,
        tu=tables_used,
        st=schema_txt,
    )
    qid = qrow["question_id"]
    norm_r = [[submissions.json_value(row.get(c)) for c in cols] for row in exec_res["rows"]]
    expected = {
        "columns": cols,
        "rows": norm_r,
        "row_count": rc,
        "result_hash": eng.rv.result_hash(norm_r, mode),
        "compare_mode": mode,
    }
    ex(
        conn,
        """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
           VALUES (:q, 'enterprise/base', :ver, 'standard', CAST(:e AS jsonb), false)""",
        q=qid,
        ver=w["dataset_version"],
        e=json.dumps(expected, ensure_ascii=False, default=str),
    )
    audit.log(conn, admin["user_id"], "question.manual_create", "question", qid, {"title": payload["title"], "row_count": rc})
    return {
        "question_id": qid,
        "title": payload["title"].strip(),
        "difficulty": payload["difficulty"],
        "status": "ready",
        "output_columns": cols,
        "row_count": rc,
    }
