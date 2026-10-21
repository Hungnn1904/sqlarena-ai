import json

from sqlalchemy import Connection

from ..db import ex


def log(conn: Connection, actor_id: int | None, action: str, entity_type: str, entity_id, detail: dict | None = None) -> None:
    ex(conn, "INSERT INTO live.audit_logs (actor_id, action, entity_type, entity_id, detail) VALUES (:a, :ac, :et, :ei, CAST(:d AS jsonb))",
       a=actor_id, ac=action, et=entity_type, ei=str(entity_id), d=json.dumps(detail or {}, ensure_ascii=False, default=str))
