"""Thảo luận / Bình luận 1 cấp theo từng câu hỏi SQL (live.question_comments — tách biệt với live.question_reports)."""
from __future__ import annotations

from sqlalchemy import Connection

from ..db import COMMENTS_SCHEMA_DDL, ex, q, q1, table_exists
from ..errors import ApiError, bad_request, conflict, not_found
from . import audit

BADGE_LABELS: dict[str, str] = {
    "admin": "Quản trị viên",
    "solved": "Đã giải đúng",
    "attempted": "Đã thử làm",
}


def _ensure_table(conn: Connection) -> None:
    if not table_exists(conn, "live.question_comments"):
        conn.exec_driver_sql(COMMENTS_SCHEMA_DDL)


def _assert_published_question_visible(conn: Connection, question_id: int, write: bool = False) -> dict:
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
    if write and (row["is_voided"] or row["status"] != "ready"):
        raise conflict("QUESTION_VOIDED", "Câu hỏi này đã được thu hồi khỏi bộ đề hiện tại.")
    return row


def can_user_comment(conn: Connection, user: dict, question_id: int) -> bool:
    if user.get("role") == "admin":
        return True
    has_sub = q1(
        conn,
        "SELECT 1 AS ok FROM live.submissions WHERE user_id = :u AND question_id = :q LIMIT 1",
        u=user["user_id"],
        q=question_id,
    )
    return bool(has_sub)


def _format_comment(row: dict, current_user: dict) -> dict:
    role = str(row.get("author_role") or "learner")
    solved = bool(row.get("author_solved"))
    badge = "admin" if role == "admin" else ("solved" if solved else "attempted")
    uid = int(row["user_id"])
    return {
        "comment_id": int(row["comment_id"]),
        "question_id": int(row["question_id"]),
        "user_id": uid,
        "parent_comment_id": int(row["parent_comment_id"]) if row.get("parent_comment_id") is not None else None,
        "username": row.get("username") or f"user_{uid}",
        "display_name": row.get("display_name") or row.get("username") or f"Học viên #{uid}",
        "avatar_url": row.get("avatar_url"),
        "author_role": role,
        "author_solved": solved,
        "author_badge": badge,
        "author_badge_label": BADGE_LABELS[badge],
        "can_delete": bool(uid == int(current_user["user_id"]) or current_user.get("role") == "admin"),
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "replies": [],
    }


def _fetch_enriched_comments(conn: Connection, question_id: int, only_comment_id: int | None = None) -> list[dict]:
    extra_where = "AND c.comment_id = :cid" if only_comment_id is not None else ""
    params: dict = {"q": question_id}
    if only_comment_id is not None:
        params["cid"] = only_comment_id
    return q(
        conn,
        f"""SELECT c.comment_id, c.question_id, c.user_id, c.parent_comment_id, c.content, c.created_at, c.updated_at,
                   u.username, u.display_name, u.avatar_url, rl.name AS author_role,
                   EXISTS (
                     SELECT 1 FROM live.submissions s
                     WHERE s.user_id = c.user_id AND s.question_id = c.question_id AND s.submission_status = 'passed'
                   ) AS author_solved
            FROM live.question_comments c
            JOIN live.users u ON u.user_id = c.user_id
            JOIN live.roles rl ON rl.role_id = u.role_id
            WHERE c.question_id = :q {extra_where}
            ORDER BY c.created_at ASC, c.comment_id ASC""",
        **params,
    )


def list_comments(conn: Connection, user: dict, question_id: int) -> dict:
    _ensure_table(conn)
    _assert_published_question_visible(conn, question_id, write=False)
    rows = _fetch_enriched_comments(conn, question_id)

    roots: list[dict] = []
    by_id: dict[int, dict] = {}
    for r in rows:
        item = _format_comment(r, user)
        by_id[item["comment_id"]] = item
        if item["parent_comment_id"] is None:
            roots.append(item)

    for r in rows:
        pid = r.get("parent_comment_id")
        if pid is not None and int(pid) in by_id:
            by_id[int(pid)]["replies"].append(by_id[int(r["comment_id"])])

    return {
        "items": roots,
        "total_count": len(rows),
        "can_comment": can_user_comment(conn, user, question_id),
    }


def create_comment(conn: Connection, user: dict, question_id: int, content: str, parent_comment_id: int | None = None) -> dict:
    _ensure_table(conn)
    _assert_published_question_visible(conn, question_id, write=True)
    if not can_user_comment(conn, user, question_id):
        raise conflict("SUBMISSION_REQUIRED", "Nộp bài ít nhất 1 lần để tham gia thảo luận")

    clean_content = (content or "").strip()
    if len(clean_content) < 2 or len(clean_content) > 2000:
        raise bad_request("Nội dung bình luận phải từ 2 đến 2000 ký tự.")

    if parent_comment_id is not None:
        parent = q1(
            conn,
            "SELECT comment_id, question_id, parent_comment_id FROM live.question_comments WHERE comment_id = :pid FOR KEY SHARE",
            pid=parent_comment_id,
        )
        if not parent or int(parent["question_id"]) != int(question_id):
            raise bad_request("Bình luận gốc không tồn tại hoặc không thuộc câu hỏi này.")
        if parent["parent_comment_id"] is not None:
            raise bad_request("Chỉ hỗ trợ trả lời 1 cấp dưới bình luận gốc.")

    inserted = q1(
        conn,
        """INSERT INTO live.question_comments (question_id, user_id, parent_comment_id, content)
           VALUES (:q, :u, :p, :c)
           RETURNING comment_id""",
        q=question_id,
        u=user["user_id"],
        p=parent_comment_id,
        c=clean_content,
    )
    cid = int(inserted["comment_id"])
    audit.log(
        conn,
        user["user_id"],
        "question.comment_created",
        "question_comment",
        cid,
        {"question_id": question_id, "parent_comment_id": parent_comment_id},
    )
    enriched = _fetch_enriched_comments(conn, question_id, only_comment_id=cid)
    return _format_comment(enriched[0], user)


def delete_comment(conn: Connection, user: dict, question_id: int, comment_id: int) -> dict:
    _ensure_table(conn)
    _assert_published_question_visible(conn, question_id, write=False)
    row = q1(
        conn,
        "SELECT comment_id, question_id, user_id FROM live.question_comments WHERE comment_id = :cid AND question_id = :q FOR UPDATE",
        cid=comment_id,
        q=question_id,
    )
    if not row:
        raise not_found("Không tìm thấy bình luận")
    if int(row["user_id"]) != int(user["user_id"]) and user.get("role") != "admin":
        raise ApiError(403, "FORBIDDEN", "Bạn chỉ có quyền xóa bình luận của chính mình")

    ex(conn, "DELETE FROM live.question_comments WHERE comment_id = :cid", cid=comment_id)
    audit.log(conn, user["user_id"], "question.comment_deleted", "question_comment", comment_id, {"question_id": question_id})
    return {"deleted": True, "comment_id": comment_id}
