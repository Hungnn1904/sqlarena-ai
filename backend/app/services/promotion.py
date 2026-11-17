"""Promote draft đã vượt pipeline → live.questions (ready) + live.test_cases, cùng một transaction, retry an toàn."""
import json

from sqlalchemy import Connection

from ..db import ex, q1

BASE_REF = "enterprise/base"


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def promote(conn: Connection, draft: dict, world_dataset_version: int, mode: str, reference_sql: str, testcases: list[dict]) -> int:
    """Idempotent: source_draft_id UNIQUE. Gọi lại khôi phục status='ready' nếu từng bị gỡ, và tự đưa lên bộ đề tuần published hiện tại nếu có."""
    if not testcases:
        raise ValueError("Không có test case: không được promote (fail closed).")
    row = q1(conn, """INSERT INTO live.questions (world_id, source_draft_id, title, question, reference_sql, compare_mode, difficulty,
                      skill_ids, tables_used, schema_text)
                      VALUES (:w, :d, :t, :q, :sql, :m, :diff, :sk, :tu, :st)
                      ON CONFLICT (source_draft_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        question = EXCLUDED.question,
                        reference_sql = EXCLUDED.reference_sql,
                        compare_mode = EXCLUDED.compare_mode,
                        status = 'ready',
                        retired_at = NULL,
                        retire_reason = NULL
                      RETURNING question_id""",
             w=draft["world_id"], d=draft["draft_id"], t=draft["title"], q=draft["question"], sql=reference_sql, m=mode,
             diff=draft["difficulty"], sk=list(draft["skill_ids"]), tu=list(draft["tables_used"] or []), st=draft.get("schema_text") or "")
    qid = row["question_id"]
    for t in testcases:
        expected = {"columns": t["expected_columns"], "rows": t["expected_rows"], "row_count": t["row_count"],
                    "result_hash": t["result_hash"], "compare_mode": t["compare_mode"], "dataset_fingerprint": t["dataset_version"]}
        ex(conn, """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
                    VALUES (:q, :ref, :ver, 'standard', CAST(:e AS jsonb), :h) ON CONFLICT DO NOTHING""",
           q=qid, ref=t["dataset_ref"], ver=world_dataset_version, e=_j(expected), h=t["dataset_ref"] != BASE_REF)
    pub = q1(conn, "SELECT set_id FROM live.weekly_sets WHERE status='published' ORDER BY set_id DESC LIMIT 1")
    if pub:
        ex(
            conn,
            """INSERT INTO live.weekly_set_items (set_id, question_id, position)
               VALUES (
                 :s,
                 :q,
                 (SELECT COALESCE(MAX(position), 0) + 1 FROM live.weekly_set_items WHERE set_id = :s)
               )
               ON CONFLICT (question_id) DO NOTHING""",
            s=pub["set_id"],
            q=qid,
        )
    return qid
