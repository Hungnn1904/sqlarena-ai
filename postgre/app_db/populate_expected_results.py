"""Populate core.source_questions.expected_result from the canonical Enterprise DB."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from db_readonly import check_sql

# This copy supports both a full repository checkout and a standalone SQL_run_API folder.
SQL_API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SQL_API_ROOT.parent


def load_env(path: Path) -> None:
    try:
        from dotenv import dotenv_values
    except ImportError:
        values = {}
    else:
        values = dotenv_values(path) if path.exists() else {}
    for key, value in values.items():
        if value is not None:
            os.environ.setdefault(key, value)


def db_env(prefix: str, key: str, default: str = "") -> str:
    return os.environ.get(f"{prefix}_DB_{key}", default)


def connect(prefix: str, *, read_only: bool = False):
    conn = psycopg.connect(
        host=db_env(prefix, "HOST", "localhost"),
        port=int(db_env(prefix, "PORT", "5432")),
        dbname=db_env(prefix, "NAME"),
        user=db_env(prefix, "USER"),
        password=db_env(prefix, "PASSWORD"),
        row_factory=dict_row,
    )
    if read_only:
        with conn.cursor() as cur:
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            timeout_ms = int(os.environ.get("EXPECTED_TIMEOUT_MS", "15000"))
            if timeout_ms < 100 or timeout_ms > 60000:
                raise ValueError("EXPECTED_TIMEOUT_MS must be between 100 and 60000")
            cur.execute("SELECT set_config('statement_timeout', %s, false)", (str(timeout_ms),))
            cur.execute("SET search_path = pg_catalog, public")
    return conn


def json_value(value):
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f") if value else "0"
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    raise TypeError(f"Unsupported PostgreSQL value: {type(value).__name__}")


def stable_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_result(row, source_conn):
    sql = row["reference_sql"].strip()
    check_sql(sql)
    with source_conn.transaction():
        with source_conn.cursor() as cur:
            cur.execute(sql)
            columns = [item.name for item in cur.description]
            rows = [{name: json_value(value) for name, value in item.items()} for item in cur.fetchall()]
    metadata = row["metadata"] or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    payload = {
        "dataset_ref": "enterprise/base",
        "dataset_version": "enterprise_v1",
        "compare_mode": "ordered" if metadata.get("ordering_required") else "unordered",
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
    payload["result_hash"] = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
    return row["question_id"], payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    configured_env = os.environ.get("SQLARENA_ENV_FILE")
    if configured_env:
        load_env(Path(configured_env))
    else:
        load_env(REPO_ROOT / ".env")
        load_env(SQL_API_ROOT / ".env")
        load_env(REPO_ROOT / "ai" / ".env")
    source = target = None
    results = []
    failures = []
    try:
        source = connect("ENTERPRISE", read_only=True)
        target = connect("ARENA")
        with target.cursor() as cur:
            cur.execute("SELECT question_id, reference_sql, metadata FROM core.source_questions ORDER BY question_id")
            questions = cur.fetchall()
        # End the read transaction before opening the single write transaction.
        target.commit()
        if len(questions) != 50:
            raise RuntimeError(f"Expected 50 source questions, found {len(questions)}")
        for row in questions:
            try:
                question_id, payload = build_result(row, source)
                results.append((question_id, payload))
                print(f"{question_id}: OK rows={payload['row_count']}", flush=True)
            except Exception as exc:
                failures.append((row["question_id"], str(exc)))
                print(f"{row['question_id']}: FAIL {exc}", flush=True)
        if failures:
            print(f"Không ghi DB: {len(failures)}/50 câu lỗi.", file=sys.stderr)
            return 1
        if args.dry_run:
            print("Dry-run OK: 50/50 results valid; sqlarena_db unchanged.")
            return 0
        with target.transaction():
            with target.cursor() as cur:
                cur.executemany(
                    "UPDATE core.source_questions SET expected_result = %s WHERE question_id = %s",
                    [(Jsonb(payload), question_id) for question_id, payload in results],
                )
        print("Wrote expected_result for 50/50 questions to sqlarena_db.core.source_questions.")
        return 0
    finally:
        if source is not None:
            source.close()
        if target is not None:
            target.close()


if __name__ == "__main__":
    raise SystemExit(main())
