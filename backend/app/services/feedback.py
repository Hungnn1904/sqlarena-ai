"""Bình chọn (👍/👎), Báo lỗi / Góp ý câu hỏi (🚩) và xử lý Human-in-the-loop tại Ngân hàng đề."""
from __future__ import annotations

import json
import re
from sqlalchemy import Connection

from ..db import FEEDBACK_SCHEMA_DDL, begin, ex, q, q1, table_exists
from ..errors import bad_request, conflict, not_found
from ..pipeline import engine as eng
from . import audit, submissions

REASON_LABELS: dict[str, str] = {
    "ambiguous_prompt": "Đề mơ hồ",
    "wrong_difficulty": "Sai độ khó",
    "wrong_answer_or_testcase": "Nghi sai đáp án/test case",
    "typo_or_column_name": "Lỗi chính tả/tên cột",
    "other": "Khác",
}
_LABEL_TO_CODE = {v.lower(): k for k, v in REASON_LABELS.items()}


def _ensure_tables(conn: Connection) -> None:
    if not table_exists(conn, "live.question_votes") or not table_exists(conn, "live.question_reports"):
        conn.exec_driver_sql(FEEDBACK_SCHEMA_DDL)


def normalize_reason_type(raw: str) -> str:
    val = (raw or "").strip()
    if val in REASON_LABELS:
        return val
    mapped = _LABEL_TO_CODE.get(val.lower())
    if mapped:
        return mapped
    raise bad_request("Loại báo lỗi không hợp lệ", {"allowed": list(REASON_LABELS.keys())})


def _assert_published_question_visible(conn: Connection, question_id: int) -> dict:
    row = q1(
        conn,
        """SELECT qq.question_id, qq.status, wsi.is_voided
           FROM live.weekly_set_items wsi
           JOIN live.weekly_sets ws ON ws.set_id = wsi.set_id
           JOIN live.questions qq ON qq.question_id = wsi.question_id
           WHERE ws.status = 'published' AND wsi.question_id = :q
           LIMIT 1""",
        q=question_id,
    )
    if not row:
        raise not_found("Không tìm thấy câu hỏi")
    if row["is_voided"] or row["status"] != "ready":
        raise conflict("QUESTION_VOIDED", "Câu hỏi này đã được thu hồi khỏi bộ đề hiện tại.")
    return row


def _vote_counts(conn: Connection, question_id: int, user_id: int | None = None) -> dict:
    agg = q1(
        conn,
        """SELECT COALESCE(SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END), 0) AS upvotes,
                  COALESCE(SUM(CASE WHEN vote = -1 THEN 1 ELSE 0 END), 0) AS downvotes
           FROM live.question_votes WHERE question_id = :q""",
        q=question_id,
    ) or {"upvotes": 0, "downvotes": 0}
    my_row = (
        q1(conn, "SELECT vote FROM live.question_votes WHERE question_id = :q AND user_id = :u", q=question_id, u=user_id)
        if user_id
        else None
    )
    return {
        "upvotes": int(agg["upvotes"] or 0),
        "downvotes": int(agg["downvotes"] or 0),
        "my_vote": int(my_row["vote"]) if my_row and my_row.get("vote") is not None else None,
    }


def _format_report(r: dict) -> dict:
    rt = str(r.get("reason_type") or "other")
    return {
        **r,
        "reason_type": rt,
        "reason_label": REASON_LABELS.get(rt, rt),
    }


def learner_feedback_for_question(conn: Connection, question_id: int, user_id: int | None, attempt_count: int = 0) -> dict:
    _ensure_tables(conn)
    vc = _vote_counts(conn, question_id, user_id)
    open_rep = (
        q1(
            conn,
            """SELECT report_id, question_id, user_id, reason_type, comment, status, created_at
               FROM live.question_reports
               WHERE question_id = :q AND user_id = :u AND status = 'open'
               LIMIT 1""",
            q=question_id,
            u=user_id,
        )
        if user_id
        else None
    )
    return {
        **vc,
        "can_vote": bool((attempt_count or 0) >= 1),
        "my_open_report": _format_report(open_rep) if open_rep else None,
    }


def cast_vote(conn: Connection, user_id: int, question_id: int, vote: int) -> dict:
    _ensure_tables(conn)
    _assert_published_question_visible(conn, question_id)
    if vote not in (-1, 0, 1):
        raise bad_request("Giá trị vote phải là 1, -1 hoặc 0")
    attempts = q1(
        conn,
        "SELECT count(*) AS n FROM live.submissions WHERE user_id = :u AND question_id = :q",
        u=user_id,
        q=question_id,
    )["n"]
    if int(attempts or 0) < 1:
        raise conflict("SUBMISSION_REQUIRED", "Bạn cần nộp bài ít nhất 1 lần trước khi bình chọn câu hỏi này.")

    if vote == 0:
        ex(conn, "DELETE FROM live.question_votes WHERE question_id = :q AND user_id = :u", q=question_id, u=user_id)
    else:
        ex(
            conn,
            """INSERT INTO live.question_votes (question_id, user_id, vote, updated_at)
               VALUES (:q, :u, :v, now())
               ON CONFLICT (question_id, user_id)
               DO UPDATE SET vote = EXCLUDED.vote, updated_at = now()""",
            q=question_id,
            u=user_id,
            v=vote,
        )
    vc = _vote_counts(conn, question_id, user_id)
    return {"question_id": question_id, **vc, "can_vote": True}


def submit_report(conn: Connection, user_id: int, question_id: int, reason_type: str, comment: str) -> dict:
    _ensure_tables(conn)
    _assert_published_question_visible(conn, question_id)
    code = normalize_reason_type(reason_type)
    clean_comment = (comment or "").strip()
    if len(clean_comment) < 3:
        raise bad_request("Nội dung góp ý / báo lỗi cần tối thiểu 3 ký tự.")

    inserted = q1(
        conn,
        """INSERT INTO live.question_reports (question_id, user_id, reason_type, comment, status)
           VALUES (:q, :u, :rt, :cm, 'open')
           ON CONFLICT (question_id, user_id) WHERE (status = 'open')
           DO NOTHING
           RETURNING *""",
        q=question_id,
        u=user_id,
        rt=code,
        cm=clean_comment,
    )
    if not inserted:
        raise conflict("OPEN_REPORT_EXISTS", "Bạn đã có 1 báo lỗi đang mở cho câu hỏi này; vui lòng chờ Quản trị viên xử lý.")
    audit.log(conn, user_id, "question.report_created", "question", question_id, {"report_id": inserted["report_id"], "reason_type": code})
    return _format_report(inserted)


def attach_admin_feedback_counts(conn: Connection, items: list[dict]) -> list[dict]:
    if not items:
        return items
    _ensure_tables(conn)
    qids = [int(it["question_id"]) for it in items if it.get("question_id") is not None]
    vote_map: dict[int, tuple[int, int]] = {}
    rep_map: dict[int, tuple[int, int]] = {}
    if qids:
        for vr in q(
            conn,
            """SELECT question_id,
                      COALESCE(SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END), 0) AS up,
                      COALESCE(SUM(CASE WHEN vote = -1 THEN 1 ELSE 0 END), 0) AS down
               FROM live.question_votes WHERE question_id = ANY(:qids) GROUP BY question_id""",
            qids=qids,
        ):
            vote_map[int(vr["question_id"])] = (int(vr["up"] or 0), int(vr["down"] or 0))
        for rr in q(
            conn,
            """SELECT question_id,
                      COALESCE(SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END), 0) AS open_n,
                      COUNT(*) AS total_n
               FROM live.question_reports WHERE question_id = ANY(:qids) GROUP BY question_id""",
            qids=qids,
        ):
            rep_map[int(rr["question_id"])] = (int(rr["open_n"] or 0), int(rr["total_n"] or 0))
    out: list[dict] = []
    for it in items:
        qid = int(it["question_id"])
        up, down = vote_map.get(qid, (0, 0))
        open_n, total_n = rep_map.get(qid, (0, 0))
        out.append({
            **it,
            "upvotes": up,
            "downvotes": down,
            "open_reports_count": open_n,
            "total_reports_count": total_n,
        })
    return out


def question_feedback_detail(conn: Connection, question_id: int) -> dict:
    _ensure_tables(conn)
    vc = _vote_counts(conn, question_id, None)
    rows = q(
        conn,
        """SELECT r.*, u.username, u.display_name, adm.username AS resolved_by_username
           FROM live.question_reports r
           JOIN live.users u ON u.user_id = r.user_id
           LEFT JOIN live.users adm ON adm.user_id = r.resolved_by
           WHERE r.question_id = :q
           ORDER BY (r.status = 'open') DESC, r.created_at DESC, r.report_id DESC""",
        q=question_id,
    )
    reports = [_format_report(r) for r in rows]
    open_n = sum(1 for r in reports if r["status"] == "open")
    return {
        "upvotes": vc["upvotes"],
        "downvotes": vc["downvotes"],
        "open_reports_count": open_n,
        "total_reports_count": len(reports),
        "reports": reports,
    }


def list_admin_feedback(conn: Connection, status: str | None, question_id: int | None, page: int, size: int) -> dict:
    _ensure_tables(conn)
    conds, params = [], {}
    if status:
        conds.append("r.status = :st")
        params["st"] = status
    if question_id is not None:
        conds.append("r.question_id = :qid")
        params["qid"] = question_id
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = q1(conn, f"SELECT count(*) AS n FROM live.question_reports r {where}", **params)["n"]
    rows = q(
        conn,
        f"""SELECT r.*, q.title AS question_title, q.difficulty, q.status AS question_status, q.source_draft_id,
                   u.username, u.display_name, adm.username AS resolved_by_username,
                   (SELECT count(*) FROM live.question_votes v WHERE v.question_id = r.question_id AND v.vote = 1) AS upvotes,
                   (SELECT count(*) FROM live.question_votes v WHERE v.question_id = r.question_id AND v.vote = -1) AS downvotes,
                   (SELECT count(*) FROM live.question_reports r2 WHERE r2.question_id = r.question_id AND r2.status = 'open') AS open_reports_count
            FROM live.question_reports r
            JOIN live.questions q ON q.question_id = r.question_id
            JOIN live.users u ON u.user_id = r.user_id
            LEFT JOIN live.users adm ON adm.user_id = r.resolved_by
            {where}
            ORDER BY (r.status = 'open') DESC, r.created_at DESC, r.report_id DESC
            LIMIT :l OFFSET :o""",
        l=size,
        o=(page - 1) * size,
        **params,
    )
    return {"items": [_format_report(r) for r in rows], "total": total, "page": page, "page_size": size}


def _apply_reverified_question_update(conn: Connection, admin: dict, qrow: dict, edits: dict, exec_res: dict) -> None:
    from .order_spec import sync_question_order_contract

    w = q1(conn, "SELECT world_id, dataset_version, schema_description FROM core.worlds WHERE world_id = :w", w=qrow["world_id"])
    ver = int(w["dataset_version"]) if w else 1
    clean_sql = edits["clean_sql"]
    cols = list(exec_res["columns"])
    next_title = (edits.get("title") or qrow["title"] or "").strip()
    base_q = (edits.get("question") or qrow["question"] or "").strip()
    synced_q, mode = sync_question_order_contract(base_q, clean_sql, qrow.get("compare_mode"), cols)
    schema_tables = [t["table"] for t in ((w or {}).get("schema_description") or {}).get("tables", [])]
    tables_used = [t for t in schema_tables if re.search(rf"\b{re.escape(t)}\b", clean_sql, flags=re.IGNORECASE)] or list(qrow.get("tables_used") or [])

    ex(
        conn,
        """UPDATE live.questions
           SET title = :t, question = :qt, reference_sql = :sql, compare_mode = :cm, tables_used = :tu, status = 'ready', retired_at = NULL, retire_reason = NULL
           WHERE question_id = :qid""",
        t=next_title,
        qt=synced_q,
        sql=clean_sql,
        cm=mode,
        tu=tables_used,
        qid=qrow["question_id"],
    )
    ex(
        conn,
        """UPDATE live.weekly_set_items wsi
           SET is_voided = false
           FROM live.weekly_sets ws
           WHERE ws.set_id = wsi.set_id AND ws.status = 'published' AND wsi.question_id = :qid""",
        qid=qrow["question_id"],
    )
    norm_rows = eng.rv.norm_rows([[row.get(c) for c in cols] for row in exec_res["rows"]])
    expected = {
        "columns": cols,
        "rows": norm_rows,
        "row_count": exec_res["row_count"],
        "result_hash": eng.rv.result_hash(norm_rows, mode),
        "compare_mode": mode,
    }
    ex(conn, "DELETE FROM live.test_cases WHERE question_id = :qid", qid=qrow["question_id"])
    ex(
        conn,
        """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
           VALUES (:qid, 'enterprise/base', :ver, 'standard', CAST(:er AS jsonb), false)""",
        qid=qrow["question_id"],
        ver=ver,
        er=json.dumps(expected, ensure_ascii=False, default=str),
    )
    if qrow.get("source_draft_id"):
        ex(
            conn,
            "UPDATE draft.question_drafts SET title = :t, question = :qt, reference_sql = :sql, compare_mode = :cm, updated_at = now() WHERE draft_id = :did",
            t=next_title,
            qt=synced_q,
            sql=clean_sql,
            cm=mode,
            did=qrow["source_draft_id"],
        )
    audit.log(conn, admin["user_id"], "question.reworked_sql", "question", qrow["question_id"], {"row_count": exec_res["row_count"], "compare_mode": mode})


def resolve_report(admin: dict, report_id: int, payload: dict) -> dict:
    from . import drafts, questions

    action = payload["action"]
    note = (payload.get("admin_note") or "").strip() or None
    updated_sql = (payload.get("updated_sql") or "").strip() or None
    updated_title = (payload.get("updated_title") or "").strip() or None
    updated_question = (payload.get("updated_question") or "").strip() or None

    pre_exec: dict | None = None
    pre_clean_sql: str | None = None
    if action == "rework" and (updated_sql or updated_title or updated_question):
        with begin() as c_pre:
            _ensure_tables(c_pre)
            rep_pre = q1(c_pre, "SELECT question_id, status FROM live.question_reports WHERE report_id = :rid", rid=report_id)
            if not rep_pre:
                raise not_found("Không tìm thấy báo lỗi")
            if rep_pre["status"] != "open":
                raise conflict("INVALID_STATE", f"Báo lỗi đã được xử lý trước đó ({rep_pre['status']})")
            q_pre = q1(c_pre, "SELECT reference_sql FROM live.questions WHERE question_id = :qid", qid=rep_pre["question_id"])
            if not q_pre:
                raise not_found("Không tìm thấy câu hỏi")
            raw_sql = (updated_sql or q_pre["reference_sql"] or "").strip()
        try:
            pre_clean_sql = submissions.guard_select(raw_sql)
            pre_exec = submissions.execute_sandbox_sql(pre_clean_sql)
        except Exception as exc:
            raise bad_request(f"Câu lệnh SQL sửa lại không hợp lệ: {exc}") from exc
        if pre_exec["row_count"] <= 0:
            raise bad_request("Câu lệnh SQL sửa lại trả về 0 dòng dữ liệu trên Enterprise DB.")

    with begin() as conn:
        _ensure_tables(conn)
        rep = q1(conn, "SELECT * FROM live.question_reports WHERE report_id = :rid FOR UPDATE", rid=report_id)
        if not rep:
            raise not_found("Không tìm thấy báo lỗi")
        if rep["status"] != "open":
            raise conflict("INVALID_STATE", f"Báo lỗi đã được xử lý trước đó ({rep['status']})")
        qrow = q1(conn, "SELECT * FROM live.questions WHERE question_id = :qid FOR UPDATE", qid=rep["question_id"])
        if not qrow:
            raise not_found("Không tìm thấy câu hỏi")

        qid = int(qrow["question_id"])
        if action == "dismiss":
            ex(
                conn,
                """UPDATE live.question_reports
                   SET status = 'dismissed', admin_note = :n, resolved_by = :aid, resolved_at = now(), updated_at = now()
                   WHERE report_id = :rid""",
                n=note,
                aid=admin["user_id"],
                rid=report_id,
            )
            audit.log(conn, admin["user_id"], "report.dismiss", "question_report", report_id, {"question_id": qid, "note": note})
        elif action == "retire":
            if qrow["status"] != "retired":
                questions.retire(conn, admin, qid, note or "Loại bỏ câu hỏi theo phản hồi người học")
            ex(
                conn,
                """UPDATE live.question_reports
                   SET status = 'resolved', admin_note = COALESCE(:n, admin_note), resolved_by = :aid, resolved_at = now(), updated_at = now()
                   WHERE question_id = :qid AND status = 'open'""",
                n=note,
                aid=admin["user_id"],
                qid=qid,
            )
        elif action in ("rework", "return_needs_human"):
            if pre_exec is not None and pre_clean_sql is not None:
                _apply_reverified_question_update(
                    conn,
                    admin,
                    qrow,
                    {"title": updated_title, "question": updated_question, "clean_sql": pre_clean_sql},
                    pre_exec,
                )
            else:
                src_did = qrow.get("source_draft_id")
                reason_txt = note or "Thu hồi từ báo lỗi người học để biên tập lại"
                if src_did:
                    d_cur = q1(conn, "SELECT status FROM draft.question_drafts WHERE draft_id = :d", d=src_did)
                    if d_cur and d_cur["status"] == "approved":
                        drafts.return_needs_human(conn, admin, int(src_did), reason_txt)
                    else:
                        drafts._unpublish_live_question_for_draft(conn, int(src_did), reason_txt)
                else:
                    w = q1(conn, "SELECT schema_description, fk_relations, business_rules FROM core.worlds WHERE world_id = :w", w=qrow["world_id"])
                    all_tbl_defs = ((w or {}).get("schema_description") or {}).get("tables", [])
                    schema_tables = [t["table"] for t in all_tbl_defs]
                    inferred_tables = list(qrow["tables_used"] or []) or [
                        t for t in schema_tables if re.search(rf"\b{re.escape(t)}\b", qrow.get("reference_sql") or "", flags=re.IGNORECASE)
                    ]
                    raw_br = (w or {}).get("business_rules")
                    br_list = raw_br.get("rules", []) if isinstance(raw_br, dict) else list(raw_br or [])
                    schema_ctx = {
                        "tables": [t for t in all_tbl_defs if t["table"] in inferred_tables] or all_tbl_defs,
                        "fk_relations": (w or {}).get("fk_relations") or [],
                        "business_rules": br_list,
                        "tables_used": inferred_tables,
                    }
                    new_draft = q1(
                        conn,
                        """INSERT INTO draft.question_drafts
                           (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, schema_context, status, status_reason, gen_model, gen_prompt_version)
                           VALUES (:w, :t, :qt, :sql, :cm, :d, :sk, '{}'::jsonb, :tu, :st, CAST(:sc AS jsonb), 'approved', :sr, 'manual', 'v1')
                           RETURNING draft_id""",
                        w=qrow["world_id"],
                        t=qrow["title"],
                        qt=qrow["question"],
                        sql=qrow["reference_sql"],
                        cm=qrow["compare_mode"] or "unordered",
                        d=qrow["difficulty"],
                        sk=qrow["skill_ids"],
                        tu=inferred_tables,
                        st=qrow["schema_text"] or "",
                        sc=json.dumps(schema_ctx, ensure_ascii=False),
                        sr=reason_txt,
                    )
                    ex(conn, "UPDATE live.questions SET source_draft_id = :did WHERE question_id = :qid", did=new_draft["draft_id"], qid=qid)
                    drafts.return_needs_human(conn, admin, int(new_draft["draft_id"]), reason_txt)
            ex(
                conn,
                """UPDATE live.question_reports
                   SET status = 'resolved', admin_note = COALESCE(:n, admin_note), resolved_by = :aid, resolved_at = now(), updated_at = now()
                   WHERE question_id = :qid AND status = 'open'""",
                n=note,
                aid=admin["user_id"],
                qid=qid,
            )
        else:
            raise bad_request("Hành động xử lý không hợp lệ")

        updated_rep = q1(conn, "SELECT * FROM live.question_reports WHERE report_id = :rid", rid=report_id)
        return {
            "report": _format_report(updated_rep),
            "question": questions.admin_detail(conn, qid),
        }
