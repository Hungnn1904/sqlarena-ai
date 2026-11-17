"""Quản lý Nhóm câu hỏi nháp (Question Groups) và phát hành hàng loạt lên bộ đề tuần."""
from datetime import date, datetime, timedelta

from sqlalchemy import Connection

from ..db import begin, ex, q, q1
from ..errors import bad_request, conflict, not_found
from . import audit, drafts, weekly


def _lock_group(conn: Connection, group_id: int) -> dict:
    grp = q1(conn, "SELECT * FROM live.question_groups WHERE group_id=:g FOR UPDATE", g=group_id)
    if not grp:
        raise not_found("Không tìm thấy nhóm câu hỏi")
    return grp


def _validate_ready_questions(conn: Connection, question_ids: list[int]) -> None:
    if not question_ids:
        return
    rows = {
        r["question_id"]: r
        for r in q(
            conn,
            "SELECT question_id, status FROM live.questions WHERE question_id = ANY(:ids)",
            ids=question_ids,
        )
    }
    not_found_ids = [qid for qid in question_ids if qid not in rows]
    not_ready_ids = [qid for qid in question_ids if qid in rows and rows[qid]["status"] != "ready"]
    if not_found_ids or not_ready_ids:
        problems = {}
        if not_found_ids:
            problems["not_found"] = not_found_ids
        if not_ready_ids:
            problems["not_ready"] = not_ready_ids
        raise conflict("QUESTION_NOT_ELIGIBLE", "Có câu hỏi không tồn tại hoặc không ở trạng thái ready", problems)


def _resolve_draft_question_ids(admin: dict, draft_ids: list[int] | None, note: str) -> list[int]:
    if not draft_ids:
        return []
    res = drafts.bulk_approve(admin, draft_ids, note=note)
    qids = list(res["question_ids"])
    # Nếu có draft đã được approve từ trước, lấy luôn question_id tương ứng để idempotent
    with begin() as conn:
        for sk in res["skipped"]:
            if sk["reason"] == "already_approved":
                lq = q1(conn, "SELECT question_id FROM live.questions WHERE source_draft_id=:d AND status='ready'", d=sk["draft_id"])
                if lq and lq["question_id"] not in qids:
                    qids.append(lq["question_id"])
    return qids


def list_groups(conn: Connection) -> dict:
    groups = q(conn, "SELECT * FROM live.question_groups ORDER BY group_id DESC")
    if not groups:
        return {"items": [], "total": 0}
    gids = [g["group_id"] for g in groups]
    item_rows = q(
        conn,
        """SELECT gi.group_id, gi.position, q.question_id, q.title, q.difficulty, q.status, q.tables_used
           FROM live.question_group_items gi
           JOIN live.questions q USING (question_id)
           WHERE gi.group_id = ANY(:gids)
           ORDER BY gi.group_id, gi.position""",
        gids=gids,
    )
    by_group: dict[int, list[dict]] = {gid: [] for gid in gids}
    for it in item_rows:
        by_group[it["group_id"]].append({
            "position": it["position"],
            "question_id": it["question_id"],
            "title": it["title"],
            "difficulty": it["difficulty"],
            "status": it["status"],
            "tables_used": it["tables_used"] or [],
        })
    items = []
    for g in groups:
        g_items = by_group[g["group_id"]]
        items.append({
            "group_id": g["group_id"],
            "name": g["name"],
            "description": g["description"],
            "status": g["status"],
            "question_count": len(g_items),
            "published_set_id": g["published_set_id"],
            "created_at": g["created_at"],
            "published_at": g["published_at"],
            "items": g_items,
        })
    return {"items": items, "total": len(items)}


def get(conn: Connection, group_id: int) -> dict:
    g = q1(conn, "SELECT * FROM live.question_groups WHERE group_id=:g", g=group_id)
    if not g:
        raise not_found("Không tìm thấy nhóm câu hỏi")
    smap = {r["skill_id"]: r["name"] for r in q(conn, "SELECT skill_id, name FROM core.skills")}
    rows = q(
        conn,
        """SELECT gi.position, q.question_id, q.title, q.question, q.difficulty, q.status, q.skill_ids, q.tables_used,
                  EXISTS (
                    SELECT 1 FROM live.weekly_set_items wsi
                    JOIN live.weekly_sets ws USING (set_id)
                    WHERE wsi.question_id = q.question_id AND ws.status = 'published'
                  ) AS in_published_set
           FROM live.question_group_items gi
           JOIN live.questions q USING (question_id)
           WHERE gi.group_id = :g
           ORDER BY gi.position""",
        g=group_id,
    )
    items = [
        {
            "position": r["position"],
            "question_id": r["question_id"],
            "title": r["title"],
            "question": r["question"],
            "difficulty": r["difficulty"],
            "status": r["status"],
            "skills": [smap[sid] for sid in (r["skill_ids"] or []) if sid in smap],
            "tables_used": r["tables_used"] or [],
            "in_published_set": bool(r["in_published_set"]),
        }
        for r in rows
    ]
    return {
        "group_id": g["group_id"],
        "name": g["name"],
        "description": g["description"],
        "status": g["status"],
        "question_count": len(items),
        "published_set_id": g["published_set_id"],
        "created_at": g["created_at"],
        "published_at": g["published_at"],
        "items": items,
    }


def create(admin: dict, name: str, description: str | None, question_ids: list[int] | None, draft_ids: list[int] | None) -> dict:
    approved_qids = _resolve_draft_question_ids(admin, draft_ids, f"Duyệt nhanh khi tạo nhóm: {name}")
    combined_ids = list(dict.fromkeys([*(question_ids or []), *approved_qids]))
    with begin() as conn:
        _validate_ready_questions(conn, combined_ids)
        grp = q1(
            conn,
            """INSERT INTO live.question_groups (name, description, status, created_by)
               VALUES (:n, :d, 'draft', :u) RETURNING group_id""",
            n=name.strip(),
            d=description,
            u=admin["user_id"],
        )
        gid = grp["group_id"]
        for pos, qid in enumerate(combined_ids, start=1):
            ex(conn, "INSERT INTO live.question_group_items (group_id, question_id, position) VALUES (:g, :q, :p)", g=gid, q=qid, p=pos)
        audit.log(conn, admin["user_id"], "question_group.create", "question_group", gid, {"name": name, "count": len(combined_ids)})
        return get(conn, gid)


def update(conn: Connection, admin: dict, group_id: int, name: str | None, description: str | None, fields_set: set[str]) -> dict:
    grp = _lock_group(conn, group_id)
    if grp["status"] != "draft":
        raise conflict("INVALID_STATE", f"Chỉ sửa được thông tin khi nhóm còn draft (hiện: {grp['status']})", {"status": grp["status"]})
    new_name = name.strip() if ("name" in fields_set and name is not None) else grp["name"]
    new_desc = description if "description" in fields_set else grp["description"]
    ex(conn, "UPDATE live.question_groups SET name=:n, description=:d WHERE group_id=:g", n=new_name, d=new_desc, g=group_id)
    audit.log(conn, admin["user_id"], "question_group.update", "question_group", group_id, {"name": new_name})
    return get(conn, group_id)


def replace_items(conn: Connection, admin: dict, group_id: int, question_ids: list[int]) -> dict:
    grp = _lock_group(conn, group_id)
    if grp["status"] != "draft":
        raise conflict("INVALID_STATE", f"Chỉ sắp xếp/thay đổi câu hỏi khi nhóm còn draft (hiện: {grp['status']})", {"status": grp["status"]})
    if len(set(question_ids)) != len(question_ids):
        raise bad_request("question_ids bị trùng lặp")
    _validate_ready_questions(conn, question_ids)
    ex(conn, "DELETE FROM live.question_group_items WHERE group_id=:g", g=group_id)
    for pos, qid in enumerate(question_ids, start=1):
        ex(conn, "INSERT INTO live.question_group_items (group_id, question_id, position) VALUES (:g, :q, :p)", g=group_id, q=qid, p=pos)
    audit.log(conn, admin["user_id"], "question_group.items", "question_group", group_id, {"count": len(question_ids)})
    return get(conn, group_id)


def add_items(admin: dict, group_id: int, question_ids: list[int] | None, draft_ids: list[int] | None) -> dict:
    with begin() as conn:
        grp = q1(conn, "SELECT status, name FROM live.question_groups WHERE group_id=:g", g=group_id)
        if not grp:
            raise not_found("Không tìm thấy nhóm câu hỏi")
        if grp["status"] != "draft":
            raise conflict("INVALID_STATE", f"Chỉ thêm câu hỏi khi nhóm còn draft (hiện: {grp['status']})", {"status": grp["status"]})
    approved_qids = _resolve_draft_question_ids(admin, draft_ids, f"Duyệt nhanh khi thêm vào nhóm #{group_id}")
    candidate_ids = list(dict.fromkeys([*(question_ids or []), *approved_qids]))
    with begin() as conn:
        grp_locked = _lock_group(conn, group_id)
        if grp_locked["status"] != "draft":
            raise conflict("INVALID_STATE", f"Chỉ thêm câu hỏi khi nhóm còn draft (hiện: {grp_locked['status']})", {"status": grp_locked["status"]})
        existing = {r["question_id"] for r in q(conn, "SELECT question_id FROM live.question_group_items WHERE group_id=:g", g=group_id)}
        to_add = [qid for qid in candidate_ids if qid not in existing]
        _validate_ready_questions(conn, to_add)
        start_pos = q1(conn, "SELECT COALESCE(MAX(position), 0) AS p FROM live.question_group_items WHERE group_id=:g", g=group_id)["p"]
        for offset, qid in enumerate(to_add, start=1):
            ex(conn, "INSERT INTO live.question_group_items (group_id, question_id, position) VALUES (:g, :q, :p)", g=group_id, q=qid, p=start_pos + offset)
        audit.log(conn, admin["user_id"], "question_group.add_items", "question_group", group_id, {"added_count": len(to_add)})
        return get(conn, group_id)


def delete(conn: Connection, admin: dict, group_id: int) -> dict:
    grp = _lock_group(conn, group_id)
    if grp["status"] != "draft":
        raise conflict("INVALID_STATE", "Không thể xoá nhóm câu hỏi đã phát hành", {"status": grp["status"]})
    ex(conn, "DELETE FROM live.question_groups WHERE group_id=:g", g=group_id)
    audit.log(conn, admin["user_id"], "question_group.delete", "question_group", group_id, {"name": grp["name"]})
    return {"deleted": True, "group_id": group_id}


def _pick_free_week_start(conn: Connection) -> date:
    today = datetime.now(weekly._tz()).date()
    monday = today - timedelta(days=today.weekday())
    used = {r["week_start"] for r in q(conn, "SELECT week_start FROM live.weekly_sets")}
    if monday not in used:
        return monday
    offset = 1
    while True:
        cand_next = monday + timedelta(days=7 * offset)
        if cand_next not in used:
            return cand_next
        cand_prev = monday - timedelta(days=7 * offset)
        if cand_prev not in used:
            return cand_prev
        offset += 1


def _detach_from_draft_sets(conn: Connection, draft_set_map: dict[int, int]) -> None:
    """Gỡ an toàn các câu đang nằm ở bộ đề tuần nháp (draft) khác và đánh lại position liên tục."""
    if not draft_set_map:
        return
    affected_sets = sorted(set(draft_set_map.values()))
    ex(conn, "DELETE FROM live.weekly_set_items WHERE question_id = ANY(:qids)", qids=list(draft_set_map.keys()))
    for d_sid in affected_sets:
        ex(conn, "UPDATE live.weekly_set_items SET position = position + 1000 WHERE set_id=:s", s=d_sid)
        ex(
            conn,
            """UPDATE live.weekly_set_items i
               SET position = n.rn
               FROM (SELECT question_id, row_number() OVER (ORDER BY position) AS rn FROM live.weekly_set_items WHERE set_id=:s) n
               WHERE i.set_id=:s AND i.question_id = n.question_id""",
            s=d_sid,
        )


def publish(conn: Connection, admin: dict, group_id: int, mode: str = "append_active", set_title: str | None = None) -> dict:
    grp = _lock_group(conn, group_id)
    if grp["status"] != "draft":
        raise conflict("INVALID_STATE", f"Chỉ phát hành được nhóm ở trạng thái draft (hiện: {grp['status']})", {"status": grp["status"]})
    items = q(
        conn,
        """SELECT gi.position, q.question_id, q.status, q.is_flagged
           FROM live.question_group_items gi
           JOIN live.questions q USING (question_id)
           WHERE gi.group_id=:g ORDER BY gi.position""",
        g=group_id,
    )
    if not items:
        raise conflict("EMPTY_GROUP", "Không thể phát hành nhóm câu hỏi rỗng")

    qids = [it["question_id"] for it in items]
    bad = {
        "not_ready_or_flagged": [it["question_id"] for it in items if it["status"] != "ready" or it["is_flagged"]],
        **weekly._test_problems(conn, qids),
    }
    if any(bad.values()):
        raise conflict("GROUP_NOT_PUBLISHABLE", "Có câu hỏi chưa đủ điều kiện phát hành", {k: v for k, v in bad.items() if v})

    existing_ws = {
        r["question_id"]: r
        for r in q(
            conn,
            """SELECT wsi.question_id, wsi.set_id, ws.status AS set_status
               FROM live.weekly_set_items wsi
               JOIN live.weekly_sets ws USING (set_id)
               WHERE wsi.question_id = ANY(:ids)""",
            ids=qids,
        )
    }
    closed_used = [qid for qid, info in existing_ws.items() if info["set_status"] == "closed"]
    if closed_used:
        raise conflict("QUESTION_ALREADY_USED", "Có câu hỏi đã thuộc bộ đề tuần đã đóng trước đó", {"question_ids": closed_used})

    draft_set_map = {qid: info["set_id"] for qid, info in existing_ws.items() if info["set_status"] == "draft"}

    if mode == "append_active":
        pub_set = q1(conn, "SELECT * FROM live.weekly_sets WHERE status='published' FOR UPDATE")
        if not pub_set:
            ws_date = _pick_free_week_start(conn)
            s_title = (set_title or grp["name"])[:100]
            pub_set = q1(
                conn,
                "INSERT INTO live.weekly_sets (title, week_start, status, published_at) VALUES (:t, :w, 'published', now()) RETURNING *",
                t=s_title,
                w=ws_date,
            )
        sid = pub_set["set_id"]
        s_title = pub_set["title"]
        _detach_from_draft_sets(conn, draft_set_map)
        next_pos = q1(conn, "SELECT COALESCE(MAX(position), 0) AS p FROM live.weekly_set_items WHERE set_id=:s", s=sid)["p"]
        inserted_count = 0
        for qid in qids:
            if qid in existing_ws and existing_ws[qid]["set_id"] == sid:
                continue
            next_pos += 1
            ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, :p)", s=sid, q=qid, p=next_pos)
            inserted_count += 1
    elif mode == "new_weekly_set":
        already_pub = [qid for qid, info in existing_ws.items() if info["set_status"] == "published"]
        if already_pub:
            raise conflict("QUESTION_ALREADY_USED", "Có câu hỏi đang nằm trong bộ đề đang mở; không thể gắn lại sang bộ tuần mới", {"question_ids": already_pub})
        old_pub = q1(conn, "SELECT * FROM live.weekly_sets WHERE status='published' FOR UPDATE")
        if old_pub:
            for h in weekly.CLOSE_HOOKS:
                h(conn, old_pub["set_id"])
            ex(
                conn,
                """UPDATE live.questions SET status='archived', archived_at=now()
                   WHERE status='ready'
                     AND question_id IN (SELECT question_id FROM live.weekly_set_items WHERE set_id=:s)
                     AND NOT (question_id = ANY(:keep))""",
                s=old_pub["set_id"],
                keep=qids,
            )
            ex(conn, "UPDATE live.weekly_sets SET status='closed', closed_at=now() WHERE set_id=:s", s=old_pub["set_id"])
        _detach_from_draft_sets(conn, draft_set_map)
        ws_date = _pick_free_week_start(conn)
        s_title = (set_title or grp["name"])[:100]
        new_pub = q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) VALUES (:t, :w, 'published', now()) RETURNING *",
            t=s_title,
            w=ws_date,
        )
        sid = new_pub["set_id"]
        inserted_count = 0
        for pos, qid in enumerate(qids, start=1):
            ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, :p)", s=sid, q=qid, p=pos)
            inserted_count += 1
    else:
        raise bad_request(f"Chế độ phát hành không hợp lệ: {mode}")

    ex(
        conn,
        "UPDATE live.question_groups SET status='published', published_at=now(), published_set_id=:sid WHERE group_id=:g",
        sid=sid,
        g=group_id,
    )
    audit.log(
        conn,
        admin["user_id"],
        "question_group.publish",
        "question_group",
        group_id,
        {"mode": mode, "set_id": sid, "published_count": inserted_count},
    )
    return {
        "group": get(conn, group_id),
        "published_count": inserted_count,
        "set_id": sid,
        "set_title": s_title,
        "mode": mode,
    }
