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
