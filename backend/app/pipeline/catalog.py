"""Dựng cấu trúc `data` mà engine cần (trước đây do ai/main.inspect_database đọc từ schema v1) từ schema ứng dụng mới."""
import psycopg
from sqlalchemy import Connection

from ..db import q, q1
from ..domain import DIFF_NAME
from . import engine as eng


class CatalogError(ValueError):
    pass


def load_engine_data(conn: Connection, world_name: str) -> dict:
    w = q1(conn, "SELECT * FROM core.worlds WHERE name=:n AND is_active", n=world_name)
    if not w or w["dialect"] != "postgresql":
        raise CatalogError(f"World '{world_name}' không tồn tại / không active / không phải PostgreSQL. Chạy `python -m app.cli seed`.")
    skills_rows = q(conn, "SELECT * FROM core.skills WHERE is_active ORDER BY skill_id")
    code_by_pk = {s["skill_id"]: s["code"] for s in skills_rows}
    skills = [{"skill_id": s["code"], "name": s["name"], "category": s["category"],
               "base_difficulty": DIFF_NAME[s["base_difficulty"]], "_pk": s["skill_id"]} for s in skills_rows]
    sources = [{"question_id": r["code"], "world_id": world_name, "title": r["title"], "question_text": r["question_text"],
                "reference_sql": r["reference_sql"], "difficulty": DIFF_NAME[r["difficulty"]],
                "primary_skill_group": code_by_pk.get(r["primary_skill_id"]), "primary_business_domain": r["primary_business_domain"],
                "skills": r["skills"], "depth": r["depth"], "metadata": r["metadata"], "validation": r["validation"]}
               for r in q(conn, "SELECT * FROM core.source_questions WHERE world_id=:w ORDER BY code", w=w["world_id"])]
    if not sources:
        raise CatalogError("Chưa có đề nguồn (core.source_questions). Chạy `python -m app.cli seed`.")
    drafts = [{"draft_id": d["draft_id"], "question": d["question"], "validation_report": d["validation_report"]}
              for d in q(conn, "SELECT draft_id, question, validation_report FROM draft.question_drafts WHERE world_id=:w ORDER BY draft_id",
                         w=w["world_id"])]
    tables = w["schema_description"]["tables"]
    schema = {t["table"]: {c["name"]: c["postgres_type"] for c in t["columns"]} for t in tables}
    world = {"world_id": w["name"], "name": w["display_name"], "dialect": w["dialect"],
             "schema_description": w["schema_description"], "fk_relations": w["fk_relations"],
             "business_rules": w["business_rules"], "planted_traps": w["planted_traps"],
             "allowed_sql_features": w["allowed_sql_features"], "_pk": w["world_id"],
             "dataset_ref": w["dataset_ref"], "dataset_version": w["dataset_version"]}
    return {"world": world, "skills": skills, "sources": sources, "drafts": drafts, "schema": schema,
            "skill_pk": {s["skill_id"]: s["_pk"] for s in skills}, "skill_code": code_by_pk}


def verify_catalog(config: dict, data: dict) -> None:
    """Schema Enterprise thật phải khớp metadata world; lệch thì dừng (không tự sửa database)."""
    kwargs = eng.arena.connection_config(config, "CATALOG")
    with psycopg.connect(**kwargs, options="-c default_transaction_read_only=on") as c:
        rows = c.execute("SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a "
                         "JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                         "WHERE n.nspname='public' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped "
                         "ORDER BY c.relname,a.attnum").fetchall()
    actual: dict = {}
    for t, col, typ in rows:
        actual.setdefault(t, {})[col] = typ
    if actual != data["schema"]:
        raise CatalogError("Schema Enterprise thực tế lệch metadata trong core.worlds; dừng sinh/duyệt, không sửa database.")
