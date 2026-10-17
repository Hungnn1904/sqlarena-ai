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
REVIEW_VERSION = "review_v1.3.1_contract_audit_repair"
STATUSES = ("approved", "needs_human", "rejected")
SQL_ERRORS = (ValueError, TypeError, KeyError, parser.ParseError)
ORDER_WORDS = re.compile(r"(sắp xếp|xếp theo|thứ tự|giảm dần|tăng dần|từ cao|từ thấp|xếp hạng|top\s*\d|"
                         r"order by|\basc\b|\bdesc\b)", re.I)
LEAK_PATTERNS = (re.compile(r"\bselect\b[\s\S]{0,400}\bfrom\b", re.I), re.compile(r"```"),
                 re.compile(r"\breference_sql\b", re.I))
AGGREGATES = {"count", "sum", "avg", "min", "max", "string_agg", "array_agg"}
DATE_WORDS = {"day", "week", "month", "quarter", "year", "hour", "minute", "second", "epoch", "dow", "doy", "isodow"}
GLOSSARY = (
    'Meaning of common Vietnamese phrases in questions:',
    '"loại X", "bỏ X", "trừ X", "không tính X", "không bao gồm X" = EXCLUDE X (so "loại NULL" means keep only non-NULL: col IS NOT NULL).',
    '"giữ nguyên", "giữ lại", "vẫn xuất hiện", "không loại" = keep those rows/values as they are: do NOT filter them out and do NOT replace NULL.',
    '"không duyệt cha", "không suy diễn", "không thêm" = do not add any logic the question did not ask for (no extra filter, join or fallback value).',
    '"khác nhau" = DISTINCT; "tăng dần" = ASC; "giảm dần" = DESC; "không giới hạn" = no filter on that attribute.',
    'If the question lists "Cột kết quả", return exactly those columns, in that order, with those names.',
)


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
    # Nhieu model: REVIEW_MODEL_NAME=modelA,modelB (cac mau giai chia lien tiep cho cac model, phai dong thuan chung).
    config["REVIEW_MODELS"] = [m.strip() for m in config["REVIEW_MODEL_NAME"].split(",") if m.strip()]
    if not config["REVIEW_MODELS"]:
        raise ValueError("REVIEW_MODEL_NAME khong hop le.")
    config["REVIEW_OLLAMA_HOST"] = config.get("REVIEW_OLLAMA_HOST") or config["OLLAMA_HOST"]
    number("REVIEW_SAMPLES", 3, int, 1)
    number("REVIEW_SAMPLE_RETRIES", 1, int, 0)
    number("REVIEW_TEMPERATURE", 0.3, float, 0)
    number("REVIEW_NUM_PREDICT", 900, int, 64)
    number("REVIEW_MAX_ROWS", 5000, int, 1)
    number("REVIEW_FEWSHOT", 2, int, 0)
    action = (config.get("REVIEW_ZERO_VALID_ACTION") or "needs_human").strip()
    if action not in ("rejected", "needs_human"):
        raise ValueError("REVIEW_ZERO_VALID_ACTION chi nhan rejected hoac needs_human.")
    config["REVIEW_ZERO_VALID_ACTION"] = action
    think = (config.get("REVIEW_THINK") or "").strip().lower()
    config["REVIEW_THINK"] = {"": None, "true": True, "false": False}.get(think, "bad")
    if config["REVIEW_THINK"] == "bad":
        raise ValueError("REVIEW_THINK chi nhan true, false hoac de trong.")
    if config["REVIEW_SAMPLES"] < len(config["REVIEW_MODELS"]):
        raise ValueError("REVIEW_SAMPLES phai >= so model trong REVIEW_MODEL_NAME.")
    config["REVIEW_VARIANT_DBS"] = [d.strip() for d in (config.get("REVIEW_VARIANT_DBS") or "").split(",") if d.strip()]
    audit_enabled = (config.get("REVIEW_SEMANTIC_AUDIT") or "true").strip().lower()
    if audit_enabled not in ("true", "false"):
        raise ValueError("REVIEW_SEMANTIC_AUDIT chi nhan true/false.")
    config["REVIEW_SEMANTIC_AUDIT"] = audit_enabled == "true"
    config["REVIEW_AUDIT_MODEL_NAME"] = (config.get("REVIEW_AUDIT_MODEL_NAME") or config["REVIEW_MODELS"][-1]).strip()
    number("REVIEW_AUDIT_NUM_PREDICT", 600, int, 128)
    number("REVIEW_REPAIR_ROUNDS", 2, int, 0)
    if config["REVIEW_REPAIR_ROUNDS"] > 2:
        raise ValueError("REVIEW_REPAIR_ROUNDS toi da la 2 de tranh lap khong can thiet.")
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
    if explicit_no_order_requested(question):
        return False
    return bool(ORDER_WORDS.search(unicodedata.normalize("NFC", question or "")))


def expected_columns_from_text(question):
    """Read the explicit output-column contract used by SQLArena's generated questions."""
    match = re.search(r"(?im)^\s*Cột kết quả theo thứ tự\s*:\s*([^\n]+)", question or "")
    if not match:
        return []
    raw = match.group(1).strip().rstrip(".")
    return [part.strip().strip('`"\' ') for part in raw.split(",") if part.strip()]


def normalize_output_columns(value):
    if not isinstance(value, (list, tuple)):
        return []
    result = []
    for item in value:
        if isinstance(item, dict):
            item = item.get("name") or item.get("column") or item.get("alias")
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def explicit_no_order_requested(question):
    """Detect explicit negation before loose ORDER BY keyword matching.

    Example: ENT-020 says "Sắp xếp: Một dòng nên không có yêu cầu thứ tự".
    The word "Sắp xếp" alone must not turn that into a required ORDER BY.
    """
    text = unicodedata.normalize("NFC", question or "").casefold()
    patterns = (
        r"không\s+có\s+yêu\s+cầu\s+thứ\s+tự",
        r"không\s+yêu\s+cầu\s+(?:thứ\s+tự|sắp\s+xếp)",
        r"không\s+cần\s+sắp\s+xếp",
        r"không\s+đặt\s+thứ\s+tự",
        r"không\s+sắp\s+xếp(?:\s+theo)?",
        r"one\s+row[^\n]{0,60}no\s+ordering\s+required",
    )
    # Negation is authoritative only when it occurs in the dedicated ordering line or
    # in a short sentence explicitly about ordering (avoid negating unrelated prose).
    for line in text.splitlines():
        if re.search(r"sắp\s+xếp|order\s+by|thứ\s+tự|ordering", line, re.I):
            if any(re.search(pattern, line, re.I) for pattern in patterns):
                return True
    return False


def parse_expected_order_full(text):
    """Parse `key tăng, other giảm NULLS LAST` into (key, direction, nulls)."""
    if not isinstance(text, str) or not text.strip():
        return []
    specs = []
    pattern = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_$.]*)\s+(tăng(?:\s+dần)?|giảm(?:\s+dần)?|asc|desc)"
        r"(?:\s+NULLS\s+(FIRST|LAST))?$", re.I)
    for piece in [part.strip().strip(".") for part in text.split(",") if part.strip()]:
        found = pattern.match(piece)
        if not found:
            return []
        key, direction, nulls = found.groups()
        specs.append((key.split(".")[-1].lower(),
                      "desc" if direction.lower().startswith(("giảm", "desc")) else "asc",
                      (nulls or "default").lower()))
    return specs


def parse_expected_order(text):
    """Backwards-compatible pair form used by older callers/tests."""
    return [(key, direction) for key, direction, _nulls in parse_expected_order_full(text)]


def expected_order_specs_full(ctx):
    question = ctx.get("question") or ""
    if explicit_no_order_requested(question):
        return []
    # Parse the actual question line first. It is authoritative over model-generated metadata.
    # The ordering contract can follow introductory prose on the same line, e.g.
    # "Liệt kê các status khác nhau. Sắp xếp: status tăng.". Do not require
    # the header to start a new line; explicit_no_order_requested() handles negation first.
    match = re.search(r"(?i)\bSắp\s+xếp(?:\s+theo)?\s*:\s*([^\n]+)", question)
    from_question = parse_expected_order_full(match.group(1)) if match else []
    if from_question:
        return from_question
    metadata_order = ctx.get("expected_order_by")
    if isinstance(metadata_order, list):
        result = []
        for item in metadata_order:
            if not isinstance(item, dict) or not item.get("column"):
                return []
            direction = str(item.get("direction") or "asc").lower()
            nulls = str(item.get("nulls") or "default").lower()
            if direction not in ("asc", "desc") or nulls not in ("default", "first", "last"):
                return []
            result.append((str(item["column"]).split(".")[-1].lower(), direction, nulls))
        if result:
            return result
    if isinstance(metadata_order, str) and metadata_order.strip():
        parsed = parse_expected_order_full(metadata_order)
        if parsed:
            return parsed
    return []


def expected_order_specs(ctx):
    """Backwards-compatible pair form used by tests and older code."""
    return [(key, direction) for key, direction, _nulls in expected_order_specs_full(ctx)]


def ordering_required(ctx):
    question = ctx.get("question") or ""
    # The explicit natural-language negation overrides stale/over-broad metadata.
    if explicit_no_order_requested(question):
        return False
    if expected_order_specs_full({**ctx, "ordering_required": None}):
        return True
    metadata_value = ctx.get("ordering_required")
    if isinstance(metadata_value, bool):
        return metadata_value
    if isinstance(metadata_value, str):
        normalized = metadata_value.strip().lower()
        if normalized in {"false", "0", "no", "none", ""}:
            return False
        if normalized in {"true", "1", "yes"}:
            return True
    return bool(re.search(r"(?i)\b(?:order\s+by|tăng dần|giảm dần|từ cao xuống thấp|từ thấp lên cao)\b", question))

def actual_order_specs_full(tree):
    query = tree.get("SelectStmt", {})
    specs = []
    for item in query.get("sortClause") or []:
        sort = item.get("SortBy", {})
        node = sort.get("node", {})
        fields = [f["String"]["sval"] for f in node.get("ColumnRef", {}).get("fields", []) if "String" in f]
        key = fields[-1].lower() if fields else None
        raw_dir = sort.get("sortby_dir", 0)
        if isinstance(raw_dir, str):
            direction = "desc" if "DESC" in raw_dir.upper() else "asc"
        else:
            direction = {2: "desc"}.get(raw_dir, "asc")  # PostgreSQL default is ASC.
        raw_nulls = sort.get("sortby_nulls", 0)
        if isinstance(raw_nulls, str):
            nulls = "last" if "LAST" in raw_nulls.upper() else ("first" if "FIRST" in raw_nulls.upper() else "default")
        else:
            nulls = {1: "first", 2: "last"}.get(raw_nulls, "default")
        specs.append((key, direction, nulls))
    return specs


def actual_order_specs(tree):
    """Backwards-compatible pair form."""
    return [(key, direction) for key, direction, _nulls in actual_order_specs_full(tree)]


def decide_mode(tree, question):
    return "ordered" if order_keys(tree) and ordering_requested(question) else "unordered"


def tiebreaker_ok(tree, primary_keys):
    """A column suffix such as *_id is not proof of uniqueness; check result keys instead."""
    keys = [k.lower() for k in order_keys(tree) if k]
    return bool(keys) and any(k in {str(pk).lower() for pk in primary_keys} for k in keys)


def ordering_deterministic(tree, output_columns, results, primary_keys):
    """Fail closed unless the complete ORDER BY key tuple is exposed and unique on every dataset.

    This intentionally prefers manual review over guessing that an *_id field is unique at the
    query's row grain (a JOIN can duplicate parent IDs).
    """
    keys = [k.lower() for k in order_keys(tree) if k]
    names = [str(c).lower() for c in output_columns]
    if not keys or len(keys) != len(order_keys(tree)) or any(k not in names for k in keys):
        return False
    indices = [names.index(k) for k in keys]
    for res in results:
        key_tuples = [tuple(json.dumps(row[i], ensure_ascii=False, sort_keys=True) for i in indices)
                      for row in res["rows"]]
        if len(set(key_tuples)) != len(key_tuples):
            return False
    return True


def shadowed_subquery_aliases(tree):
    """Return relation aliases reused across nested SELECT scopes (often breaks correlation).

    Reusing an alias can be legal SQL, but it makes a correlated predicate easy to accidentally
    bind to the inner relation. Such cases go to human review rather than being auto-approved.
    """
    def direct_aliases(query):
        aliases = set()
        def visit_from(node):
            if not isinstance(node, dict):
                return
            if "RangeVar" in node:
                rel = node["RangeVar"]
                alias = (rel.get("alias") or {}).get("aliasname") or rel.get("relname")
                if alias:
                    aliases.add(str(alias).lower())
            elif "JoinExpr" in node:
                join = node["JoinExpr"]
                visit_from(join.get("larg"))
                visit_from(join.get("rarg"))
            elif "RangeSubselect" in node:
                alias = (node["RangeSubselect"].get("alias") or {}).get("aliasname")
                if alias:
                    aliases.add(str(alias).lower())
        for source in query.get("fromClause") or []:
            visit_from(source)
        return aliases

    def child_queries(value, current_query, out):
        if isinstance(value, dict):
            if "SelectStmt" in value and value is not current_query:
                out.append(value["SelectStmt"])
                return
            for item in value.values():
                child_queries(item, current_query, out)
        elif isinstance(value, list):
            for item in value:
                child_queries(item, current_query, out)

    findings = set()
    def descend(query, ancestors):
        aliases = direct_aliases(query)
        collisions = aliases & ancestors
        if collisions:
            # Only flag collisions when the nested SELECT actually qualifies a column with them.
            local_refs = set()
            def refs(value):
                if isinstance(value, dict):
                    if "SelectStmt" in value and value is not query:
                        return
                    if "ColumnRef" in value:
                        fields = value["ColumnRef"].get("fields") or []
                        names = [f["String"]["sval"] for f in fields if "String" in f]
                        if len(names) >= 2:
                            local_refs.add(names[-2].lower())
                    for item in value.values():
                        refs(item)
                elif isinstance(value, list):
                    for item in value:
                        refs(item)
            refs(query)
            findings.update(collisions & local_refs)
        nested = []
        child_queries(query, query, nested)
        for child in nested:
            descend(child, ancestors | aliases)

    root = tree.get("SelectStmt", {})
    descend(root, set())
    return sorted(findings)


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


def unstated_string_literals(tree, question, checks):
    """Hang chuoi trong SQL khong xuat hien trong de hoac trong CHECK cua bang (vd COALESCE(x, 'None'))."""
    haystack = unicodedata.normalize("NFC", (question or "") + " " + " ".join(checks)).casefold()
    found = []
    for tag, node in walk(tree):
        if tag != "A_Const" or "sval" not in node:
            continue
        literal = node["sval"].get("sval", "")
        core = literal.strip("%_ ").casefold()
        if (not core or core in DATE_WORDS or re.fullmatch(r"[ymdhisw0-9\-/:. ]+", core, re.I)
                or core in haystack):
            continue
        found.append(literal)
    return sorted(set(found))


def skill_difficulty_issues(skill, difficulty, f):
    issues = []
    if skill == "S1" and (f["joins"] or f["aggregate"] or f["ctes"] or f["sublinks"] or f["window"] or f["selects"] > 1):
        issues.append("skill_s1_has_forbidden_features")
    if skill == "S2" and not (f["joins"] or f["range_vars"] >= 2):
        issues.append("skill_s2_no_join")
    if skill == "S3" and not f["aggregate"]:
        issues.append("skill_s3_no_aggregate")
    if skill == "S4" and not (f["sublinks"] or f["range_subselects"]):
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


# --------------------------------------------------------------------------- normalized query contract

def _question_lines(question):
    return [line.strip() for line in unicodedata.normalize("NFC", question or "").splitlines() if line.strip()]


def build_query_contract(ctx):
    """Create a review-time structured contract without changing the database schema.

    The question text is authoritative. Metadata is surfaced as helpful structure, not trusted
    as proof: when it conflicts with the question, semantic audit must flag it for a human.
    """
    lines = _question_lines(ctx.get("question", ""))
    question = ctx.get("question", "")
    signature = ctx.get("logic_signature") if isinstance(ctx.get("logic_signature"), dict) else {}
    supplied = ctx.get("metadata_query_contract") if isinstance(ctx.get("metadata_query_contract"), dict) else {}
    ordering = ordering_required({**ctx, "question": question})
    order_specs = expected_order_specs_full({**ctx, "question": question}) if ordering else []
    clauses = {
        "filter_pattern": signature.get("filter_pattern") or "",
        "aggregation_pattern": signature.get("aggregation_pattern") or "",
        "analysis_goal": signature.get("analysis_goal") or "",
    }
    edge_lines = [line for line in lines if re.match(r"(?i)^quy tắc biên\s*:", line)]
    time_lines = [line for line in lines if re.match(r"(?i)^thời gian\s*:", line)]
    unit_lines = [line for line in lines if re.search(r"(?i)làm tròn|chữ số|đơn vị|triệu đồng|VND|phần trăm|%", line)]
    return {
        "contract_version": "1.0",
        "source_of_truth": "question_text",
        "question_lines": lines,
        "required_output_columns": ctx.get("expected_output_columns") or expected_columns_from_text(question),
        "output_grain": ctx.get("output_grain") or signature.get("output_grain") or signature.get("grain") or "",
        "central_table": (signature.get("central_table") or supplied.get("central_table") or ""),
        "table_roles": ctx.get("table_roles") or {},
        "join_relations": ctx.get("join_relations") or [],
        "analysis_goal": clauses["analysis_goal"],
        "filter_pattern": clauses["filter_pattern"],
        "aggregation_pattern": clauses["aggregation_pattern"],
        "edge_cases": ctx.get("edge_cases") or edge_lines,
        "date_time_requirements": time_lines,
        "rounding_and_unit_requirements": unit_lines,
        "ordering": {
            "required": bool(ordering),
            "keys": [{"column": key, "direction": direction, "nulls": nulls}
                     for key, direction, nulls in order_specs],
            "source_line": next((line for line in lines if re.match(r"(?i)^sắp\s+xếp\s*:", line)), ""),
        },
        "additional_contract_metadata": supplied,
        "metadata_consistency_warning": (
            "Metadata is model-authored and may be incomplete; if it conflicts with the question, do not auto-approve."
        ),
    }


def order_specs_match(actual, expected):
    """Require the requested sort as a prefix; allow extra deterministic tie-breakers."""
    if len(actual) < len(expected):
        return False
    for (ak, ad, an), (ek, ed, en) in zip(actual[:len(expected)], expected):
        if ak != ek or ad != ed:
            return False
        if en != "default":
            effective_actual_nulls = an
            if an == "default":
                # PostgreSQL defaults: ASC NULLS LAST, DESC NULLS FIRST.
                effective_actual_nulls = "last" if ad == "asc" else "first"
            if effective_actual_nulls != en:
                return False
    return True


def _split_top_level_commas(text):
    parts, start, depth = [], 0, 0
    single = double = False
    i = 0
    while i < len(text):
        ch = text[i]
        if single:
            if ch == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                single = False
        elif double:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    i += 2
                    continue
                double = False
        elif ch == "'":
            single = True
        elif ch == '"':
            double = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
        i += 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _split_top_level_keyword(text, keyword):
    """Split on a SQL keyword only outside parentheses and quoted literals."""
    parts, start, depth = [], 0, 0
    single = double = False
    upper = (text or "").upper()
    target = keyword.upper()
    i = 0
    while i < len(text or ""):
        ch = text[i]
        if single:
            if ch == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                single = False
        elif double:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    i += 2
                    continue
                double = False
        elif ch == "'":
            single = True
        elif ch == '"':
            double = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and upper.startswith(target, i):
            before = upper[i - 1] if i else " "
            after_i = i + len(target)
            after = upper[after_i] if after_i < len(upper) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                parts.append(text[start:i].strip())
                start = after_i
                i = after_i
                continue
        i += 1
    parts.append((text or "")[start:].strip())
    return [part for part in parts if part]


def _top_level_select_expressions(sql):
    body = _top_level_clause_body(sql, "SELECT", ("FROM",))
    expressions = {}
    for expression in _split_top_level_commas(body):
        alias = re.search(r"(?is)\s+AS\s+([a-z_][a-z0-9_$]*)\s*$", expression)
        if alias:
            expressions[alias.group(1).lower()] = expression[:alias.start()].strip()
        else:
            bare = re.search(r"(?is)\s+([a-z_][a-z0-9_$]*)\s*$", expression)
            if bare and ")" in expression:
                expressions[bare.group(1).lower()] = expression[:bare.start()].strip()
            else:
                ref = re.search(r"(?is)(?:[a-z_][a-z0-9_$]*\.)?([a-z_][a-z0-9_$]*)\s*$", expression)
                if ref:
                    expressions[ref.group(1).lower()] = expression
    return expressions


def _outer_function_args(expression, function_name):
    """Return top-level arguments only when the expression is exactly FUNCTION(...)."""
    match = re.match(rf"(?is)^\s*{re.escape(function_name)}\s*\(", expression or "")
    if not match:
        return []
    open_paren = expression.find("(", match.start())
    depth, single, double = 0, False, False
    close_at = None
    i = open_paren
    while i < len(expression):
        ch = expression[i]
        if single:
            if ch == "'":
                if i + 1 < len(expression) and expression[i + 1] == "'":
                    i += 2
                    continue
                single = False
        elif double:
            if ch == '"':
                if i + 1 < len(expression) and expression[i + 1] == '"':
                    i += 2
                    continue
                double = False
        elif ch == "'":
            single = True
        elif ch == '"':
            double = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                close_at = i
                break
        i += 1
    if close_at is None or expression[close_at + 1:].strip():
        return []
    return _split_top_level_commas(expression[open_paren + 1:close_at])


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
    parents = row.get("parent_ids") or []
    question = row["question"]
    meta_columns = normalize_output_columns(meta.get("output_columns"))
    expected_columns = meta_columns or expected_columns_from_text(question)
    ordering_meta = meta.get("ordering_required") if "ordering_required" in meta else None
    order_by = meta.get("order_by") or ""
    logic_signature = meta.get("logic_signature") or vr.get("logic_signature") or {}
    output_grain = meta.get("output_grain") or logic_signature.get("output_grain") or logic_signature.get("grain") or ""
    edge_cases = meta.get("edge_cases") or logic_signature.get("edge_cases") or ""
    table_roles = meta.get("table_roles") if isinstance(meta.get("table_roles"), dict) else {}
    join_relations = meta.get("join_relations") if isinstance(meta.get("join_relations"), list) else []
    ctx = {"draft_id": row["draft_id"], "question": question, "difficulty": row["difficulty"],
            "parent_ids": [p for p in parents if isinstance(p, str)], "examples": [],
            "skill": meta.get("primary_skill_group") or (skills[0] if skills else None),
            "tables_used": tables_used, "schema": schema, "fks": fks, "checks": checks, "rules": rules,
            "primary_keys": {k for t in tables_used if t in defs for k in defs[t].get("primary_key", [])},
            "all_checks": [c for t in tables_used if t in defs for c in defs[t].get("checks", [])],
            "expected_output_columns": expected_columns, "ordering_required": ordering_meta,
            "expected_order_by": order_by, "output_grain": output_grain, "edge_cases": edge_cases,
            "logic_signature": logic_signature, "metadata_query_contract": meta.get("query_contract") or {},
            "table_roles": table_roles, "join_relations": join_relations,
            "schema_text": row.get("schema_text") or "", "duplicate": vr.get("duplicate") or {}}
    ctx["query_contract"] = build_query_contract(ctx)
    return ctx


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
    if ctx.get("question"):
        contract = ctx.get("query_contract") or build_query_contract(ctx)
        parts.append("NORMALIZED QUESTION CONTRACT (derived from the question and available metadata; the wording of the question remains authoritative):\n" +
                     json.dumps(contract, ensure_ascii=False, indent=2))
    parts.append("SQL RULES:\n" + "\n".join("- " + r for r in (
        "Exactly one PostgreSQL SELECT statement (WITH ... SELECT allowed). No DDL/DML.",
        "Use only the allowed tables and only columns that exist in them. Give every output column an alias.",
        "Follow the question literally: output columns and their order, filters, rounding, grouping.",
        "Do NOT add any WHERE/HAVING/JOIN condition that the question does not state.",
        "Do NOT use COALESCE/CASE to invent placeholder text; keep NULL as NULL unless the question gives the replacement.",
        "Add ORDER BY only if the question asks for an ordering; if it does, end with a unique tie-breaker key.",
        "No now(), CURRENT_DATE or CURRENT_TIMESTAMP; use the dates stated in the question.",
        "Do not hardcode ids or values that the question does not state.",
        "Allowed functions only: " + ", ".join(sorted(SAFE_FUNCTIONS)) + ".")))
    parts.append("\n".join(GLOSSARY))
    if ctx.get("examples"):
        shown = "\n\n".join(f"Example {i}\nQuestion: {e['question']}\nSQL: {e['sql']}" for i, e in enumerate(ctx["examples"], 1))
        parts.append("SOLVED EXAMPLES (same dataset; they only show the conventions. They may use other tables: you may use "
                     "ONLY the allowed tables above. Never copy them blindly):\n" + shown)
    if feedback:
        parts.append("YOUR PREVIOUS ATTEMPT WAS REJECTED:\n" + feedback + "\nFix it and answer again.")
    parts.append('Return only JSON: {"sql": "<one SELECT statement>"}')
    return "\n\n".join(parts)


def solver_format():
    return {"type": "object", "properties": {"sql": {"type": "string", "minLength": 1}},
            "required": ["sql"], "additionalProperties": False}


def call_solver(config, prompt, seed, temperature, model=None):
    options = {"num_ctx": config["OLLAMA_CONTEXT_SIZE"], "num_predict": config["REVIEW_NUM_PREDICT"],
               "temperature": temperature, "seed": seed}
    body = {"model": model or config["REVIEW_MODELS"][0], "prompt": prompt, "stream": False,
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


def auditor_format():
    return {"type": "object", "properties": {
        "verdict": {"type": "string", "enum": ["pass", "needs_human"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "checks": {"type": "array", "items": {"type": "object", "properties": {
            "requirement": {"type": "string"},
            "status": {"type": "string", "enum": ["pass", "fail", "uncertain"]},
            "finding": {"type": "string"}},
            "required": ["requirement", "status", "finding"], "additionalProperties": False}},
        }, "required": ["verdict", "issues", "checks"], "additionalProperties": False}


def semantic_audit_prompt(ctx, sql):
    """Build a separate audit prompt; it does not receive the model's sample consensus or answer SQL."""
    contract = {
        "query_contract": ctx.get("query_contract") or build_query_contract(ctx),
        "allowed_tables_and_columns": ctx.get("schema", {}),
        "foreign_keys": ctx.get("fks", []),
        "business_rules": ctx.get("rules", []),
        "check_constraints": ctx.get("all_checks", []),
        "candidate_sql": sql,
    }
    return ("You are a separate PostgreSQL SQL SEMANTIC AUDITOR. Do not write or repair SQL. "
            "Judge whether candidate_sql implements the Vietnamese question, not whether it parses or executes. "
            "Treat question_lines in query_contract as the authoritative requirements. Treat the other metadata as a "
            "navigation aid only; if it conflicts with question_lines, report needs_human. For every explicit business "
            "requirement, locate the exact SQL expression that implements it. Pay special attention to a conditional "
            "threshold such as 'at least 5 delivered orders': HAVING COUNT(*) >= 5 is NOT equivalent to counting only "
            "delivered orders. A query may run and still be wrong. Read the SQL literally and audit each requirement. "
            "Pay special attention to: every WHERE/HAVING predicate and threshold; aggregate filters versus total-row counts; NULL handling; joins that can "
            "multiply rows when the requested output grain is one row per entity; EXISTS/NOT EXISTS semantics; "
            "correlated subqueries and alias scope; required output columns/aliases/order; rounding and units; "
            "date/time semantics; and ORDER BY keys/directions/tie-breakers. Do not assume that successful execution "
            "or agreement with another sample means correctness. Return AT LEAST FIVE distinct checks, one for each "
            "of these groups: (1) output columns and aliases, (2) WHERE/HAVING/aggregate thresholds, (3) joins, row "
            "grain, EXISTS and correlated subqueries, (4) NULL/date/rounding/unit edge cases, and (5) ordering and "
            "tie-breakers. Each check's requirement field MUST use exactly one of these five labels: "
            "'output columns and aliases'; 'WHERE/HAVING/aggregate thresholds'; "
            "'joins, row grain, EXISTS and correlated subqueries'; 'NULL/date/rounding/unit edge cases'; "
            "'ordering and tie-breakers'. Do not combine groups or repeat a label in place of another group. "
            "If a group is not applicable, mark it pass only with a concise explanation. If a requirement "
            "is ambiguous, not demonstrably satisfied, or a plausible semantic bug exists, choose needs_human. Use pass "
            "only when all explicit requirements are supported by the SQL. `issues` must be empty for pass. Keep "
            "findings concise and cite the relevant SQL clause.\n\nAUDIT INPUT JSON:\n" + json.dumps(contract, ensure_ascii=False, default=str))


def audit_requirement_group(requirement):
    """Map one auditor check label to exactly one required audit group.

    Do not concatenate all labels and search for keywords: a single vague/duplicated label must
    not satisfy several independent checks.
    """
    label = unicodedata.normalize("NFC", str(requirement or "")).casefold()
    label = re.sub(r"^\s*\(?[1-5]\)?[.)\-:]\s*", "", label)
    label = re.sub(r"[^a-z0-9à-ỹ]+", " ", label).strip()
    aliases = {
        "output_columns": {
            "output columns and aliases", "output columns aliases", "required output columns and aliases",
            "output columns", "columns and aliases",
        },
        "filters_aggregates": {
            "where having aggregate thresholds", "where having aggregation thresholds",
            "filters and having aggregate thresholds", "filters and aggregate thresholds",
            "where predicates having and aggregate thresholds",
        },
        "joins_grain_subqueries": {
            "joins row grain exists and correlated subqueries",
            "joins and row grain exists and correlated subqueries",
            "joins row grain and subqueries", "joins and row grain", "joins grain exists and subqueries",
        },
        "edge_cases": {
            "null date rounding unit edge cases", "null date rounding units edge cases",
            "null date rounding and unit edge cases", "null date rounding and units",
        },
        "ordering": {
            "ordering and tie breakers", "ordering tie breakers", "order by and tie breakers",
            "ordering and tiebreakers",
        },
    }
    for group, labels in aliases.items():
        if label in labels:
            return group
    return None


def call_semantic_auditor(config, ctx, sql):
    if not config.get("REVIEW_SEMANTIC_AUDIT", True):
        return {"verdict": "needs_human", "issues": ["Semantic audit is disabled; fail-closed."], "checks": []}
    model = config["REVIEW_AUDIT_MODEL_NAME"]
    body = {"model": model, "prompt": semantic_audit_prompt(ctx, sql), "stream": False,
            "format": auditor_format(),
            "options": {"num_ctx": config["OLLAMA_CONTEXT_SIZE"],
                        "num_predict": config["REVIEW_AUDIT_NUM_PREDICT"], "temperature": 0, "seed": 0}}
    if config.get("REVIEW_THINK") is not None:
        body["think"] = config["REVIEW_THINK"]
    try:
        response = arena.ollama_request({**config, "OLLAMA_HOST": config["REVIEW_OLLAMA_HOST"]}, "/api/generate", body)
    except ValueError as exc:
        raise InfraError(f"Semantic auditor khong goi duoc model {model}: {exc}") from exc
    if response.get("done_reason") == "length":
        return {"verdict": "needs_human", "issues": ["semantic_audit_output_truncated"], "checks": []}
    try:
        result = json.loads(response["response"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return {"verdict": "needs_human", "issues": ["semantic_audit_invalid_json"], "checks": []}
    if (not isinstance(result, dict) or result.get("verdict") not in ("pass", "needs_human")
            or not isinstance(result.get("issues"), list) or not isinstance(result.get("checks"), list)):
        return {"verdict": "needs_human", "issues": ["semantic_audit_invalid_schema"], "checks": []}
    # Fail closed: any issue, failed check, uncertain check, or non-pass verdict blocks auto-approval.
    uncertain = [c for c in result["checks"]
                 if (not isinstance(c, dict) or c.get("status") != "pass"
                     or not isinstance(c.get("requirement"), str) or not c.get("requirement", "").strip()
                     or not isinstance(c.get("finding"), str) or not c.get("finding", "").strip())]
    issues = [str(x)[:400] for x in result["issues"] if str(x).strip()]
    if len(result["checks"]) < 5:
        uncertain.append({"finding": "semantic_audit_insufficient_checks"})
    required_groups = {
        "output_columns": "audit_group_output_columns_missing",
        "filters_aggregates": "audit_group_filters_aggregates_missing",
        "joins_grain_subqueries": "audit_group_joins_grain_subqueries_missing",
        "edge_cases": "audit_group_edge_cases_missing",
        "ordering": "audit_group_ordering_missing",
    }
    covered_groups = {
        audit_requirement_group(check.get("requirement"))
        for check in result["checks"] if isinstance(check, dict)
    }
    for group_name, issue in required_groups.items():
        if group_name not in covered_groups:
            uncertain.append({"finding": issue})
    if result["verdict"] != "pass" or issues or uncertain:
        result["verdict"] = "needs_human"
        if uncertain:
            issues.extend(str(c.get("finding", "Auditor khong xac minh duoc mot yeu cau"))[:400]
                          for c in uncertain if isinstance(c, dict))
        result["issues"] = list(dict.fromkeys(issues)) or ["semantic_audit_needs_human"]
    return result


def make_auditor(config):
    return lambda ctx, sql: call_semantic_auditor(config, ctx, sql)


def model_for(index, k, models):
    return models[index * len(models) // k] if models else None


def solve_samples(ctx, datasets, solver, k, retries, log=lambda *_: None, models=None, feedback=None, seed_offset=0):
    """Moi mau: toi da 1+retries lan goi; chi nhan mau qua guard va chay duoc tren MOI dataset."""
    samples = []
    for index in range(k):
        sample_feedback, attempts = feedback, []
        model = model_for(index, k, models)
        sample = {"index": index, "ok": False, "sql": None, "attempts": attempts, "model": model}
        for attempt in range(retries + 1):
            record = {"attempt": attempt}
            attempts.append(record)
            try:
                sql, metrics = solver(build_solver_prompt(ctx, sample_feedback), seed_offset + index * 100 + attempt,
                                      0.0 if index == 0 or (models and model_for(index - 1, k, models) != model) else None, model)
            except SolverOutputError as exc:
                record["error"] = sample_feedback = f"format: {exc}"
                continue
            record["sql"], sample["sql"] = sql, sql
            try:
                tree, info = guard_sql(sql, ctx["schema"])
            except SQL_ERRORS as exc:
                record["error"] = sample_feedback = f"guard: {exc}"
                continue
            results = {}
            for ds in datasets:
                results[ds.ref] = ds.run(sql)
            bad = next(((r, ds) for ds, r in zip(datasets, results.values())
                        if r["status"] != "ok"), None)
            if bad:
                record["error"] = sample_feedback = f"execution on {bad[1].ref}: {bad[0].get('error')}"
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



def _top_level_clause_body(sql, clause, stop_words=()):
    """Get a top-level SQL clause body while ignoring parentheses and quoted strings/identifiers."""
    depth = 0
    single_quote = False
    double_quote = False
    dollar_tag = None
    start = None
    i = 0
    stop_words = {w.upper() for w in stop_words}
    while i < len(sql):
        if dollar_tag:
            if sql.startswith(dollar_tag, i):
                i += len(dollar_tag)
                dollar_tag = None
            else:
                i += 1
            continue
        ch = sql[i]
        if single_quote:
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 2
                    continue
                single_quote = False
            i += 1
            continue
        if double_quote:
            if ch == '"':
                if i + 1 < len(sql) and sql[i + 1] == '"':
                    i += 2
                    continue
                double_quote = False
            i += 1
            continue
        if ch == "'":
            single_quote = True
            i += 1
            continue
        if ch == '"':
            double_quote = True
            i += 1
            continue
        if ch == '$':
            match = re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])
            if match:
                dollar_tag = match.group(0)
                i += len(dollar_tag)
                continue
        if ch == '(':
            depth += 1
            i += 1
            continue
        if ch == ')':
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0 and (ch.isalpha() or ch == '_'):
            match = re.match(r"[A-Za-z_][A-Za-z_0-9$]*", sql[i:])
            if match:
                word = match.group(0).upper()
                end = i + len(match.group(0))
                if start is None and word == clause.upper():
                    start = end
                elif start is not None and word in stop_words:
                    return sql[start:i].strip()
                i = end
                continue
        i += 1
    return sql[start:].strip() if start is not None else ""


def _direct_from_relations(tree):
    """Return (relation name, alias) pairs from the outer FROM/JOIN only.

    Deliberately stops at subqueries so an EXISTS against a child table is not mistaken for
    a row-multiplying outer join.
    """
    query = tree.get("SelectStmt", tree if isinstance(tree, dict) else {})
    found = []

    def visit(node):
        if not isinstance(node, dict):
            return
        if "RangeVar" in node:
            rel = node["RangeVar"]
            name = str(rel.get("relname") or "").lower()
            alias = str((rel.get("alias") or {}).get("aliasname") or rel.get("relname") or "").lower()
            if name:
                found.append((name, alias))
            return
        if "JoinExpr" in node:
            join = node["JoinExpr"]
            visit(join.get("larg"))
            visit(join.get("rarg"))
            return
        # RangeSubselect and RangeFunction are not base table relations for this test.

    for node in query.get("fromClause") or []:
        visit(node)
    return found


def one_to_many_join_grain_issues(ctx, tree, info):
    """Flag a risky direct many-side join when output grain is a single parent entity.

    Prefer explicit central-table metadata. If absent (as with existing Model A metadata), infer
    the parent conservatively from (a) an entity-grain contract, (b) selected source aliases, and
    (c) the existing child->parent foreign-key list. DISTINCT or parent-grain GROUP BY is accepted.
    This is a review guard, not a proof that every one-to-many join is wrong.
    """
    query = tree.get("SelectStmt", tree if isinstance(tree, dict) else {})
    if not (query.get("fromClause") and info.get("features", {}).get("joins", 0)):
        return []
    if query.get("distinctClause"):
        return []

    signature = ctx.get("logic_signature") if isinstance(ctx.get("logic_signature"), dict) else {}
    contract = ctx.get("query_contract") if isinstance(ctx.get("query_contract"), dict) else {}
    grain = str(ctx.get("output_grain") or contract.get("output_grain") or signature.get("output_grain") or signature.get("grain") or "").strip().casefold()
    if not grain:
        return []
    # A singular entity grain can be described in several ways by Model A.
    singular_grain = bool(re.search(
        r"^(?:một\s+.+|mỗi\s+.+|one\s+row\s+per\s+.+|one\s+.+|per\s+.+|danh\s+sách\s+(?:các\s+)?[\wÀ-ỹ]+)",
        grain, re.I))
    # Do not treat multidimensional/time-bucket grains as one-parent output.
    compound_or_time_grain = bool(re.search(
        r"\b(?:và|and|per month|per week|per quarter|per year|theo tháng|theo tuần|theo quý|theo năm)\b",
        grain, re.I))
    if not singular_grain or compound_or_time_grain:
        return []

    relations = _direct_from_relations(tree)
    tables = {table for table, _alias in relations}
    if not relations:
        return []
    aliases = {alias: table for table, alias in relations}

    # Gather aliases represented in the outer SELECT list. Nested subqueries must not affect the
    # inferred output grain.
    target_list = query.get("targetList") or []
    projected_aliases = set()

    def collect_refs(node):
        if isinstance(node, dict):
            if "SelectStmt" in node:
                return
            if "ColumnRef" in node:
                fields = [f["String"]["sval"].lower() for f in node["ColumnRef"].get("fields", []) if "String" in f]
                if len(fields) >= 2:
                    projected_aliases.add(fields[-2])
            for value in node.values():
                collect_refs(value)
        elif isinstance(node, list):
            for value in node:
                collect_refs(value)

    collect_refs(target_list)
    projected_tables = {aliases[a] for a in projected_aliases if a in aliases}

    central = str(signature.get("central_table") or contract.get("central_table") or "").lower()
    # Existing candidate_metadata does not require central_table. Infer it only when every
    # explicitly qualified output field comes from one joined table that is the FK parent.
    fk_pattern = re.compile(r"^\s*([A-Za-z_][\w]*)\s*\([^)]*\)\s*->\s*([A-Za-z_][\w]*)\s*\(", re.I)
    fk_edges = []
    for fk in ctx.get("fks", []) or []:
        match = fk_pattern.match(str(fk))
        if match:
            child, parent = match.group(1).lower(), match.group(2).lower()
            if child in tables and parent in tables:
                fk_edges.append((child, parent))
    if not central and len(projected_tables) == 1:
        projected_table = next(iter(projected_tables))
        if any(parent == projected_table for _child, parent in fk_edges):
            central = projected_table
    if not central or central not in tables:
        return []

    child_tables = {child for child, parent in fk_edges if parent == central}
    if not child_tables:
        return []

    # If selected fields explicitly come from a child relation, the result may legitimately be
    # finer than one row per parent; do not flag it as a parent-grain duplication risk.
    if any(aliases.get(alias) in child_tables for alias in projected_aliases):
        return []

    # GROUP BY only establishes parent grain when it does not group by child-side fields.
    def aliases_in(node):
        found = set()
        def visit(value):
            if isinstance(value, dict):
                if "SelectStmt" in value:
                    return
                if "ColumnRef" in value:
                    fields = [f["String"]["sval"].lower() for f in value["ColumnRef"].get("fields", []) if "String" in f]
                    if len(fields) >= 2:
                        found.add(fields[-2])
                for sub in value.values():
                    visit(sub)
            elif isinstance(value, list):
                for sub in value:
                    visit(sub)
        visit(node)
        return found

    group_aliases = aliases_in(query.get("groupClause") or [])
    if query.get("groupClause") and not any(aliases.get(alias) in child_tables for alias in group_aliases):
        return []

    return ["one_to_many_join_may_duplicate_output_grain"]


def explicit_semantic_contract_issues(ctx, sql):
    """Block high-impact mismatches that are explicit in SQLArena's question format.

    These are deterministic guardrails, not an attempt to prove arbitrary SQL semantics.
    Unknown patterns are left to the auditor/human instead of being guessed as correct.
    """
    question = unicodedata.normalize("NFC", ctx.get("question") or "")
    q_lower = question.casefold()
    sql_text = sql or ""
    issues = []

    # Explicit "(loại NULL)" contract tied to a named column, e.g.
    # "Theo employee_id được gán trên đơn (loại NULL)".
    null_matches = re.findall(
        r"\b([A-Za-z_][A-Za-z_0-9]*)\b(?=[^.\n]{0,140}\(\s*loại\s+NULL\s*\))",
        question, re.I)
    if null_matches:
        # In prose such as "Theo employee_id được gán ...", the last ASCII identifier
        # before the annotation is the intended column, not the sentence opener "Theo".
        col = re.escape(null_matches[-1])
        where_body = _top_level_clause_body(sql_text, "WHERE", ("GROUP", "HAVING", "ORDER", "LIMIT", "FETCH"))
        if not re.search(rf"(?i)(?:\b[A-Za-z_][A-Za-z_0-9]*\s*\.\s*)?\b{col}\s+IS\s+NOT\s+NULL\b", where_body):
            issues.append("explicit_null_exclusion_missing")

    # A conditional threshold must apply the threshold to a delivered-only aggregate,
    # not to all rows in the group. Split HAVING's top-level AND predicates so the
    # delivered condition and numeric threshold must belong to the same predicate.
    threshold = re.search(r"ít nhất\s+(\d+)\s+đơn\s+(?:đã\s+)?delivered\b", q_lower, re.I)
    if threshold:
        n = threshold.group(1)
        having_body = _top_level_clause_body(sql_text, "HAVING", ("ORDER", "LIMIT", "FETCH"))
        predicates = _split_top_level_keyword(having_body, "AND")
        matching = False
        for predicate in predicates:
            delivered = bool(re.search(r"(?i)\bdelivered\b", predicate))
            number = bool(re.search(rf"(?:>=\s*{re.escape(n)}\b|\b{re.escape(n)}\s*<=)", predicate))
            aggregate = bool(re.search(r"(?i)\b(?:COUNT|SUM)\s*\(", predicate))
            if delivered and number and aggregate:
                matching = True
                break
        if not matching:
            issues.append("conditional_having_threshold_missing_delivered_filter")

    # The question says the month value is the first day of the month; SQLArena stores
    # that contract as a DATE, not a raw PostgreSQL timestamp from date_trunc().
    if re.search(r"(?i)\bmonth\s+là\s+ngày\s+đầu\s+tháng\b", q_lower):
        expr = _top_level_select_expressions(sql_text).get("month", "")
        is_date = bool(re.search(r"(?is)::\s*date\b", expr)
                        or re.search(r"(?is)\bCAST\s*\(.*?\s+AS\s+DATE\s*\)", expr))
        if not is_date:
            issues.append("month_output_must_be_date")

    # If output says these hour measures are rounded, verify each aliased expression
    # has ROUND(expression, requested_precision) at the outermost expression level.
    rounding = re.search(r"(?i)làm\s+tròn[^.\n]*?\b(\d+)\s+chữ\s+số\b", question)
    expected = {str(c).lower() for c in (ctx.get("expected_output_columns") or expected_columns_from_text(question))}
    if rounding and {"min_hours", "max_hours", "avg_hours"}.issubset(expected):
        precision = rounding.group(1)
        expressions = _top_level_select_expressions(sql_text)
        for fn, alias in (("MIN", "min_hours"), ("MAX", "max_hours"), ("AVG", "avg_hours")):
            outer_args = _outer_function_args(expressions.get(alias, ""), "ROUND")
            if len(outer_args) != 2 or not re.fullmatch(rf"\s*{re.escape(precision)}\s*", outer_args[1]):
                issues.append(f"required_rounding_missing_{alias}")

    return list(dict.fromkeys(issues))

def _review_draft_once(ctx, datasets, solver, k, retries, zero_valid_action="needs_human", log=lambda *_: None,
                       models=None, auditor=None, feedback=None, seed_offset=0):
    """Tra ve dict ket qua; khong ghi DB. Fail-closed: thieu bang chung -> khong approved."""
    out = {"draft_id": ctx["draft_id"], "status": None, "reasons": [], "mode": None, "reference_sql": None,
           "samples": [], "testcases": [], "stages": {}, "notes": []}
    pre = pre_checks(ctx)
    out["stages"]["pre"] = {"passed": not pre, "reasons": pre}
    if pre:
        out.update(status="rejected", reasons=pre)
        return out

    samples = solve_samples(ctx, datasets, solver, k, retries, log, models,
                            feedback=feedback, seed_offset=seed_offset)
    out["samples"] = samples
    valid = [s for s in samples if s["ok"]]
    out["stages"]["solve"] = {"passed": len(valid) == k, "valid": len(valid), "k": k}
    if not valid:
        # Failure to solve is not proof that the question itself is invalid.
        out.update(status=zero_valid_action, reasons=["no_valid_solution"])
        return out
    if len(valid) < k:
        out.update(status="needs_human", reasons=["insufficient_valid_solutions"])
        return out

    # If the prompt explicitly requires ordering, every sample must implement it; accidental natural
    # row order on the current dataset is not evidence that ORDER BY is optional.
    if ordering_required(ctx):
        missing_order = [s["index"] for s in valid if not order_keys(s["tree"])]
        if missing_order:
            out["stages"]["ordering_contract"] = {"passed": False, "missing_samples": missing_order}
            out.update(status="needs_human", reasons=["required_order_by_missing"])
            return out
        required_specs = expected_order_specs_full(ctx)
        if required_specs:
            wrong_order = [s["index"] for s in valid if not order_specs_match(actual_order_specs_full(s["tree"]), required_specs)]
            if wrong_order:
                out["stages"]["ordering_contract"] = {"passed": False, "required": required_specs,
                                                         "mismatched_samples": wrong_order}
                out.update(status="needs_human", reasons=["order_by_contract_mismatch"])
                return out

    # De yeu cau sap xep -> uu tien loi giai co ORDER BY (neu khong, tham chieu se mat thu tu cua de).
    pool = [s for s in valid if order_keys(s["tree"])] if ordering_required(ctx) else []
    selected = min(pool or valid, key=lambda s: (s["info"]["features"]["ast_nodes"], len(s["sql"]), s["index"]))
    mode = "ordered" if order_keys(selected["tree"]) and ordering_required(ctx) else "unordered"
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
    expected_cols = ctx.get("expected_output_columns") or expected_columns_from_text(ctx.get("question", ""))
    if expected_cols and selected["info"]["output_columns"] != expected_cols:
        reasons_human.append("output_columns_mismatch")
        out["notes"].append({"expected_output_columns": expected_cols,
                              "actual_output_columns": selected["info"]["output_columns"]})
    if mode == "ordered" and not ordering_deterministic(selected["tree"], selected["info"]["output_columns"],
                                                         [selected["results"][ds.ref] for ds in datasets], ctx["primary_keys"]):
        reasons_human.append("order_tiebreaker_missing")
    shadowed = shadowed_subquery_aliases(selected["tree"])
    if shadowed:
        reasons_human.append("subquery_alias_shadowing")
        out["notes"].append({"shadowed_subquery_aliases": shadowed})
    hard = hardcoded_id_literals(selected["tree"], ctx["question"])
    if hard:
        reasons_human.append("hardcoded_id_literal")
        out["notes"].append({"hardcoded": hard})
    if set(selected["info"]["tables"]) != set(ctx["tables_used"]):
        reasons_human.append("tables_mismatch")
        out["notes"].append({"declared": sorted(ctx["tables_used"]), "used": selected["info"]["tables"]})
    invented = unstated_string_literals(selected["tree"], ctx["question"], ctx.get("all_checks", []))
    if invented:
        reasons_human.append("unstated_string_literal")
        out["notes"].append({"unstated_literals": invented})
    if ctx["duplicate"].get("suspected_duplicate"):
        reasons_human.append("suspected_duplicate")
    if len(datasets) == 1:
        out["notes"].append("Chi co 1 dataset: chua bat duoc dap an dung rieng cho du lieu hien co (hardcode gia tri).")
    contract_issues = explicit_semantic_contract_issues(ctx, selected["sql"])
    grain_issues = one_to_many_join_grain_issues(ctx, selected["tree"], selected["info"])
    contract_issues.extend(grain_issues)
    contract_issues = list(dict.fromkeys(contract_issues))
    out["stages"]["semantic_contract"] = {"passed": not contract_issues, "issues": contract_issues}
    reasons_human.extend(contract_issues)
    out["stages"]["post"] = {"passed": not (reasons_reject or reasons_human),
                             "reasons": sorted(set(reasons_reject + reasons_human)), "features": features}
    if reasons_reject:
        out.update(status="rejected", reasons=sorted(set(reasons_reject + reasons_human)))
        return out
    if reasons_human:
        out.update(status="needs_human", reasons=sorted(set(reasons_human)))
        return out

    if auditor is None:
        out["stages"]["semantic_audit"] = {"passed": False, "verdict": "needs_human",
                                            "issues": ["semantic_auditor_not_configured"], "checks": []}
        out.update(status="needs_human", reasons=["semantic_audit_unavailable"])
        return out
    try:
        audit = auditor(ctx, selected["sql"])
    except InfraError:
        raise
    except Exception as exc:
        audit = {"verdict": "needs_human", "issues": [f"semantic_audit_exception: {type(exc).__name__}"], "checks": []}
    audit_passed = (isinstance(audit, dict) and audit.get("verdict") == "pass" and not audit.get("issues")
                    and isinstance(audit.get("checks"), list) and len(audit.get("checks", [])) >= 5
                    and all(isinstance(c, dict) and c.get("status") == "pass"
                            and isinstance(c.get("requirement"), str) and c.get("requirement", "").strip()
                            and isinstance(c.get("finding"), str) and c.get("finding", "").strip()
                            for c in audit.get("checks", [])))
    out["stages"]["semantic_audit"] = {"passed": audit_passed,
                                        "verdict": audit.get("verdict") if isinstance(audit, dict) else "needs_human",
                                        "issues": audit.get("issues", []) if isinstance(audit, dict) else ["invalid_audit_result"],
                                        "checks": audit.get("checks", []) if isinstance(audit, dict) else []}
    if not audit_passed:
        audit_issues = out["stages"]["semantic_audit"]["issues"] or ["semantic_audit_needs_human"]
        out["notes"].append({"semantic_audit": audit_issues})
        out.update(status="needs_human", reasons=["semantic_audit_flagged"])
        return out

    for ds in datasets:
        res = selected["results"][ds.ref]
        out["testcases"].append({"dataset_ref": ds.ref, "dataset_version": ds.version, "compare_mode": mode,
                                 "reference_sql": selected["sql"], "expected_columns": res["columns"],
                                 "expected_rows": res["rows"], "row_count": res["row_count"],
                                 "result_hash": result_hash(res["rows"], mode)})
    out.update(status="approved", reasons=[])
    return out


# --------------------------------------------------------------------------- bounded repair loop

_REPAIRABLE_REASONS = {
    "no_valid_solution", "insufficient_valid_solutions", "consensus_disagreement", "order_disagreement",
    "required_order_by_missing", "order_by_contract_mismatch", "order_tiebreaker_missing",
    "output_columns_mismatch", "subquery_alias_shadowing",
    "explicit_null_exclusion_missing", "conditional_having_threshold_missing_delivered_filter",
    "one_to_many_join_may_duplicate_output_grain", "month_output_must_be_date", "required_rounding_missing_min_hours", "required_rounding_missing_max_hours",
    "required_rounding_missing_avg_hours", "semantic_audit_flagged", "skill_s1_has_forbidden_features",
    "skill_s2_no_join", "skill_s3_no_aggregate", "skill_s4_no_subquery", "skill_s5_no_cte_or_window",
    "skill_s6_no_recursion_or_layers", "difficulty_easy_exceeded", "tables_mismatch",
    "hardcoded_id_literal", "unstated_string_literal",
}


def _repair_feedback(result):
    """Create bounded, actionable feedback; never include the source reference answer."""
    issues = list(result.get("reasons") or [])
    stages = result.get("stages") or {}
    for stage_name in ("ordering_contract", "semantic_contract", "post", "semantic_audit", "consensus", "solve"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        for key in ("reasons", "issues", "mismatches"):
            value = stage.get(key)
            if value:
                issues.append(f"{stage_name}.{key}: {json.dumps(value, ensure_ascii=False, default=str)[:900]}")
    sql = result.get("reference_sql")
    if not sql:
        sql = next((sample.get("sql") for sample in result.get("samples", []) if sample.get("sql")), None)
    text = [
        "This is a repair attempt after deterministic checks or semantic audit found issues.",
        "Rewrite the SQL from the question and contract, rather than preserving the old logic.",
        "Fix every listed issue. Do not relax the requirement, invent conditions, or return an explanation.",
        "The question text is authoritative. If a condition is unclear, produce the most literal SQL solution.",
        "Issues to fix:",
        *[f"- {issue}" for issue in list(dict.fromkeys(issues))[:20]],
    ]
    if sql:
        text.extend(["Previous candidate SQL (may be wrong):", sql[:3500]])
    return "\n".join(text)[:6500]


def review_draft(ctx, datasets, solver, k, retries, zero_valid_action="needs_human", log=lambda *_: None,
                 models=None, auditor=None, repair_rounds=0):
    """Run the review and, if configured, retry a failed candidate at most N times.

    Every repair round regenerates k candidates and re-runs *all* guards, executions,
    consensus, contracts and semantic audit. A successful audit never overrides a hard-rule failure.
    """
    maximum = max(0, min(int(repair_rounds or 0), 2))
    result = _review_draft_once(ctx, datasets, solver, k, retries, zero_valid_action, log, models, auditor)
    history = []
    for repair_index in range(maximum):
        reasons = set(result.get("reasons") or [])
        # Only repeat candidate-generation failures; structural question errors should remain human/rejected.
        retryable_status = result.get("status") == "needs_human" or (
            result.get("status") == "rejected" and reasons == {"no_valid_solution"})
        if not retryable_status or not (reasons & _REPAIRABLE_REASONS):
            break
        feedback = _repair_feedback(result)
        history.append({"round": repair_index + 1, "prior_status": result.get("status"),
                        "prior_reasons": sorted(reasons), "feedback": feedback[:1800]})
        repaired = _review_draft_once(ctx, datasets, solver, k, retries, zero_valid_action, log, models, auditor,
                                      feedback=feedback, seed_offset=(repair_index + 1) * 10000)
        result = repaired
        if result.get("status") == "approved":
            history[-1]["outcome"] = "approved_after_repair"
            break
        history[-1]["outcome"] = result.get("status")
    if history:
        result.setdefault("stages", {})["repair"] = {"attempted": len(history), "limit": maximum, "history": history,
                                                      "approved_after_repair": result.get("status") == "approved"}
        result.setdefault("notes", []).append({"repair_rounds": len(history),
                                               "approved_after_repair": result.get("status") == "approved"})
    else:
        result.setdefault("stages", {})["repair"] = {"attempted": 0, "limit": maximum, "history": [],
                                                      "approved_after_repair": False}
    return result


# --------------------------------------------------------------------------- persistence

def sample_rows(result, model):
    rows = []
    for s in result["samples"]:
        res = (s.get("results") or {})
        first = next(iter(res.values()), None) or {}
        rows.append({"sample_index": s["index"], "model": s.get("model") or model, "sql": s["sql"], "is_selected": bool(s.get("is_selected")),
                     "exec_status": "ok" if s["ok"] else "failed", "row_count": first.get("row_count"),
                     "hash": result_hash(first["rows"], result["mode"] or "unordered") if first else None,
                     "error": s.get("error"), "mismatch": s.get("mismatch"),
                     "matched": [ref for ref, r in res.items() if not (s.get("mismatch") or {}).get(ref)]})
    return rows


def persist(config, result, datasets):
    model = config["REVIEW_MODELS"][0]
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
                          r["error"], r["model"]))
        stages = result["stages"]

        def log(stage, passed, reasons, raw, score=None):
            conn.execute("INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, raw_output) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s)", (draft_id, stage, passed, score, Jsonb(reasons), ",".join(config["REVIEW_MODELS"]),
                                                          Jsonb({"review_version": REVIEW_VERSION, **raw})))
        log("code_check", stages["pre"]["passed"], stages["pre"]["reasons"], {"phase": "pre"})
        if "solve" in stages:
            k = stages["solve"]["k"]
            log("self_solve", stages["solve"]["passed"], [] if stages["solve"]["passed"] else ["not_all_samples_valid"],
                {"samples": [{k2: v for k2, v in r.items() if k2 != "sql"} for r in rows], "datasets": dataset_info,
                 "models": config["REVIEW_MODELS"]},
                score=round(100 * stages["solve"]["valid"] / k, 2))
        if "post" in stages:
            log("code_check", stages["post"]["passed"], stages["post"]["reasons"],
                {"phase": "post", "features": stages["post"]["features"], "notes": result["notes"]})
        if "semantic_audit" in stages:
            audit_stage = stages["semantic_audit"]
            log("checklist", audit_stage["passed"], audit_stage.get("issues", []),
                {"phase": "semantic_audit", "verdict": audit_stage.get("verdict"),
                 "issues": audit_stage.get("issues", []), "checks": audit_stage.get("checks", [])})
        repair_stage = stages.get("repair") or {}
        if repair_stage.get("attempted"):
            log("code_check", bool(repair_stage.get("approved_after_repair")),
                [] if repair_stage.get("approved_after_repair") else ["repair_did_not_reach_approval"],
                {"phase": "repair", **repair_stage})
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

def load_example_pool(conn, world_id):
    rows = conn.execute("SELECT question_id, difficulty, primary_skill_group, question_text, reference_sql, metadata "
                        "FROM core.source_questions WHERE world_id=%s ORDER BY question_id", (world_id,)).fetchall()
    return [r for r in rows if r["reference_sql"] and r["question_text"]]


def pick_examples(pool, ctx, n, exclude=()):
    """Vi du da giai cung dataset: uu tien cung skill, trung bang, cung do kho. Loai cau cha/cau dang do."""
    if n <= 0:
        return []
    used, ranked = set(ctx["tables_used"]), []
    for r in pool:
        if r["question_id"] in exclude or len(r["question_text"]) > 900 or len(r["reference_sql"]) > 700:
            continue
        overlap = len(used & set((r["metadata"] or {}).get("tables_used") or []))
        ranked.append((-(r["primary_skill_group"] == ctx["skill"]), -overlap, -(r["difficulty"] == ctx["difficulty"]), r["question_id"], r))
    ranked.sort(key=lambda t: t[:4])
    return [{"id": r["question_id"], "question": r["question_text"].strip(), "sql": r["reference_sql"].strip()}
            for *_, r in ranked[:n]]


def make_solver(config):
    def solver(prompt, seed, temperature, model=None):
        return call_solver(config, prompt, seed, config["REVIEW_TEMPERATURE"] if temperature is None else temperature, model)
    return solver


def ensure_model(config):
    tags = arena.ollama_request({**config, "OLLAMA_HOST": config["REVIEW_OLLAMA_HOST"]}, "/api/tags")
    names = {m["name"] for m in tags.get("models", [])}
    wanted_models = list(config["REVIEW_MODELS"])
    if config.get("REVIEW_SEMANTIC_AUDIT", True):
        wanted_models.append(config["REVIEW_AUDIT_MODEL_NAME"])
    for wanted in dict.fromkeys(wanted_models):
        if wanted not in names and wanted + ":latest" not in names:
            kind = "Semantic auditor" if wanted == config.get("REVIEW_AUDIT_MODEL_NAME") else "Model B"
            raise ValueError(f"{kind} {wanted} chua cai. Tu chay: ollama pull {wanted}")


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
    print(f"Model B: {', '.join(config['REVIEW_MODELS'])} @ {config['REVIEW_OLLAMA_HOST']} (đã cài)")
    print(f"Semantic auditor: {config['REVIEW_AUDIT_MODEL_NAME']} | enabled={config['REVIEW_SEMANTIC_AUDIT']}")
    if config["MODEL_NAME"] in config["REVIEW_MODELS"]:
        print("Cảnh báo: Model B trùng Model A; sai lệch của hai model sẽ giống nhau, đồng thuận kém tin cậy.")
    if len(config["REVIEW_MODELS"]) == 1:
        print("Gợi ý: có thể khai 2 model (REVIEW_MODEL_NAME=modelX,modelY) để hai model khác họ phải đồng thuận.")
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
        pool = load_example_pool(conn, config["WORLD_ID"]) if config["REVIEW_FEWSHOT"] else []
    if not rows:
        print("Không có draft pending để kiểm duyệt.")
        return 0
    ensure_model(config)
    datasets = build_datasets(config)
    print(f"{len(rows)} draft pending | Model B {', '.join(config['REVIEW_MODELS'])} | auditor {config['REVIEW_AUDIT_MODEL_NAME']} | k={k} | few-shot={config['REVIEW_FEWSHOT']} | "
          f"dataset: {', '.join(d.ref for d in datasets)}" + (" | DRY-RUN" if options.dry_run else ""))
    if not confirm("Bắt đầu kiểm duyệt?", options.yes):
        print("Đã hủy.")
        return 0
    output = new_output("review")
    session = {"review_version": REVIEW_VERSION, "started_at": datetime.now().astimezone().isoformat(),
               "model_b": config["REVIEW_MODELS"], "semantic_audit_model": config["REVIEW_AUDIT_MODEL_NAME"],
               "k": k, "fewshot": config["REVIEW_FEWSHOT"], "dry_run": options.dry_run,
               "datasets": [{"ref": d.ref, "version": d.version} for d in datasets], "results": [], "status": "running"}
    solver, auditor, counts = make_solver(config), make_auditor(config), Counter()
    try:
        for row in rows:
            ctx = draft_context(row)
            ctx["examples"] = pick_examples(pool, ctx, config["REVIEW_FEWSHOT"], set(ctx["parent_ids"]))
            if not options.dry_run and not claim(config, ctx["draft_id"]):
                print(f"Draft {ctx['draft_id']}: đã bị tiến trình khác nhận, bỏ qua.")
                continue
            print(f"\n=== Draft {ctx['draft_id']} ({ctx['difficulty']}, {ctx['skill']}): {ctx['question'][:90]}")
            try:
                result = review_draft(ctx, datasets, solver, k, config["REVIEW_SAMPLE_RETRIES"],
                                      config["REVIEW_ZERO_VALID_ACTION"],
                                      log=lambda i, s: print(f"  mẫu {i + 1}/{k}: {'OK' if s['ok'] else 'LỖI - ' + str(s.get('error'))[:110]}"),
                                      models=config["REVIEW_MODELS"], auditor=auditor,
                                      repair_rounds=config["REVIEW_REPAIR_ROUNDS"])
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


def source_to_row(src, world):
    """Cau nguon -> dong giong draft that, de calibrate chay dung duong di cua pipeline that."""
    used = set(src["metadata"].get("tables_used") or [])
    tables = [{"table": t["table"], "columns": [{"name": c["name"], "type": c["postgres_type"], "nullable": c["nullable"]}
                                                for c in t["columns"]], "primary_key": t["primary_key"],
               "checks": [c["definition"] for c in t["constraints"] if c["kind"] == "c"]}
              for t in world["schema_description"]["tables"] if t["table"] in used]
    schema_context = {"tables": tables, "fk_relations": [f for f in world["fk_relations"]
                                                         if {f["table_name"], f["referenced_table"]} <= used],
                      "business_rules": []}
    return {"draft_id": src["question_id"], "question": src["question_text"], "difficulty": src["difficulty"],
            "skills": [src["primary_skill_group"]], "parent_ids": [src["question_id"]],
            "schema_context": schema_context, "schema_text": arena.render_schema_text(schema_context, sorted(used)),
            "validation_report": {"candidate_metadata": {"primary_skill_group": src["primary_skill_group"],
                                                         "tables_used": sorted(used),
                                                         "output_columns": src["metadata"].get("output_columns", []),
                                                         "ordering_required": src["metadata"].get("ordering_required"),
                                                         "order_by": src["metadata"].get("order_by", ""),
                                                         "output_grain": src["metadata"].get("output_grain", ""),
                                                         "logic_signature": src["metadata"].get("logic_signature", {}),
                                                         "edge_cases": src["metadata"].get("edge_cases", ""),
                                                         "query_contract": src["metadata"].get("query_contract", {})},
                                 "duplicate": {}}}


def cmd_calibrate(config, options):
    """Chay DUNG pipeline review tren cau nguon co dap an. Chi so nguy hiem nhat: approved_WRONG."""
    k = options.samples or config["REVIEW_SAMPLES"]
    ensure_model(config)
    datasets = build_datasets(config)
    with arena.connect(config, "ARENA") as conn:
        world = conn.execute("SELECT * FROM core.worlds WHERE world_id=%s", (config["WORLD_ID"],)).fetchone()
        query = "SELECT * FROM core.source_questions WHERE world_id=%s" + (" AND difficulty=%s" if options.difficulty else "") + " ORDER BY question_id"
        sources = conn.execute(query, (config["WORLD_ID"], options.difficulty) if options.difficulty else (config["WORLD_ID"],)).fetchall()
        pool = load_example_pool(conn, config["WORLD_ID"]) if config["REVIEW_FEWSHOT"] else []
    sources = sources[options.skip or 0:]
    if options.limit:
        sources = sources[:options.limit]
    evaluated = {src["question_id"] for src in sources}
    print(f"Calibrate: {len(sources)} câu nguồn | Model B {', '.join(config['REVIEW_MODELS'])} | semantic auditor {config['REVIEW_AUDIT_MODEL_NAME']} | k={k} | few-shot={config['REVIEW_FEWSHOT']}"
          f" | ví dụ lấy từ {len([r for r in pool if r['question_id'] not in evaluated])} câu KHÔNG nằm trong tập đo")
    if not confirm("Bắt đầu?", options.yes):
        return 0
    solver, auditor, report, tally = make_solver(config), make_auditor(config), [], Counter()
    for src in sources:
        ctx = draft_context(source_to_row(src, world))
        ctx["examples"] = pick_examples(pool, ctx, config["REVIEW_FEWSHOT"], evaluated)
        truths = {ds.ref: ds.run(src["reference_sql"]) for ds in datasets}
        mode = "ordered" if ordering_required(ctx) else "unordered"
        out = review_draft(ctx, datasets, solver, k, config["REVIEW_SAMPLE_RETRIES"], config["REVIEW_ZERO_VALID_ACTION"],
                           models=config["REVIEW_MODELS"], auditor=auditor,
                           repair_rounds=config["REVIEW_REPAIR_ROUNDS"])
        valid = [s for s in out["samples"] if s["ok"]]
        right = [s for s in valid if all(same_result(truths[ds.ref], s["results"][ds.ref], mode) for ds in datasets)]
        if out["status"] == "approved":
            ok_all = all(same_result(truths[t["dataset_ref"]], {"status": "ok", "columns": t["expected_columns"],
                                                               "rows": t["expected_rows"], "row_count": t["row_count"]}, mode)
                         for t in out["testcases"])
            outcome = "approved_correct" if ok_all else "approved_WRONG"
        else:
            outcome = out["status"] + ("_but_all_samples_correct" if valid and len(right) == len(valid) else "")
        tally[(src["difficulty"], outcome)] += 1
        tally[("all", outcome)] += 1
        report.append({"id": src["question_id"], "difficulty": src["difficulty"], "skill": src["primary_skill_group"],
                       "outcome": outcome, "reasons": out["reasons"], "valid": len(valid), "correct": len(right),
                       "mode_differs": bool(out["mode"] and out["mode"] != mode), "notes": out["notes"],
                       "semantic_contract": out["stages"].get("semantic_contract"),
                       "semantic_audit": out["stages"].get("semantic_audit"),
                       "repair": out["stages"].get("repair"),
                       "sqls": [s["sql"] for s in out["samples"]], "reference_sql": src["reference_sql"]})
        print(f"  {src['question_id']} [{src['difficulty']}/{src['primary_skill_group']}] {outcome} "
              f"(đúng {len(right)}/{k}) {', '.join(out['reasons'])}")
        audit_stage = out["stages"].get("semantic_audit")
        if audit_stage and not audit_stage.get("passed"):
            print("     SEMANTIC AUDIT: " + "; ".join(map(str, audit_stage.get("issues", [])))[:350])
        if outcome == "approved_WRONG":
            print("     B:  " + " ".join((out["reference_sql"] or "").split())[:300])
            print("     ĐÁP ÁN: " + " ".join(src["reference_sql"].split())[:300])
    output = new_output("calibration")
    names = ("approved_correct", "approved_WRONG", "needs_human", "needs_human_but_all_samples_correct",
             "rejected", "rejected_but_all_samples_correct")
    arena.checkpoint(output, {"review_version": REVIEW_VERSION, "model_b": config["REVIEW_MODELS"],
                              "semantic_audit_model": config["REVIEW_AUDIT_MODEL_NAME"], "k": k,
                              "fewshot": config["REVIEW_FEWSHOT"], "tally": {f"{a}/{b}": n for (a, b), n in tally.items()},
                              "items": report})
    print("\nTổng hợp:", {o: tally[("all", o)] for o in names if tally[("all", o)]})
    print("approved_WRONG: pipeline duyệt nhầm (nguy hiểm nhất). *_but_all_samples_correct: đề đúng nhưng bị chặn (quá thận trọng).")
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
    args.add_argument("--skip", type=int, help="Bỏ qua N câu nguồn đầu (calibrate), vd --skip 15 để đo từ ENT-016")
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
