"""Promote draft đã vượt pipeline → live.questions (ready) + live.test_cases, cùng một transaction, retry an toàn."""
import json

from sqlalchemy import Connection

from ..db import ex, q1
from .order_spec import sync_question_order_contract

BASE_REF = "enterprise/base"


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def promote(conn: Connection, draft: dict, world_dataset_version: int, mode: str, reference_sql: str, testcases: list[dict]) -> int:
    """Idempotent: source_draft_id UNIQUE. Đưa câu hỏi vào kho ready (Chưa có trên kệ); chỉ lên kệ Học viên khi Admin phát hành Bộ đề tuần."""
    if not testcases:
        raise ValueError("Không có test case: không được promote (fail closed).")
    out_cols = list(testcases[0].get("expected_columns") or [])
    synced_question, synced_mode = sync_question_order_contract(
        draft.get("question") or "",
        reference_sql,
        mode,
        out_cols,
    )
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
             w=draft["world_id"], d=draft["draft_id"], t=draft["title"], q=synced_question, sql=reference_sql, m=synced_mode,
             diff=draft["difficulty"], sk=list(draft["skill_ids"]), tu=list(draft["tables_used"] or []), st=draft.get("schema_text") or "")
    qid = row["question_id"]
    for t in testcases:
        r_hash = (
            t["result_hash"]
            if synced_mode == t.get("compare_mode")
            else __import__("app.pipeline.engine", fromlist=["rv"]).rv.result_hash(t["expected_rows"], synced_mode)
        )
        expected = {"columns": t["expected_columns"], "rows": t["expected_rows"], "row_count": t["row_count"],
                    "result_hash": r_hash, "compare_mode": synced_mode, "dataset_fingerprint": t["dataset_version"]}
        ex(conn, """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
                    VALUES (:q, :ref, :ver, 'standard', CAST(:e AS jsonb), :h)
                    ON CONFLICT (question_id, dataset_ref, dataset_version, type) DO UPDATE SET
                      expected_result = EXCLUDED.expected_result,
                      is_hidden = EXCLUDED.is_hidden""",
           q=qid, ref=t["dataset_ref"], ver=world_dataset_version, e=_j(expected), h=t["dataset_ref"] != BASE_REF)
    return qid
