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
