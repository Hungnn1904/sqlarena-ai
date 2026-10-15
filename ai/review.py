"""SQLArena review pipeline (Model B): giai de k lan, doi chieu ket qua, sinh reference SQL + test case.

Chi doc Core/Enterprise; chi ghi vao draft.* (self_solve_runs, review_logs, test_cases, status/compare_mode).
Khong tu migration, khong tao role. Xem ai/review_pipeline.md.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from pglast import parser
from psycopg.types.json import Jsonb

import main as arena
from validator import SAFE_FUNCTIONS, SQLSchema, parse_select, strings, verify_readonly, walk

HERE = Path(__file__).resolve().parent
REVIEW_VERSION = "review_v1.0_model_b_consensus"
STATUSES = ("approved", "needs_human", "rejected")
SQL_ERRORS = (ValueError, TypeError, KeyError, parser.ParseError)
ORDER_WORDS = re.compile(r"(sắp xếp|xếp theo|thứ tự|giảm dần|tăng dần|từ cao|từ thấp|xếp hạng|top\s*\d|"
                         r"order by|\basc\b|\bdesc\b)", re.I)
LEAK_PATTERNS = (re.compile(r"\bselect\b[\s\S]{0,400}\bfrom\b", re.I), re.compile(r"```"),
                 re.compile(r"\breference_sql\b", re.I))
AGGREGATES = {"count", "sum", "avg", "min", "max", "string_agg", "array_agg"}


class InfraError(Exception):
    """Ollama/DB khong dung duoc: dung ca phien, tra draft ve pending, khong ket luan ve de."""


class SolverOutputError(ValueError):
    """Model B tra output khong dung dinh dang (loi cua mot lan giai, khong phai ha tang)."""


# --------------------------------------------------------------------------- config

def load_review_config(env=None):
    config = arena.load_config()
    if env:
        config.update(env)

    def number(key, default, cast=int, low=None):
        value = cast(config.get(key) or default)
        if low is not None and value < low:
            raise ValueError(f"Cau hinh khong hop le: {key} phai >= {low}")
        config[key] = value

    config["REVIEW_MODEL_NAME"] = config.get("REVIEW_MODEL_NAME") or config["MODEL_NAME"]
    config["REVIEW_OLLAMA_HOST"] = config.get("REVIEW_OLLAMA_HOST") or config["OLLAMA_HOST"]
    number("REVIEW_SAMPLES", 3, int, 1)
    number("REVIEW_SAMPLE_RETRIES", 1, int, 0)
    number("REVIEW_TEMPERATURE", 0.3, float, 0)
    number("REVIEW_NUM_PREDICT", 900, int, 64)
    number("REVIEW_MAX_ROWS", 5000, int, 1)
    action = (config.get("REVIEW_ZERO_VALID_ACTION") or "rejected").strip()
    if action not in ("rejected", "needs_human"):
        raise ValueError("REVIEW_ZERO_VALID_ACTION chi nhan rejected hoac needs_human.")
    config["REVIEW_ZERO_VALID_ACTION"] = action
    think = (config.get("REVIEW_THINK") or "").strip().lower()
    config["REVIEW_THINK"] = {"": None, "true": True, "false": False}.get(think, "bad")
    if config["REVIEW_THINK"] == "bad":
        raise ValueError("REVIEW_THINK chi nhan true, false hoac de trong.")
    config["REVIEW_VARIANT_DBS"] = [d.strip() for d in (config.get("REVIEW_VARIANT_DBS") or "").split(",") if d.strip()]
    return config


# --------------------------------------------------------------------------- result normalisation / comparison

def norm_value(value):
    """Gia tri JSON-able, so sanh duoc: so -> chuoi chuan hoa, ngay -> ISO, None giu nguyen."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, Decimal, float)):
        try:
            number = value if isinstance(value, Decimal) else Decimal(repr(round(value, 9)) if isinstance(value, float) else value)
        except (InvalidOperation, ValueError):
            return str(value)
        if not number.is_finite():
            return str(number)
        text = format(number.normalize(), "f")
        return "0" if text in ("-0", "0.0") else text
    if isinstance(value, (datetime, date, dtime)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return f"{value.total_seconds():.6f}".rstrip("0").rstrip(".")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, (list, tuple)):
        return [norm_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): norm_value(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    return str(value)


def norm_rows(rows):
    return [[norm_value(v) for v in row] for row in rows]


def _row_key(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def canonical(rows, mode):
    keys = [_row_key(r) for r in rows]
    return keys if mode == "ordered" else sorted(keys)


def result_hash(rows, mode):
    return hashlib.sha256("\n".join(canonical(rows, mode)).encode("utf-8")).hexdigest()


def same_result(a, b, mode):
    """So theo vi tri cot (ten alias cua cac loi giai co the khac nhau)."""
    if a["status"] != "ok" or b["status"] != "ok":
        return False
    if len(a["columns"]) != len(b["columns"]) or a["row_count"] != b["row_count"]:
        return False
    return canonical(a["rows"], mode) == canonical(b["rows"], mode)


def diff_hint(a, b, mode):
    """Mo ta ngan su khac nhau (cho admin); khong day ca ket qua."""
    hint = {"columns": [len(a["columns"]), len(b["columns"])], "row_count": [a["row_count"], b["row_count"]]}
    if len(a["columns"]) == len(b["columns"]):
        ka, kb = canonical(a["rows"], "unordered"), canonical(b["rows"], "unordered")
        only_a = [k for k in ka if k not in set(kb)][:3]
        only_b = [k for k in kb if k not in set(ka)][:3]
        hint["only_in_selected"] = only_a
        hint["only_in_other"] = only_b
        hint["same_as_multiset"] = ka == kb
    return hint


# --------------------------------------------------------------------------- SQL analysis (AST)

def sql_features(tree):
    tags = Counter(tag for tag, _ in walk(tree))
    funcs = [strings(node["funcname"])[-1] for tag, node in walk(tree) if tag == "FuncCall"]
    return {"joins": tags["JoinExpr"], "ctes": tags["CommonTableExpr"], "sublinks": tags["SubLink"],
            "range_subselects": tags["RangeSubselect"], "selects": tags["SelectStmt"],
            "range_vars": tags["RangeVar"], "aggregate": any(f in AGGREGATES for f in funcs),
            "window": any(tag == "FuncCall" and node.get("over") for tag, node in walk(tree)),
            "recursive": any(tag == "withClause" and node.get("recursive") for tag, node in walk(tree)),
            "ast_nodes": sum(tags.values())}


def guard_sql(sql, schema):
    """AST guard cua validator.py + gioi han bang theo cac bang de khai bao."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL rong.")
    if len(sql) > 5000:
        raise ValueError("SQL qua dai (>5000 ky tu).")
    tree = parse_select(sql)
    resolver = SQLSchema(schema)
    outputs = resolver.query(tree)
    return tree, {"tables": sorted(resolver.tables), "output_columns": list(outputs), "features": sql_features(tree)}


def order_keys(tree):
    query = tree["SelectStmt"]
    keys = []
    for item in query.get("sortClause") or []:
        node = item["SortBy"]["node"]
        fields = [f["String"]["sval"] for f in node.get("ColumnRef", {}).get("fields", []) if "String" in f]
        keys.append(fields[-1] if fields else None)
    return keys


def ordering_requested(question):
    return bool(ORDER_WORDS.search(unicodedata.normalize("NFC", question or "")))


def decide_mode(tree, question):
    return "ordered" if order_keys(tree) and ordering_requested(question) else "unordered"


def tiebreaker_ok(tree, primary_keys):
    keys = order_keys(tree)
    return any(k and (k.endswith("_id") or k in primary_keys) for k in keys)


def hardcoded_id_literals(tree, question):
    """Cot *_id so sanh voi hang so khong xuat hien trong de -> nghi hardcode theo du lieu hien co."""
    found = []
    for tag, node in walk(tree):
        if tag != "A_Expr":
            continue
        left = node.get("lexpr", {}).get("ColumnRef")
        if not left:
            continue
        fields = [f["String"]["sval"] for f in left.get("fields", []) if "String" in f]
        if not fields or not fields[-1].endswith("_id"):
            continue
        for sub_tag, sub in walk(node.get("rexpr", {})):
            if sub_tag == "A_Const" and "ival" in sub:
                value = sub["ival"].get("ival", 0)
                if not re.search(rf"(?<!\d){value}(?!\d)", question or ""):
                    found.append(f"{fields[-1]}={value}")
    return found


def skill_difficulty_issues(skill, difficulty, f):
    issues = []
    if skill == "S1" and (f["joins"] or f["aggregate"] or f["ctes"] or f["sublinks"] or f["window"] or f["selects"] > 1):
        issues.append("skill_s1_has_forbidden_features")
    if skill == "S2" and not (f["joins"] or f["range_vars"] >= 2):
        issues.append("skill_s2_no_join")
    if skill == "S3" and not f["aggregate"]:
        issues.append("skill_s3_no_aggregate")
    if skill == "S4" and not (f["sublinks"] or f["range_subselects"] or f["joins"]):
        issues.append("skill_s4_no_subquery")
    if skill == "S5" and not (f["ctes"] or f["window"]):
        issues.append("skill_s5_no_cte_or_window")
    if skill == "S6" and not (f["recursive"] or (f["window"] and f["selects"] >= 3)):
        issues.append("skill_s6_no_recursion_or_layers")
    if difficulty == "easy" and (f["ctes"] or f["window"] or f["sublinks"]):
        issues.append("difficulty_easy_exceeded")
    return issues


# --------------------------------------------------------------------------- database access

class PgDataset:
    """Mot dataset de thuc thi SQL (chi SELECT, role chi doc)."""

    def __init__(self, ref, kwargs, version, timeout_ms, max_rows):
        self.ref, self.kwargs, self.version = ref, kwargs, version
        self.timeout_ms, self.max_rows = timeout_ms, max_rows

    def run(self, sql):
        started = time.perf_counter()
        try:
            with psycopg.connect(**self.kwargs, autocommit=True) as conn:
                with conn.transaction():
                    conn.execute("SET TRANSACTION READ ONLY")
                    conn.execute("SET LOCAL search_path = pg_catalog, public")
                    conn.execute("SET LOCAL TIME ZONE 'UTC'")
                    conn.execute("SELECT set_config('statement_timeout',%s,true)", (str(self.timeout_ms),))
                    rows, columns, truncated = [], None, False
                    with conn.cursor(name="review_ro") as cur:
                        cur.execute(sql)
                        while True:
                            batch = cur.fetchmany(500)
                            if cur.description:
                                columns = [c.name for c in cur.description]
                            if not batch:
                                break
                            rows.extend(batch)
                            if len(rows) > self.max_rows:
                                rows, truncated = rows[:self.max_rows], True
                                break
            return {"status": "ok", "columns": columns or [], "rows": norm_rows(rows), "row_count": len(rows),
                    "truncated": truncated, "runtime_ms": round((time.perf_counter() - started) * 1000, 1)}
        except psycopg.errors.QueryCanceled:
            return {"status": "timeout", "error": f"Vuot {self.timeout_ms} ms"}
        except psycopg.OperationalError as exc:
            raise InfraError(f"Khong ket noi duoc {self.ref}: {exc}") from exc
        except psycopg.Error as exc:
            return {"status": "execution_error", "error": str(exc).splitlines()[0][:300]}


def catalog_version(config, dbname):
    """Phien ban dataset = hash cau truc + hash du lieu tung bang (doc bang tai khoan CATALOG)."""
    kwargs = {**arena.connection_config(config, "CATALOG"), "dbname": dbname}
    with psycopg.connect(**kwargs, options="-c default_transaction_read_only=on") as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY 1").fetchall()]
        parts = []
        for table in tables:
            q = psycopg.sql.SQL("SELECT count(*), md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM "
                                "(SELECT md5(row_to_json(t)::text) h FROM public.{} t) x").format(psycopg.sql.Identifier(table))
            parts.append((table, *conn.execute(q).fetchone()))
        columns = conn.execute(
            "SELECT table_name,column_name,data_type FROM information_schema.columns "
            "WHERE table_schema='public' ORDER BY 1,ordinal_position").fetchall()
    return hashlib.sha256(json.dumps([parts, columns], default=str).encode()).hexdigest()[:16], tables, columns


def build_datasets(config):
    """enterprise/base (+ cac DB variant neu co). Bat buoc role chi doc dung chuan verify_readonly."""
    if not config.get("ENTERPRISE_DB_USER"):
        raise ValueError("Chua cau hinh ENTERPRISE_DB_USER (role chi doc). Chay postgre/enterprise_db/03_create_readonly_role.sql "
                         "roi dien ENTERPRISE_DB_USER/ENTERPRISE_DB_PASSWORD trong ai/.env.")
    datasets, base_columns = [], None
    names = [(config["ENTERPRISE_DB_NAME"], "enterprise/base")] + [(n, f"enterprise/{n}") for n in config["REVIEW_VARIANT_DBS"]]
    for dbname, ref in names:
        version, tables, columns = catalog_version(config, dbname)
        if base_columns is None:
            base_columns = columns
        elif columns != base_columns:
            raise ValueError(f"Variant {dbname} co cau truc bang/cot khac enterprise_db; dataset variant phai cung schema.")
        kwargs = {"host": config["ENTERPRISE_DB_HOST"], "port": int(config["ENTERPRISE_DB_PORT"]), "dbname": dbname,
                  "user": config["ENTERPRISE_DB_USER"], "password": config.get("ENTERPRISE_DB_PASSWORD", ""),
                  "connect_timeout": 5}
        try:
            with psycopg.connect(**kwargs, autocommit=True) as conn:
                with conn.transaction():
                    conn.execute("SET TRANSACTION READ ONLY")
                    conn.execute("SET LOCAL search_path = pg_catalog, public")
                    verify_readonly(conn, {t: {} for t in tables})
        except psycopg.OperationalError as exc:
            raise InfraError(f"Khong dang nhap duoc {dbname} bang ENTERPRISE_DB_USER: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"Role chi doc khong dat chuan an toan tren {dbname}: {exc}. "
                             f"Xem postgre/enterprise_db/03_create_readonly_role.sql.") from exc
        datasets.append(PgDataset(ref, kwargs, version, config["STATEMENT_TIMEOUT_MS"], config["REVIEW_MAX_ROWS"]))
    return datasets


def migration_gaps(conn):
    gaps = []
    if not conn.execute("SELECT to_regclass('draft.test_cases') AS t").fetchone()["t"]:
        gaps.append("thieu bang draft.test_cases")
    cols = {r["column_name"] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='draft' AND table_name='self_solve_runs'").fetchall()}
    for col in ("sample_index", "is_selected", "exec_status", "row_count", "result_hash", "error", "review_model"):
        if col not in cols:
            gaps.append(f"draft.self_solve_runs thieu cot {col}")
    stage = [r["d"] for r in conn.execute(
        "SELECT pg_get_constraintdef(oid) AS d FROM pg_constraint WHERE conrelid=to_regclass('draft.review_logs') "
        "AND conname='chk_review_stage'").fetchall()]
    if not stage or "'decision'" not in stage[0] or "'test_case'" not in stage[0]:
        gaps.append("draft.review_logs.chk_review_stage chua cho phep test_case/decision")
    return gaps


# --------------------------------------------------------------------------- draft context

def draft_context(row):
    sc, vr = row.get("schema_context") or {}, row.get("validation_report") or {}
    meta = vr.get("candidate_metadata") or {}
    tables_used = list(meta.get("tables_used") or sc.get("tables_used") or [])
    defs = {t["table"]: t for t in sc.get("tables", [])}
    skills = row.get("skills") or []
    schema = {t: {c["name"]: c.get("type") or c.get("postgres_type") or "" for c in defs[t]["columns"]} for t in tables_used if t in defs}
    used = set(tables_used)
    fks = [f"{f['table_name']}({', '.join(f['columns'])}) -> {f['referenced_table']}({', '.join(f['referenced_columns'])})"
           for f in sc.get("fk_relations", []) if f.get("table_name") in used and f.get("referenced_table") in used]
    checks = {t: [c[:200] for c in defs[t].get("checks", [])] for t in tables_used if t in defs and defs[t].get("checks")}
    rules = [f"{r.get('code')}: {r.get('title')}" for r in (sc.get("business_rules") or [])[:4]
             if set(r.get("related_tables", [])) & used]
    return {"draft_id": row["draft_id"], "question": row["question"], "difficulty": row["difficulty"],
            "skill": meta.get("primary_skill_group") or (skills[0] if skills else None),
            "tables_used": tables_used, "schema": schema, "fks": fks, "checks": checks, "rules": rules,
            "primary_keys": {k for t in tables_used if t in defs for k in defs[t].get("primary_key", [])},
            "schema_text": row.get("schema_text") or "", "duplicate": vr.get("duplicate") or {}}


# --------------------------------------------------------------------------- Model B

def build_solver_prompt(ctx, feedback=None):
    schema_text = ctx["schema_text"] or "\n\n".join(
        f"public.{t}\n" + "\n".join(f"  - {c}: {ty}" for c, ty in cols.items()) for t, cols in ctx["schema"].items())
    parts = ["You are Model B, a careful PostgreSQL author. Write ONE read-only SQL query that answers the question exactly.",
             "QUESTION (Vietnamese):\n" + ctx["question"].strip(),
             "ALLOWED TABLES (reference no other table):\n" + schema_text]
    if ctx["fks"]:
        parts.append("FOREIGN KEYS between allowed tables:\n" + "\n".join("- " + f for f in ctx["fks"]))
    if ctx["checks"]:
        parts.append("CHECK CONSTRAINTS (valid values):\n" + "\n".join(
            f"- {t}: {c}" for t, cs in ctx["checks"].items() for c in cs))
    if ctx["rules"]:
        parts.append("DATASET BUSINESS RULES:\n" + "\n".join("- " + r for r in ctx["rules"]))
    parts.append("SQL RULES:\n" + "\n".join("- " + r for r in (
        "Exactly one PostgreSQL SELECT statement (WITH ... SELECT allowed). No DDL/DML.",
        "Use only the allowed tables and only columns that exist in them. Give every output column an alias.",
        "Follow the question literally: output columns and their order, filters, rounding, grouping.",
        "Add ORDER BY only if the question asks for an ordering; if it does, end with a unique tie-breaker key.",
        "No now(), CURRENT_DATE or CURRENT_TIMESTAMP; use the dates stated in the question.",
        "Do not hardcode ids or values that the question does not state.",
        "Allowed functions only: " + ", ".join(sorted(SAFE_FUNCTIONS)) + ".")))
    if feedback:
        parts.append("YOUR PREVIOUS ATTEMPT WAS REJECTED:\n" + feedback + "\nFix it and answer again.")
    parts.append('Return only JSON: {"sql": "<one SELECT statement>"}')
    return "\n\n".join(parts)


def solver_format():
    return {"type": "object", "properties": {"sql": {"type": "string", "minLength": 1}},
            "required": ["sql"], "additionalProperties": False}


def call_solver(config, prompt, seed, temperature):
    options = {"num_ctx": config["OLLAMA_CONTEXT_SIZE"], "num_predict": config["REVIEW_NUM_PREDICT"],
               "temperature": temperature, "seed": seed}
    body = {"model": config["REVIEW_MODEL_NAME"], "prompt": prompt, "stream": False,
            "format": solver_format(), "options": options}
    if config["REVIEW_THINK"] is not None:
        body["think"] = config["REVIEW_THINK"]
    try:
        result = arena.ollama_request({**config, "OLLAMA_HOST": config["REVIEW_OLLAMA_HOST"]}, "/api/generate", body)
    except ValueError as exc:
        raise InfraError(str(exc)) from exc
    if result.get("done_reason") == "length":
        raise SolverOutputError("Output bi cat do het token; tra SQL ngan hon.")
    if result.get("prompt_eval_count", 0) >= config["OLLAMA_CONTEXT_SIZE"] - 128:
        raise InfraError("Prompt gan/vuot cua so context; tang OLLAMA_CONTEXT_SIZE hoac giam bang de.")
    try:
        sql = json.loads(result["response"])["sql"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SolverOutputError("Output khong phai JSON {sql: ...}.") from exc
    if not isinstance(sql, str) or not sql.strip():
        raise SolverOutputError("Truong sql rong.")
    return sql.strip().rstrip(";").strip(), {k: result.get(k) for k in ("prompt_eval_count", "eval_count", "total_duration")}


def solve_samples(ctx, datasets, solver, k, retries, log=lambda *_: None):
    """Moi mau: toi da 1+retries lan goi; chi nhan mau qua guard va chay duoc tren MOI dataset."""
    samples = []
    for index in range(k):
        feedback, attempts = None, []
        sample = {"index": index, "ok": False, "sql": None, "attempts": attempts}
        for attempt in range(retries + 1):
            record = {"attempt": attempt}
            attempts.append(record)
            try:
                sql, metrics = solver(build_solver_prompt(ctx, feedback), index * 100 + attempt,
                                      0.0 if index == 0 else None)
            except SolverOutputError as exc:
                record["error"] = feedback = f"format: {exc}"
                continue
            record["sql"], sample["sql"] = sql, sql
            try:
                tree, info = guard_sql(sql, ctx["schema"])
            except SQL_ERRORS as exc:
                record["error"] = feedback = f"guard: {exc}"
                continue
            results = {}
            for ds in datasets:
                results[ds.ref] = ds.run(sql)
            bad = next(((r, ds) for ds, r in zip(datasets, results.values())
                        if r["status"] != "ok"), None)
            if bad:
                record["error"] = feedback = f"execution on {bad[1].ref}: {bad[0].get('error')}"
                continue
            sample.update(ok=True, tree=tree, info=info, results=results, error=None)
            break
        if not sample["ok"]:
            sample["error"] = attempts[-1].get("error", "unknown")
        log(index, sample)
        samples.append(sample)
    return samples


# --------------------------------------------------------------------------- review decision

def pre_checks(ctx):
    issues = []
    if not (ctx["question"] or "").strip() or len(ctx["question"].strip()) < 10:
        issues.append("question_empty_or_too_short")
    if not ctx["tables_used"] or set(ctx["tables_used"]) - set(ctx["schema"]):
        issues.append("declared_tables_invalid")
    if ctx["skill"] not in {f"S{i}" for i in range(1, 7)}:
        issues.append("skill_unknown")
    if ctx["difficulty"] not in ("easy", "medium", "hard"):
        issues.append("difficulty_unknown")
    if any(p.search(ctx["question"] or "") for p in LEAK_PATTERNS):
        issues.append("answer_in_question")
    return issues


def review_draft(ctx, datasets, solver, k, retries, zero_valid_action="rejected", log=lambda *_: None):
    """Tra ve dict ket qua; khong ghi DB. Fail-closed: thieu bang chung -> khong approved."""
    out = {"draft_id": ctx["draft_id"], "status": None, "reasons": [], "mode": None, "reference_sql": None,
           "samples": [], "testcases": [], "stages": {}, "notes": []}
    pre = pre_checks(ctx)
    out["stages"]["pre"] = {"passed": not pre, "reasons": pre}
    if pre:
        out.update(status="rejected", reasons=pre)
        return out

    samples = solve_samples(ctx, datasets, solver, k, retries, log)
    out["samples"] = samples
    valid = [s for s in samples if s["ok"]]
    out["stages"]["solve"] = {"passed": len(valid) == k, "valid": len(valid), "k": k}
    if not valid:
        out.update(status=zero_valid_action, reasons=["no_valid_solution"])
        return out
    if len(valid) < k:
        out.update(status="needs_human", reasons=["insufficient_valid_solutions"])
        return out

    # De yeu cau sap xep -> uu tien loi giai co ORDER BY (neu khong, tham chieu se mat thu tu cua de).
    pool = [s for s in valid if order_keys(s["tree"])] if ordering_requested(ctx["question"]) else []
    selected = min(pool or valid, key=lambda s: (s["info"]["features"]["ast_nodes"], len(s["sql"]), s["index"]))
    mode = decide_mode(selected["tree"], ctx["question"])
    out["mode"], out["reference_sql"] = mode, selected["sql"]
    mismatches = {}
    for s in valid:
        s["is_selected"] = s is selected
        for ds in datasets:
            if s is selected or same_result(selected["results"][ds.ref], s["results"][ds.ref], mode):
                continue
            unordered_ok = same_result(selected["results"][ds.ref], s["results"][ds.ref], "unordered")
            mismatches.setdefault(s["index"], {})[ds.ref] = (
                {"order_only": True} if unordered_ok else diff_hint(selected["results"][ds.ref], s["results"][ds.ref], mode))
    out["stages"]["consensus"] = {"passed": not mismatches, "mismatches": mismatches}
    for s in valid:
        s["mismatch"] = mismatches.get(s["index"])
    if mismatches:
        reasons = ["order_disagreement" if all(v.get("order_only") for m in mismatches.values() for v in m.values())
                   else "consensus_disagreement"]
        out.update(status="needs_human", reasons=reasons)
        return out

    reasons_reject, reasons_human = [], []
    for ds in datasets:
        res = selected["results"][ds.ref]
        if res["truncated"]:
            reasons_human.append("result_too_large")
        elif res["row_count"] == 0:
            reasons_human.append("empty_result")
        again = ds.run(selected["sql"])
        if again["status"] != "ok" or not same_result(res, again, "unordered"):
            reasons_reject.append("nondeterministic_reference")
        elif mode == "ordered" and not same_result(res, again, "ordered"):
            reasons_reject.append("nondeterministic_reference")
    features = selected["info"]["features"]
    reasons_human += skill_difficulty_issues(ctx["skill"], ctx["difficulty"], features)
    if mode == "ordered" and not tiebreaker_ok(selected["tree"], ctx["primary_keys"]):
        reasons_human.append("order_tiebreaker_missing")
    hard = hardcoded_id_literals(selected["tree"], ctx["question"])
    if hard:
        reasons_human.append("hardcoded_id_literal")
        out["notes"].append({"hardcoded": hard})
    if ctx["duplicate"].get("suspected_duplicate"):
        reasons_human.append("suspected_duplicate")
    if len(datasets) == 1:
        out["notes"].append("Chi co 1 dataset: chua bat duoc dap an dung rieng cho du lieu hien co (hardcode gia tri).")
    out["stages"]["post"] = {"passed": not (reasons_reject or reasons_human),
                             "reasons": sorted(set(reasons_reject + reasons_human)), "features": features}
    if reasons_reject:
        out.update(status="rejected", reasons=sorted(set(reasons_reject + reasons_human)))
        return out
    if reasons_human:
        out.update(status="needs_human", reasons=sorted(set(reasons_human)))
        return out

    for ds in datasets:
        res = selected["results"][ds.ref]
        out["testcases"].append({"dataset_ref": ds.ref, "dataset_version": ds.version, "compare_mode": mode,
                                 "reference_sql": selected["sql"], "expected_columns": res["columns"],
                                 "expected_rows": res["rows"], "row_count": res["row_count"],
                                 "result_hash": result_hash(res["rows"], mode)})
    out.update(status="approved", reasons=[])
    return out


# --------------------------------------------------------------------------- persistence

def sample_rows(result, model):
    rows = []
    for s in result["samples"]:
        res = (s.get("results") or {})
        first = next(iter(res.values()), None) or {}
        rows.append({"sample_index": s["index"], "sql": s["sql"], "is_selected": bool(s.get("is_selected")),
                     "exec_status": "ok" if s["ok"] else "failed", "row_count": first.get("row_count"),
                     "hash": result_hash(first["rows"], result["mode"] or "unordered") if first else None,
                     "error": s.get("error"), "mismatch": s.get("mismatch"),
                     "matched": [ref for ref, r in res.items() if not (s.get("mismatch") or {}).get(ref)]})
    return rows


def persist(config, result, datasets):
    model = config["REVIEW_MODEL_NAME"]
    dataset_info = [{"ref": d.ref, "version": d.version} for d in datasets]
    rows = sample_rows(result, model)
    with arena.connect(config, "ARENA", readonly=False) as conn:
        draft_id = result["draft_id"]
        if result["status"] == "approved":
            updated = conn.execute("UPDATE draft.question_drafts SET status=%s, compare_mode=%s WHERE draft_id=%s "
                                   "AND status='reviewing' RETURNING draft_id", (result["status"], result["mode"], draft_id)).fetchone()
        else:
            updated = conn.execute("UPDATE draft.question_drafts SET status=%s WHERE draft_id=%s "
                                   "AND status='reviewing' RETURNING draft_id", (result["status"], draft_id)).fetchone()
        if not updated:
            raise ValueError(f"Draft {draft_id} khong con o trang thai reviewing; khong ghi de ket qua.")
        conn.execute("DELETE FROM draft.self_solve_runs WHERE draft_id=%s", (draft_id,))
        conn.execute("DELETE FROM draft.test_cases WHERE draft_id=%s", (draft_id,))
        for r in rows:
            conn.execute("INSERT INTO draft.self_solve_runs (draft_id, model_sql, matched_datasets, mismatch_detail, "
                         "sample_index, is_selected, exec_status, row_count, result_hash, error, review_model) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                         (draft_id, r["sql"], Jsonb(r["matched"]), Jsonb(r["mismatch"]) if r["mismatch"] else None,
                          r["sample_index"], r["is_selected"], r["exec_status"], r["row_count"], r["hash"],
                          r["error"], model))
        stages = result["stages"]

        def log(stage, passed, reasons, raw, score=None):
            conn.execute("INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, raw_output) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s)", (draft_id, stage, passed, score, Jsonb(reasons), model,
                                                          Jsonb({"review_version": REVIEW_VERSION, **raw})))
        log("code_check", stages["pre"]["passed"], stages["pre"]["reasons"], {"phase": "pre"})
        if "solve" in stages:
            k = stages["solve"]["k"]
            log("self_solve", stages["solve"]["passed"], [] if stages["solve"]["passed"] else ["not_all_samples_valid"],
                {"samples": [{k2: v for k2, v in r.items() if k2 != "sql"} for r in rows], "datasets": dataset_info},
                score=round(100 * stages["solve"]["valid"] / k, 2))
        if "post" in stages:
            log("code_check", stages["post"]["passed"], stages["post"]["reasons"],
                {"phase": "post", "features": stages["post"]["features"], "notes": result["notes"]})
        if result["testcases"]:
            for t in result["testcases"]:
                conn.execute("INSERT INTO draft.test_cases (draft_id, dataset_ref, dataset_version, compare_mode, reference_sql, "
                             "expected_columns, expected_rows, row_count, result_hash, review_version) "
                             "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                             (draft_id, t["dataset_ref"], t["dataset_version"], t["compare_mode"], t["reference_sql"],
                              Jsonb(t["expected_columns"]), Jsonb(t["expected_rows"]), t["row_count"],
                              t["result_hash"], REVIEW_VERSION))
            log("test_case", True, [], {"datasets": [{"ref": t["dataset_ref"], "rows": t["row_count"],
                                                     "hash": t["result_hash"]} for t in result["testcases"]]})
        log("decision", result["status"] == "approved", result["reasons"],
            {"status": result["status"], "mode": result["mode"], "datasets": dataset_info})


# --------------------------------------------------------------------------- CLI plumbing

def make_solver(config):
    def solver(prompt, seed, temperature):
        return call_solver(config, prompt, seed, config["REVIEW_TEMPERATURE"] if temperature is None else temperature)
    return solver


def ensure_model(config):
    tags = arena.ollama_request({**config, "OLLAMA_HOST": config["REVIEW_OLLAMA_HOST"]}, "/api/tags")
    names = {m["name"] for m in tags.get("models", [])}
    wanted = config["REVIEW_MODEL_NAME"]
    if wanted not in names and wanted + ":latest" not in names:
        raise ValueError(f"Model B {wanted} chua cai. Tu chay: ollama pull {wanted}")


def new_output(prefix):
    folder = HERE / "outputs"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for suffix in range(10000):
        path = folder / f"{prefix}_{stamp}{'_' + str(suffix) if suffix else ''}.json"
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write("{}\n")
            return path
        except FileExistsError:
            continue
    raise ValueError("Khong tao duoc ten output rieng.")


def summarize(result):
    return {"draft_id": result["draft_id"], "status": result["status"], "reasons": result["reasons"],
            "mode": result["mode"], "reference_sql": result["reference_sql"], "notes": result["notes"],
            "stages": result["stages"], "samples": [
                {"index": s["index"], "ok": s["ok"], "sql": s["sql"], "error": s.get("error"),
                 "rows": {ref: r.get("row_count") for ref, r in (s.get("results") or {}).items()},
                 "mismatch": s.get("mismatch")} for s in result["samples"]],
            "testcases": [{k: v for k, v in t.items() if k != "expected_rows"} for t in result["testcases"]]}


def fetch_pending(conn, limit, draft_id):
    if draft_id:
        return conn.execute("SELECT * FROM draft.question_drafts WHERE draft_id=%s AND status='pending'", (draft_id,)).fetchall()
    sql = "SELECT * FROM draft.question_drafts WHERE status='pending' ORDER BY draft_id"
    return conn.execute(sql + (" LIMIT %s" if limit else ""), (limit,) if limit else ()).fetchall()


def claim(config, draft_id):
    with arena.connect(config, "ARENA", readonly=False) as conn:
        return bool(conn.execute("UPDATE draft.question_drafts SET status='reviewing' WHERE draft_id=%s "
                                 "AND status='pending' RETURNING draft_id", (draft_id,)).fetchone())


def release(config, draft_id):
    with arena.connect(config, "ARENA", readonly=False) as conn:
        conn.execute("UPDATE draft.question_drafts SET status='pending' WHERE draft_id=%s AND status='reviewing'", (draft_id,))


def confirm(text, assume_yes):
    if assume_yes:
        return True
    return input(text + " [y/N] ").strip().lower() in ("y", "yes", "c", "co")


def cmd_check(config):
    with arena.connect(config, "ARENA") as conn:
        gaps = migration_gaps(conn)
        counts = conn.execute("SELECT status, count(*) AS n FROM draft.question_drafts GROUP BY status ORDER BY 1").fetchall()
    for gap in gaps:
        print("Thiếu migration: " + gap)
    print("Draft theo trạng thái: " + (", ".join(f"{r['status']}={r['n']}" for r in counts) or "chưa có"))
    ensure_model(config)
    print(f"Model B: {config['REVIEW_MODEL_NAME']} @ {config['REVIEW_OLLAMA_HOST']} (đã cài)")
    if config["REVIEW_MODEL_NAME"] == config["MODEL_NAME"]:
        print("Cảnh báo: Model B trùng Model A; sai lệch của hai model sẽ giống nhau, đồng thuận kém tin cậy.")
    datasets = build_datasets(config)
    for ds in datasets:
        print(f"Dataset {ds.ref}: role chỉ đọc đạt chuẩn, phiên bản {ds.version}")
    return 1 if gaps else 0


def cmd_review(config, options):
    k = options.samples or config["REVIEW_SAMPLES"]
    with arena.connect(config, "ARENA") as conn:
        gaps = migration_gaps(conn)
        if gaps:
            raise ValueError("Chưa chạy migration 03_create_review_pipeline.sql: " + "; ".join(gaps))
        rows = fetch_pending(conn, options.limit, options.draft_id)
    if not rows:
        print("Không có draft pending để kiểm duyệt.")
        return 0
    ensure_model(config)
    datasets = build_datasets(config)
    print(f"{len(rows)} draft pending | Model B {config['REVIEW_MODEL_NAME']} | k={k} | "
          f"dataset: {', '.join(d.ref for d in datasets)}" + (" | DRY-RUN" if options.dry_run else ""))
    if not confirm("Bắt đầu kiểm duyệt?", options.yes):
        print("Đã hủy.")
        return 0
    output = new_output("review")
    session = {"review_version": REVIEW_VERSION, "started_at": datetime.now().astimezone().isoformat(),
               "model_b": config["REVIEW_MODEL_NAME"], "k": k, "dry_run": options.dry_run,
               "datasets": [{"ref": d.ref, "version": d.version} for d in datasets], "results": [], "status": "running"}
    solver, counts = make_solver(config), Counter()
    try:
        for row in rows:
            ctx = draft_context(row)
            if not options.dry_run and not claim(config, ctx["draft_id"]):
                print(f"Draft {ctx['draft_id']}: đã bị tiến trình khác nhận, bỏ qua.")
                continue
            print(f"\n=== Draft {ctx['draft_id']} ({ctx['difficulty']}, {ctx['skill']}): {ctx['question'][:90]}")
            try:
                result = review_draft(ctx, datasets, solver, k, config["REVIEW_SAMPLE_RETRIES"],
                                      config["REVIEW_ZERO_VALID_ACTION"],
                                      log=lambda i, s: print(f"  mẫu {i + 1}/{k}: {'OK' if s['ok'] else 'LỖI - ' + str(s.get('error'))[:110]}"))
                if not options.dry_run:
                    persist(config, result, datasets)
            except BaseException:
                if not options.dry_run:
                    release(config, ctx["draft_id"])
                raise
            counts[result["status"]] += 1
            print(f"  -> {result['status'].upper()} {', '.join(result['reasons']) or ''}")
            session["results"].append(summarize(result))
            arena.checkpoint(output, session)
        session["status"] = "completed"
    except InfraError as exc:
        session.update(status="aborted", error=str(exc))
        print(f"\nDừng phiên: {exc}\nDraft đang xử lý đã được trả về pending.", file=sys.stderr)
        arena.checkpoint(output, session)
        return 1
    except KeyboardInterrupt:
        session["status"] = "interrupted"
        arena.checkpoint(output, session)
        print("\nĐã dừng; draft đang xử lý được trả về pending.")
        return 1
    finally:
        after = {d.ref: catalog_version(config, d.kwargs["dbname"])[0] for d in datasets}
        session["protected_data_unchanged"] = all(after[d.ref] == d.version for d in datasets)
        session["counts"] = dict(counts)
        arena.checkpoint(output, session)
    print(f"\nKết quả: {dict(counts)} | dữ liệu Enterprise không đổi: {session['protected_data_unchanged']} | JSON: {output}")
    return 0


def cmd_calibrate(config, options):
    """Do Model B tren cau nguon da co dap an: tra loi 'consensus co dang tin khong' bang so lieu."""
    k = options.samples or config["REVIEW_SAMPLES"]
    ensure_model(config)
    datasets = build_datasets(config)[:1]
    ds = datasets[0]
    with arena.connect(config, "ARENA") as conn:
        world = conn.execute("SELECT * FROM core.worlds WHERE world_id=%s", (config["WORLD_ID"],)).fetchone()
        query = "SELECT * FROM core.source_questions WHERE world_id=%s" + (" AND difficulty=%s" if options.difficulty else "") + " ORDER BY question_id"
        sources = conn.execute(query, (config["WORLD_ID"], options.difficulty) if options.difficulty else (config["WORLD_ID"],)).fetchall()
    if options.limit:
        sources = sources[:options.limit]
    world_schema = {t["table"]: {c["name"]: c["postgres_type"] for c in t["columns"]} for t in world["schema_description"]["tables"]}
    print(f"Calibrate: {len(sources)} câu nguồn | Model B {config['REVIEW_MODEL_NAME']} | k={k}")
    if not confirm("Bắt đầu?", options.yes):
        return 0
    solver, report, tally = make_solver(config), [], Counter()
    for src in sources:
        tables = list(src["metadata"].get("tables_used") or [])
        ctx = {"draft_id": src["question_id"], "question": src["question_text"], "difficulty": src["difficulty"],
               "skill": src["primary_skill_group"], "tables_used": tables,
               "schema": {t: world_schema[t] for t in tables}, "fks": [], "checks": {}, "rules": [],
               "schema_text": "", "primary_keys": set(), "duplicate": {}}
        truth = ds.run(src["reference_sql"])
        mode = "ordered" if src["metadata"].get("ordering_required") else "unordered"
        samples = solve_samples(ctx, datasets, solver, k, config["REVIEW_SAMPLE_RETRIES"])
        valid = [s for s in samples if s["ok"]]
        correct = [s for s in valid if same_result(truth, s["results"][ds.ref], mode)]
        agree = len(valid) == k and all(same_result(valid[0]["results"][ds.ref], s["results"][ds.ref], mode) for s in valid)
        if not valid:
            outcome = "no_valid_solution"
        elif agree and len(correct) == k:
            outcome = "consensus_correct"
        elif agree:
            outcome = "consensus_WRONG"
        else:
            outcome = "no_consensus"
        tally[(src["difficulty"], outcome)] += 1
        tally[("all", outcome)] += 1
        report.append({"id": src["question_id"], "difficulty": src["difficulty"], "skill": src["primary_skill_group"],
                       "outcome": outcome, "first_sample_correct": bool(samples[0]["ok"] and same_result(
                           truth, samples[0]["results"][ds.ref], mode)),
                       "valid": len(valid), "correct": len(correct), "sqls": [s["sql"] for s in samples]})
        print(f"  {src['question_id']} [{src['difficulty']}/{src['primary_skill_group']}] {outcome} (đúng {len(correct)}/{k})")
    output = new_output("calibration")
    arena.checkpoint(output, {"review_version": REVIEW_VERSION, "model_b": config["REVIEW_MODEL_NAME"], "k": k,
                              "tally": {f"{a}/{b}": n for (a, b), n in tally.items()}, "items": report})
    print("\nTổng hợp (all):", {o: tally[("all", o)] for o in ("consensus_correct", "consensus_WRONG", "no_consensus", "no_valid_solution")})
    print("consensus_WRONG là chỉ số nguy hiểm nhất: các lần giải đồng ý với nhau nhưng sai so với đáp án nguồn.")
    print(f"JSON: {output}")
    return 0


def cmd_show(config, draft_id):
    with arena.connect(config, "ARENA") as conn:
        d = conn.execute("SELECT draft_id,status,difficulty,compare_mode,question FROM draft.question_drafts WHERE draft_id=%s", (draft_id,)).fetchone()
        if not d:
            raise ValueError(f"Không có draft {draft_id}.")
        logs = conn.execute("SELECT stage, passed, score, reasons, created_at FROM draft.review_logs WHERE draft_id=%s ORDER BY log_id", (draft_id,)).fetchall()
        runs = conn.execute("SELECT sample_index,is_selected,exec_status,row_count,error,model_sql FROM draft.self_solve_runs WHERE draft_id=%s ORDER BY sample_index", (draft_id,)).fetchall()
        tests = conn.execute("SELECT dataset_ref,dataset_version,compare_mode,row_count,result_hash FROM draft.test_cases WHERE draft_id=%s", (draft_id,)).fetchall()
    print(f"Draft {d['draft_id']} [{d['status']}] {d['difficulty']} mode={d['compare_mode']}\n{d['question']}\n")
    for r in logs:
        print(f"- {r['created_at']:%H:%M:%S} {r['stage']} passed={r['passed']} score={r['score']} reasons={r['reasons']}")
    for r in runs:
        print(f"\nMẫu {r['sample_index']} {'(CHỌN)' if r['is_selected'] else ''} {r['exec_status']} rows={r['row_count']} {r['error'] or ''}\n{r['model_sql']}")
    for t in tests:
        print(f"\nTest case: {dict(t)}")
    return 0


def cmd_reset_stuck(config, assume_yes):
    with arena.connect(config, "ARENA", readonly=False) as conn:
        stuck = conn.execute("SELECT draft_id FROM draft.question_drafts WHERE status='reviewing' ORDER BY 1").fetchall()
        if not stuck:
            print("Không có draft kẹt ở reviewing.")
            return 0
        ids = [r["draft_id"] for r in stuck]
        if not confirm(f"Trả {len(ids)} draft {ids} về pending? (chỉ làm khi không có phiên review nào đang chạy)", assume_yes):
            return 0
        conn.execute("UPDATE draft.question_drafts SET status='pending' WHERE status='reviewing'")
    print("Đã trả về pending.")
    return 0


def main(argv=None):
    args = argparse.ArgumentParser(description="SQLArena review pipeline (Model B)")
    args.add_argument("--check", action="store_true", help="Kiểm tra migration, Model B, role chỉ đọc; không review")
    args.add_argument("--calibrate", action="store_true", help="Đo Model B trên câu nguồn có đáp án (không ghi DB)")
    args.add_argument("--show", type=int, metavar="DRAFT_ID", help="Xem chi tiết kết quả review của một draft")
    args.add_argument("--reset-stuck", action="store_true", help="Trả draft kẹt ở reviewing về pending")
    args.add_argument("--dry-run", action="store_true", help="Review nhưng không ghi DB (chỉ ghi JSON)")
    args.add_argument("--limit", type=int, help="Số draft/câu nguồn tối đa")
    args.add_argument("--draft-id", type=int, help="Chỉ review một draft pending")
    args.add_argument("--difficulty", choices=("easy", "medium", "hard"), help="Lọc theo độ khó (calibrate)")
    args.add_argument("--samples", type=int, help="Ghi đè REVIEW_SAMPLES (k)")
    args.add_argument("--yes", action="store_true", help="Không hỏi xác nhận")
    options = args.parse_args(argv)
    try:
        config = load_review_config()
        if options.check:
            return cmd_check(config)
        if options.show:
            return cmd_show(config, options.show)
        if options.reset_stuck:
            return cmd_reset_stuck(config, options.yes)
        if options.calibrate:
            return cmd_calibrate(config, options)
        return cmd_review(config, options)
    except InfraError as exc:
        print(f"Lỗi hạ tầng: {exc}", file=sys.stderr)
        return 1
    except (ValueError, psycopg.Error, OSError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nĐã dừng.")
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
