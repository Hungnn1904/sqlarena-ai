"""SQLAlchemy 2.x engine + helper truy vấn (SQL tường minh, trả về dict)."""
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=10, future=True)


def reset_engine() -> None:
    get_engine.cache_clear()


@contextmanager
def begin() -> Iterator[Connection]:
    """Transaction ngắn: commit khi thoát bình thường, rollback khi lỗi."""
    with get_engine().begin() as conn:
        yield conn


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency: một transaction cho mỗi request."""
    with get_engine().begin() as conn:
        yield conn


def q(conn: Connection, sql: str, /, **params: Any) -> list[dict]:
    return [dict(r) for r in conn.execute(text(sql), params).mappings().all()]


def q1(conn: Connection, sql: str, /, **params: Any) -> dict | None:
    row = conn.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def ex(conn: Connection, sql: str, /, **params: Any) -> int:
    return conn.execute(text(sql), params).rowcount


def table_exists(conn: Connection, qualified: str) -> bool:
    return bool(conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": qualified}).scalar())


def ensure_runtime_schema() -> None:
    """Đảm bảo các bảng & ràng buộc mới (0004_question_groups, 0005_admin_override) luôn tồn tại kể cả khi dev chạy uvicorn trực tiếp chưa qua alembic."""
    with begin() as conn:
        if not table_exists(conn, "live.weekly_sets") or not table_exists(conn, "live.questions"):
            return
        if not table_exists(conn, "live.question_groups"):
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS live.question_groups (
                  group_id         serial PRIMARY KEY,
                  name             varchar(120) NOT NULL,
                  description      text,
                  status           varchar(20)  NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
                  published_set_id int          REFERENCES live.weekly_sets (set_id) ON DELETE SET NULL,
                  created_by       int          REFERENCES live.users (user_id) ON DELETE SET NULL,
                  created_at       timestamptz  NOT NULL DEFAULT now(),
                  published_at     timestamptz
                );
                """
            )
        if not table_exists(conn, "live.question_group_items"):
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS live.question_group_items (
                  group_id    int      NOT NULL REFERENCES live.question_groups (group_id) ON DELETE CASCADE,
                  question_id int      NOT NULL REFERENCES live.questions (question_id) ON DELETE CASCADE,
                  position    smallint NOT NULL,
                  PRIMARY KEY (group_id, question_id),
                  UNIQUE (group_id, position)
                );
                """
            )
        if table_exists(conn, "live.admin_overrides"):
            has_return = conn.execute(
                text(
                    """SELECT 1 FROM pg_constraint
                       WHERE conname = 'admin_overrides_action_check'
                         AND pg_get_constraintdef(oid) LIKE '%return_needs_human%'"""
                )
            ).scalar()
            if not has_return:
                conn.exec_driver_sql("ALTER TABLE live.admin_overrides DROP CONSTRAINT IF EXISTS admin_overrides_action_check")
                conn.exec_driver_sql(
                    """ALTER TABLE live.admin_overrides
                       ADD CONSTRAINT admin_overrides_action_check
                       CHECK (action IN ('approve', 'reject', 'retire', 'restore', 'return_needs_human'))"""
                )
        # Đồng bộ idempotent yêu cầu sắp xếp (ORDER BY) cho các câu hỏi hiện có trong DB
        from .services.order_spec import sync_question_order_contract

        q_rows = q(
            conn,
            """SELECT qq.question_id, qq.question, qq.reference_sql, qq.compare_mode,
                      (SELECT tc.expected_result->'columns'
                       FROM live.test_cases tc
                       WHERE tc.question_id = qq.question_id
                       ORDER BY tc.test_id ASC LIMIT 1) AS cols
               FROM live.questions qq
               WHERE qq.reference_sql IS NOT NULL""",
        )
        for qr in q_rows:
            out_cols = list(qr["cols"]) if isinstance(qr.get("cols"), list) else []
            new_q, new_mode = sync_question_order_contract(
                qr["question"] or "",
                qr["reference_sql"],
                qr["compare_mode"],
                out_cols,
            )
            if new_q != qr["question"] or new_mode != qr["compare_mode"]:
                ex(
                    conn,
                    "UPDATE live.questions SET question=:qt, compare_mode=:cm WHERE question_id=:qid",
                    qt=new_q,
                    cm=new_mode,
                    qid=qr["question_id"],
                )
                ex(
                    conn,
                    """UPDATE live.test_cases
                       SET expected_result = jsonb_set(expected_result, '{compare_mode}', to_jsonb(CAST(:cm AS text)), true)
                       WHERE question_id=:qid""",
                    cm=new_mode,
                    qid=qr["question_id"],
                )
        if table_exists(conn, "draft.question_drafts"):
            d_rows = q(
                conn,
                """SELECT draft_id, question, reference_sql, compare_mode
                   FROM draft.question_drafts
                   WHERE reference_sql IS NOT NULL AND status <> 'reviewing'""",
            )
            for dr in d_rows:
                new_dq, new_dmode = sync_question_order_contract(
                    dr["question"] or "",
                    dr["reference_sql"],
                    dr["compare_mode"],
                )
                if new_dq != dr["question"] or new_dmode != dr["compare_mode"]:
                    ex(
                        conn,
                        "UPDATE draft.question_drafts SET question=:qt, compare_mode=:cm WHERE draft_id=:did AND status <> 'reviewing'",
                        qt=new_dq,
                        cm=new_dmode,
                        did=dr["draft_id"],
                    )
