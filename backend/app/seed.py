"""Nạp dữ liệu Core (world Enterprise, 6 skill S1–S6, 50 đề nguồn) từ seed/core_seed.json. Chạy lặp an toàn."""
import json

from sqlalchemy import Connection

from .config import get_settings
from .db import ex, q1
from .domain import DIFF_NUM
from .services import settings_registry


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def seed_core(conn: Connection) -> dict:
    data = json.loads(get_settings().seed_path.read_text(encoding="utf-8"))
    w = data["worlds"][0]
    ex(conn, """INSERT INTO core.worlds (name, display_name, schema_description, fk_relations, business_rules, planted_traps,
                allowed_sql_features, dataset_ref, variant_count, dataset_version)
                VALUES (:n, :d, CAST(:sd AS jsonb), CAST(:fk AS jsonb), CAST(:br AS jsonb), CAST(:pt AS jsonb), CAST(:al AS jsonb),
                        'enterprise', 0, 1) ON CONFLICT (name) DO NOTHING""",
       n=w["world_id"], d=w["name"], sd=_j(w["schema_description"]), fk=_j(w["fk_relations"]),
       br=_j(w["business_rules"]), pt=_j(w["planted_traps"]), al=_j(w["allowed_sql_features"]))
    world_pk = q1(conn, "SELECT world_id FROM core.worlds WHERE name=:n", n=w["world_id"])["world_id"]
    for s in data["skills"]:
        ex(conn, """INSERT INTO core.skills (code, name, category, base_difficulty) VALUES (:c, :n, :cat, :bd)
                    ON CONFLICT (code) DO NOTHING""", c=s["skill_id"], n=s["name"], cat=s["category"], bd=DIFF_NUM[s["base_difficulty"]])
    skill_pk = {r["code"]: r["skill_id"] for r in conn.exec_driver_sql("SELECT code, skill_id FROM core.skills").mappings()}
    inserted = 0
    for s in data["source_questions"]:
        inserted += ex(conn, """INSERT INTO core.source_questions (code, world_id, title, question_text, reference_sql, difficulty,
                    primary_skill_id, primary_business_domain, skills, depth, metadata, validation)
                    VALUES (:c, :w, :t, :qt, :rsql, :d, :sk, :dom, CAST(:skills AS jsonb), :depth, CAST(:m AS jsonb), CAST(:v AS jsonb))
                    ON CONFLICT (code) DO NOTHING""",
                       c=s["question_id"], w=world_pk, t=s["title"], qt=s["question_text"], rsql=s["reference_sql"],
                       d=DIFF_NUM[s["difficulty"]], sk=skill_pk[s["primary_skill_group"]], dom=s["primary_business_domain"],
                       skills=_j(s["skills"]), depth=s["depth"], m=_j(s["metadata"]), v=_j(s["validation"]))
    settings_registry.ensure_defaults(conn)
    return {"world_id": world_pk, "skills": len(skill_pk), "source_questions_inserted": inserted}
