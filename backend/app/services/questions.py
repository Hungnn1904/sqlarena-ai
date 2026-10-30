"""Câu hỏi đã xuất bản (live.questions): API cho người học + quản trị (list/detail/retire/restore/source)."""
from sqlalchemy import Connection

from ..db import ex, q, q1
from ..errors import bad_request, conflict, not_found
from . import audit, weekly


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


def admin_list(conn: Connection, status, difficulty, skill_id, search, page: int, size: int) -> dict:
    conds, p = [], {}
    if status:
        conds.append("q.status=:st"); p["st"] = status
    if difficulty:
        conds.append("q.difficulty=:d"); p["d"] = difficulty
    if skill_id:
        conds.append("q.skill_ids @> ARRAY[:s]::int[]"); p["s"] = skill_id
    if search:
        conds.append("q.title ILIKE :t"); p["t"] = f"%{search}%"
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = q1(conn, f"SELECT count(*) AS n FROM live.questions q {where}", **p)["n"]
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
                    ORDER BY ws.week_start DESC, ws.set_id DESC LIMIT 1) AS weekly_position
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
