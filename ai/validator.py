"""Conservative Model A checks, not semantic approval or Model B."""

import hashlib
import json
import re
import time
import unicodedata
from collections import Counter

import psycopg
from pglast import parser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from context_policy import check_group_usage, check_question_dependencies


SAFE_FUNCTIONS = set("""
count sum avg min max bool_and bool_or every array_agg string_agg
row_number rank dense_rank percent_rank cume_dist ntile lag lead
first_value last_value nth_value abs round ceil ceiling floor trunc mod
power sqrt sign greatest least coalesce nullif lower upper length char_length
substring substr trim btrim ltrim rtrim replace concat concat_ws split_part
date_part date_trunc extract age to_char to_date make_date generate_series
percentile_cont percentile_disc mode stddev stddev_pop stddev_samp variance
var_pop var_samp json_agg jsonb_agg json_build_object jsonb_build_object
array_length cardinality unnest
""".split())
SAFE_TYPES = set("""
int2 int4 int8 smallint integer bigint numeric decimal float4 float8 real
double precision text varchar bpchar char boolean bool date timestamp
timestamptz time timetz interval json jsonb uuid int integer[] text[]
""".split()) | {"double precision"}
SAFE_OPERATORS = set("= <> != < > <= >= + - * / % ^ || ~~ !~~ ~~* !~~* @> <@ &&".split())
SAFE_NODES = set("""
SelectStmt ResTarget RangeVar Alias JoinExpr RangeSubselect CommonTableExpr
WithClause ColumnRef A_Star A_Const Integer String Float Boolean BitString
FuncCall A_Expr BoolExpr NullTest BooleanTest CaseExpr CaseWhen CaseTestExpr
CoalesceExpr MinMaxExpr TypeCast TypeName SubLink WindowDef SortBy List
GroupingSet GroupingFunc RowExpr A_ArrayExpr ArrayExpr NamedArgExpr
""".split())


# --- Generation contract -------------------------------------------------
# Single source of truth shared by the prompt (main.build_prompt) and by
# metadata_check below, so the model is told exactly what will be checked.
COMMON_SQL_RULES = (
    "Exactly one PostgreSQL SELECT statement (no DDL/DML). No SELECT *; give every output column an alias.",
    "Use ONLY the ALLOWED TABLES above and ONLY columns that exist in world_schema.tables.",
    "The business goal must be answerable with the allowed tables alone; if it needs another table, pick another goal.",
    "No current-time functions or keywords (now(), CURRENT_DATE, CURRENT_TIMESTAMP) and no 'last N months/days'. "
    "If a date is needed, use a fixed date literal and state it in the question.",
    "Output aliases cannot be used in WHERE or HAVING; repeat the expression instead.",
)
SKILL_CONTRACTS = {
    "S1": "Direct filter/select/sort on ONE table (WHERE/ORDER BY/DISTINCT, scalar expressions). "
          "FORBIDDEN: JOIN, COUNT/SUM/AVG/MIN/MAX, GROUP BY, HAVING, WITH/CTE, subquery, window functions.",
    "S2": "The solution must JOIN at least two allowed tables along a foreign key (INNER/LEFT/SELF JOIN).",
    "S3": "The solution must GROUP BY with an aggregate function (COUNT/SUM/AVG/MIN/MAX); HAVING is welcome.",
    "S4": "The solution must contain a subquery: IN / EXISTS / NOT EXISTS / scalar subquery / derived table "
          "(or an equivalent anti-join).",
    "S5": "The solution must use a CTE (WITH) or a window function (OVER) for a real analytical purpose.",
    "S6": "The solution must use a recursive CTE, or multi-step history/running-total logic with several "
          "chained CTE/window layers.",
}
DIFFICULTY_CONTRACTS = {
    "easy": "EASY: no CTE, no window function, no subquery.",
    "medium": "MEDIUM: 2-3 reasoning steps (group+filter groups, anti-join/EXISTS, simple window/CTE, "
              "combined business conditions).",
    "hard": "HARD: several transformation layers or history/event reasoning with edge cases and tie-breakers.",
}


def skill_contract(skill, difficulty):
    lines = [SKILL_CONTRACTS.get(skill, ""), DIFFICULTY_CONTRACTS.get(difficulty, "")]
    return [line for line in lines if line]


# error substring -> actionable instruction for the next attempt
_HINTS = (
    ("S1 khong phai", "S1 = plain filter/sort on ONE table. Rewrite WITHOUT JOIN, aggregate, GROUP BY/HAVING, "
                      "CTE, subquery or window; make the goal a simple row filter."),
    ("S2 thieu", "S2 needs a real JOIN between two allowed tables."),
    ("S3 thieu", "S3 needs GROUP BY plus an aggregate function."),
    ("S4 thieu", "S4 needs a subquery / EXISTS / NOT EXISTS (or anti-join)."),
    ("S5 thieu", "S5 needs a CTE or window function (OVER)."),
    ("S6 can", "S6 needs a recursive CTE or multi-layer history logic."),
    ("Easy khong nen", "Difficulty easy: remove CTE, window functions and subqueries."),
    ("Bang ngoai context", "You used a table outside the allowed tables. Change the business goal so it can be "
                           "answered ONLY with the allowed tables."),
    ("Cot khong ton tai", "You referenced a column that does not exist (or an output alias inside WHERE/HAVING). "
                          "Use only column names listed in world_schema.tables."),
    ("Ham khong nam trong allowlist", "That SQL function is not allowed (now() is NOT allowed). Use basic "
                                      "aggregates/string/date_part functions, or a fixed date literal."),
    ("SQLValueFunction", "CURRENT_DATE/CURRENT_TIMESTAMP are not allowed. Use a fixed date literal."),
    ("Khong duoc doi difficulty", "Copy difficulty and primary_skill_group exactly from the task."),
    ("Sai vung nghiep vu", "business_domain must equal the requested domain."),
    ("skills phai chua", "skills must contain the primary skill and only codes S1-S6."),
    ("duplicate", "Too similar to an existing question: change the business entity and measure, "
                  "not just the threshold/date/Top N."),
)


def repair_hints(errors, request=None):
    """Keep each raw error, and add an instruction the model can act on."""
    lines = []
    for error in errors:
        lines.append(error)
        for needle, hint in _HINTS:
            if needle in error and hint not in lines:
                lines.append("FIX: " + hint)
    tables = (request or {}).get("context_tables")
    if tables and any("Bang ngoai" in e or "Cot khong" in e for e in errors):
        lines.append("Allowed tables are exactly: " + ", ".join(tables))
    return lines


def derive_sql_metadata(sql, schema):
    """tables_used / required_columns computed from the SQL AST, not trusted from the model.
    Returns None when the SQL cannot be parsed/resolved; validate() then reports the real error."""
    try:
        tree = parse_select(sql)
        resolver = SQLSchema(schema)
        resolver.query(tree)
        tables = sorted(resolver.tables)
        return tables, {t: sorted(resolver.columns[t]) for t in tables}
    except (ValueError, TypeError, KeyError, parser.ParseError):
        return None


def normalize(value):
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def digest(value):
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def strings(nodes):
    return [n["String"]["sval"] for n in nodes]


def parse_select(sql):
    tree = json.loads(parser.parse_sql_json(sql))
    statements = tree.get("stmts", [])
    if len(statements) != 1 or set(statements[0]["stmt"]) != {"SelectStmt"}:
        raise ValueError("Chi chap nhan mot SELECT, co the kem WITH.")
    for tag, node in walk(tree):
        if tag.endswith("Stmt") and tag != "SelectStmt":
            raise ValueError(f"SQL bi cam: {tag}")
        if tag in {"IntoClause", "LockingClause", "RangeTableSample", "RangeFunction",
                   "SQLValueFunction", "CollateClause", "A_Indirection"}:
            raise ValueError(f"SQL chua duoc ho tro an toan: {tag}")
        if tag[:1].isupper() and isinstance(node, dict) and tag not in SAFE_NODES:
            raise ValueError(f"AST node chua duoc cho phep an toan: {tag}")
        if tag == "FuncCall":
            names = strings(node["funcname"])
            if len(names) > 2 or (len(names) == 2 and names[0] != "pg_catalog"):
                raise ValueError("Chi cho phep ham built-in pg_catalog.")
            if names[-1] not in SAFE_FUNCTIONS:
                raise ValueError(f"Ham khong nam trong allowlist: {names[-1]}")
        if tag == "TypeName":
            names = strings(node.get("names", []))
            if not names or names[-1] not in SAFE_TYPES or (
                    len(names) > 1 and names[:-1] != ["pg_catalog"]):
                raise ValueError("Chi cho phep cast sang kieu built-in an toan.")
        if tag == "A_Expr" and node.get("name"):
            names = strings(node["name"])
            if len(names) != 1 or names[0] not in SAFE_OPERATORS:
                raise ValueError("Operator khong nam trong allowlist.")
        if tag == "CommonTableExpr" and (node.get("search_clause") or node.get("cycle_clause")):
            raise ValueError("SEARCH/CYCLE chua duoc ho tro bo phan giai cot.")
    return statements[0]["stmt"]


class SQLSchema:
    """Resolve base/CTE/subquery columns in lexical SELECT scopes, fail closed."""

    def __init__(self, schema):
        self.schema = schema
        self.tables = set()
        self.columns = {table: set() for table in schema}

    def query(self, tree, ctes=None, outer=()):
        q = tree["SelectStmt"]
        ctes = dict(ctes or {})
        for item in q.get("withClause", {}).get("ctes", []):
            cte = item["CommonTableExpr"]
            aliases = strings(cte.get("aliascolnames", []))
            inner = cte["ctequery"]
            # Recursive self references use the nonrecursive branch's output schema.
            if q["withClause"].get("recursive"):
                seed = inner["SelectStmt"].get("larg")
                if seed:
                    cols = self.query({"SelectStmt": seed}, ctes, outer)
                    ctes[cte["ctename"]] = self.rename(cols, aliases)
            cols = self.query(inner, ctes, outer)
            ctes[cte["ctename"]] = self.rename(cols, aliases)
        if q.get("op", "SETOP_NONE") != "SETOP_NONE":
            left = self.query({"SelectStmt": q["larg"]}, ctes, outer)
            right = self.query({"SelectStmt": q["rarg"]}, ctes, outer)
            if len(left) != len(right):
                raise ValueError("Hai nhanh UNION/INTERSECT/EXCEPT khac so cot.")
            self.expr(q.get("sortClause", []), {}, outer, left)
            self.expr(q.get("limitCount"), {}, outer)
            return left
        scope = {}
        merged = set()

        def add_from(node):
            if "JoinExpr" in node:
                join = node["JoinExpr"]
                before = set(scope)
                add_from(join["larg"])
                left = {k: v for k, v in scope.items() if k not in before}
                before_right = set(scope)
                add_from(join["rarg"])
                right = {k: v for k, v in scope.items() if k not in before_right}
                using = strings(join.get("usingClause", []))
                if join.get("isNatural"):
                    raise ValueError("NATURAL JOIN khong duoc ho tro; dung ON/USING ro rang.")
                for col in using:
                    for side in (left, right):
                        if not any(col in cols for cols in side.values()):
                            raise ValueError(f"Cot USING khong ton tai: {col}")
                        for cols in side.values():
                            if col in cols:
                                self.mark(cols[col])
                    merged.add(col)
                self.expr(join.get("quals"), scope, outer, ctes=ctes, merged=merged)
                if join.get("alias"):
                    raise ValueError("Alias cho ca JOIN chua duoc ho tro; dung subquery.")
                return
            if "RangeVar" in node:
                rel = node["RangeVar"]
                name = rel["relname"]
                if rel.get("catalogname") or rel.get("schemaname") not in (None, "public"):
                    raise ValueError("Chi duoc doc bang public cua world.")
                if not rel.get("schemaname") and name in ctes:
                    cols = ctes[name]
                elif name in self.schema:
                    self.tables.add(name)
                    cols = {c: {(name, c)} for c in self.schema[name]}
                else:
                    raise ValueError(f"Bang/CTE khong ton tai: {name}")
                alias = rel.get("alias", {})
                label = alias.get("aliasname", name)
            elif "RangeSubselect" in node:
                rel = node["RangeSubselect"]
                alias = rel.get("alias", {})
                label = alias.get("aliasname")
                if not label:
                    raise ValueError("Subquery FROM can alias ro rang.")
                cols = self.query(rel["subquery"], ctes,
                                  ((scope,) + outer) if rel.get("lateral") else outer)
            else:
                raise ValueError("FROM chi ho tro bang, JOIN va SELECT subquery.")
            if label in scope:
                raise ValueError(f"Alias trung: {label}")
            scope[label] = self.rename(cols, strings(alias.get("colnames", [])))

        for node in q.get("fromClause", []):
            add_from(node)
        outputs = {}
        for item in q.get("targetList", []):
            target = item["ResTarget"]
            val = target["val"]
            if "ColumnRef" in val and "A_Star" in val["ColumnRef"]["fields"][-1]:
                fields = val["ColumnRef"]["fields"]
                selected = scope if len(fields) == 1 else {
                    strings(fields[:-1])[-1]: scope.get(strings(fields[:-1])[-1], {})}
                if not all(selected.values()):
                    raise ValueError("Alias cua wildcard khong ton tai.")
                for cols in selected.values():
                    for col, lineage in cols.items():
                        self.mark(lineage)
                        outputs[col] = lineage
                continue
            lineage = self.expr(val, scope, outer, ctes=ctes, merged=merged)
            name = target.get("name")
            if not name and "ColumnRef" in val:
                name = strings(val["ColumnRef"]["fields"])[-1]
            if not name and "FuncCall" in val:
                name = strings(val["FuncCall"]["funcname"])[-1]
            name = name or "?column?"
            if name in outputs:
                raise ValueError(f"Cot ket qua trung ten; can alias rieng: {name}")
            outputs[name] = lineage
        for key in ("whereClause", "havingClause", "windowClause", "distinctClause",
                    "limitCount", "limitOffset"):
            self.expr(q.get(key), scope, outer, ctes=ctes, merged=merged)
        for key in ("groupClause", "sortClause"):
            self.expr(q.get(key), scope, outer, outputs, ctes, merged)
        return outputs

    @staticmethod
    def rename(cols, aliases):
        if len(aliases) > len(cols):
            raise ValueError("So alias cot vuot so cot cua quan he.")
        return {(aliases[i] if i < len(aliases) else key): val
                for i, (key, val) in enumerate(cols.items())}

    def mark(self, lineage):
        for table, col in lineage:
            self.columns[table].add(col)

    def expr(self, value, scope, outer, outputs=None, ctes=None, merged=None):
        if value is None:
            return set()
        if isinstance(value, list):
            return set().union(*(self.expr(v, scope, outer, outputs, ctes, merged) for v in value))
        if not isinstance(value, dict):
            return set()
        if "SelectStmt" in value:
            cols = self.query(value, ctes, (scope,) + outer)
            return set().union(*cols.values())
        if "ColumnRef" in value:
            fields = value["ColumnRef"]["fields"]
            if any("A_Star" in f for f in fields):
                raise ValueError("Wildcard chi duoc dung o SELECT target.")
            names = strings(fields)
            col = names[-1]
            if len(names) == 1 and outputs and col in outputs:
                return outputs[col]
            if len(names) > 3 or (len(names) == 3 and names[0] != "public"):
                raise ValueError("Tham chieu cot ngoai schema public.")
            for current in (scope,) + tuple(outer):
                if len(names) > 1:
                    if names[-2] not in current:
                        continue
                    cols = current[names[-2]]
                    if col not in cols:
                        raise ValueError(f"Cot khong ton tai: {'.'.join(names)}")
                    lineage = cols[col]
                else:
                    matches = [cols[col] for cols in current.values() if col in cols]
                    if not matches:
                        continue
                    if len(matches) > 1 and col not in (merged or set()):
                        raise ValueError(f"Cot mo ho, can alias: {col}")
                    lineage = set().union(*matches)
                self.mark(lineage)
                return lineage
            raise ValueError(f"Cot khong ton tai: {'.'.join(names)}")
        return set().union(*(self.expr(v, scope, outer, outputs, ctes, merged)
                             for v in value.values()))


def sql_shape(sql):
    """Ignore literal/alias spelling, not predicates, columns or relation structure."""
    tree = parse_select(sql)
    aliases = {}
    occurrences = Counter()
    for tag, node in walk(tree):
        if tag == "RangeVar":
            occurrences[node["relname"]] += 1
            if node.get("alias"):
                aliases[node["alias"]["aliasname"]] = node["relname"] + (
                    "#" + str(occurrences[node["relname"]]) if occurrences[node["relname"]] > 1 else "")
    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value]
        if not isinstance(value, dict):
            return value
        if "A_Const" in value:
            return {"A_Const": "LITERAL"}
        if "ColumnRef" in value:
            node = value["ColumnRef"]
            fields = node["fields"]
            names = strings(fields) if all("String" in f for f in fields) else []
            if len(names) >= 2 and names[-2] in aliases:
                names[-2] = aliases[names[-2]]
                fields = [{"String": {"sval": n}} for n in names]
            return {"ColumnRef": {"fields": fields}}
        return {k: clean(v) for k, v in value.items()
                if not (k == "schemaname" and v == "public")
                if k not in {"location", "stmt_location", "stmt_len", "alias", "name"}
                or k == "name" and isinstance(v, list)}
    return hashlib.sha256(json.dumps(clean(tree), sort_keys=True).encode()).hexdigest()


def signature(question):
    metadata = question.get("metadata") or {}
    sig = question.get("logic_signature") or metadata.get("logic_signature") or {}
    # Explicit mapping of legacy Core keys, not invented analytic metadata.
    return {"analysis_goal": sig.get("analysis_goal", sig.get("goal", "")),
            "output_grain": sig.get("output_grain", sig.get("grain", "")),
            "filter_pattern": sig.get("filter_pattern", sig.get("predicate", "")),
            "aggregation_pattern": sig.get("aggregation_pattern", sig.get("transformation", ""))}


def detect_duplicate(candidate, corpus, high=.85, review=.65):
    text = candidate["question"]
    corpus = [q for q in corpus if q.get("question") or q.get("question_text")]
    result = {"text_sha256": digest(text), "similarity": 0.0, "closest_question": None,
              "sources_compared": dict(Counter(q.get("origin", "unknown") for q in corpus)),
              "exact_duplicate": False, "logic_duplicate": False,
              "suspected_duplicate": False, "signature": signature(candidate), "warnings": []}
    if not corpus:
        return result
    texts = [normalize(q.get("question", q.get("question_text", ""))) for q in corpus]
    vectors = TfidfVectorizer(analyzer="char", ngram_range=(3, 5)).fit_transform(
        texts + [normalize(text)])
    scores = cosine_similarity(vectors[-1], vectors[:-1]).ravel()
    closest = int(scores.argmax())
    result.update(similarity=round(float(scores[closest]), 6),
                  closest_question=corpus[closest].get("id", corpus[closest].get("question_id")),
                  closest_origin=corpus[closest].get("origin"))
    shape = sql_shape(candidate["reference_sql"]) if candidate.get("reference_sql") else None
    sig = {k: normalize(v) for k, v in signature(candidate).items()}
    for q in corpus:
        qtext = q.get("question", q.get("question_text", ""))
        exact = digest(qtext) == digest(text)
        other = {k: normalize(v) for k, v in signature(q).items()}
        sig_equal = all(sig.values()) and sig == other
        try:
            same_shape = shape is not None and shape == sql_shape(q.get("reference_sql", ""))
        except (ValueError, parser.ParseError, KeyError):
            same_shape = False
        if exact or sig_equal or same_shape:
            result.update(exact_duplicate=exact, logic_duplicate=bool(sig_equal or same_shape),
                          duplicate_of=q.get("id", q.get("question_id")),
                          duplicate_origin=q.get("origin"),
                          duplicate_reason="normalized_text" if exact else
                          "identical_logic_signature" if sig_equal else "same_SQL_shape_ignoring_literals_aliases")
            break
    result["suspected_duplicate"] = result["similarity"] >= review
    if result["suspected_duplicate"]:
        result["warnings"].append("high_lexical_similarity" if result["similarity"] >= high
                                  else "lexical_similarity_needs_review")
    # Partial signature matches are hints, never rejection on shared skills/tables.
    result["logic_review_pairs"] = [
        {"id": q.get("id", q.get("question_id")), "origin": q.get("origin"),
         "matching_fields": [k for k, v in sig.items() if v and v == normalize(signature(q)[k])]}
        for q in corpus if sum(bool(v) and v == normalize(signature(q)[k]) for k, v in sig.items()) >= 2]
    if result["logic_review_pairs"]:
        result["suspected_duplicate"] = True
    return result


def validate_question(candidate, request, schema, references, corpus, high=.85, review=.65):
    """Names/metadata checks only; no SQL execution or claim of semantic approval."""
    report = {"passed_basic": False, "semantic_valid": None, "model_b_reviewed": False,
              "review_disposition": "HARD_FAIL", "checks": {}, "errors": [], "warnings": [
                  "Question-only: table/column usage is model-declared, not derived from SQL.",
                  "Solvability, business logic and actual difficulty require human review."],
              "execution": {"status": "not_applicable", "row_count": None,
                            "reason": "No SQL answer is generated by Model A."}}
    def check(name, action):
        try:
            detail = action()
            report["checks"][name] = {"passed": True, "detail": detail}
        except (ValueError, TypeError, KeyError) as exc:
            report["checks"][name] = {"passed": False, "error": str(exc)}
            report["errors"].append(f"{name}: {exc}")
    def json_check():
        if not isinstance(candidate, dict):
            raise ValueError("Output phai la JSON object.")
        def no_answer(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.lower() in {"reference_sql", "sql", "answer", "solution", "sql_answer", "model_sql"}:
                        raise ValueError("Chi sinh de/metadata; khong tra reference_sql hay dap an.")
                    no_answer(item)
            elif isinstance(value, list):
                for item in value:
                    no_answer(item)
            elif isinstance(value, str) and re.search(r"\bSELECT\b[\s\S]*?\bFROM\b", value, re.I):
                raise ValueError("Khong chen SQL dap an trong de/metadata.")
        no_answer(candidate)
        for key in ("title", "question", "difficulty", "primary_skill_group", "business_domain",
                    "business_goal", "difficulty_reason"):
            if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                raise ValueError(f"Truong {key} phai la chuoi khong rong.")
        for key in ("skills", "tables_used", "source_question_ids", "output_columns"):
            values = candidate.get(key)
            if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
                raise ValueError(f"Truong {key} phai la mang chuoi khong rong.")
            if len(set(values)) != len(values):
                raise ValueError(f"Truong {key} co phan tu trung.")
        sig = candidate.get("logic_signature")
        if not isinstance(sig, dict) or not all(isinstance(sig.get(k), str) and sig[k].strip() for k in
                ("output_grain", "analysis_goal", "filter_pattern", "aggregation_pattern")):
            raise ValueError("logic_signature thieu bon truong chuoi.")
        return "question metadata; no answer"
    check("json", json_check)
    if report["errors"]:
        return report
    def schema_check():
        required = candidate.get("required_columns")
        if not isinstance(required, dict) or set(required) != set(candidate["tables_used"]):
            raise ValueError("required_columns phai co dung cac bang tables_used.")
        for table in candidate["tables_used"]:
            if table not in schema or table not in request["context_tables"]:
                raise ValueError(f"Bang ngoai context/schema: {table}")
            cols = required[table]
            if not isinstance(cols, list) or not cols or not all(isinstance(c, str) and c in schema[table] for c in cols):
                raise ValueError(f"Cot metadata sai: {table}; chi khai bao cot vat ly co that.")
            if len(set(cols)) != len(cols):
                raise ValueError(f"Cot metadata trung: {table}")
        return {"declared_tables": candidate["tables_used"], "declared_columns": required}
    check("schema", schema_check)
    def metadata_check():
        if candidate["difficulty"] != request["difficulty"] or candidate["primary_skill_group"] != request["skill"]:
            raise ValueError("Khong duoc doi difficulty/primary_skill nguoi dung.")
        if candidate["business_domain"] not in request["allowed_domains"] or (
                request.get("domain") and candidate["business_domain"] != request["domain"]):
            raise ValueError("Sai vung nghiep vu yeu cau.")
        if request["skill"] not in candidate["skills"] or not set(candidate["skills"]).issubset(request["allowed_skills"]):
            raise ValueError("skills phai chua primary skill va chi dung ma Core.")
        if len(candidate["source_question_ids"]) != 5 or set(candidate["source_question_ids"]) != set(references):
            raise ValueError("source_question_ids phai dung nam reference da chon.")
        return "user assignment and Core provenance checked; skill reasoning unverified"
    check("metadata", metadata_check)
    if report["errors"]:
        return report
    check("topic_relations", lambda: check_group_usage(candidate, request))
    check("business_dependencies", lambda: check_question_dependencies(candidate, schema))
    report["warnings"].extend(report["checks"].get("business_dependencies", {}).get("detail", {}).get("review_notes", []))
    if report["errors"]:
        return report
    duplicate = detect_duplicate(candidate, corpus, high, review)
    report.update(duplicate=duplicate, logic_signature=candidate["logic_signature"], candidate_metadata=candidate)
    if duplicate["exact_duplicate"] or duplicate["logic_duplicate"]:
        report["errors"].append("duplicate: Trung de/logic ro rang; doi muc tieu nghiep vu.")
        return report
    if duplicate["suspected_duplicate"]:
        report["warnings"].append("suspected_duplicate: can nguoi duyet kiem tra.")
    report["passed_basic"] = True
    report["review_disposition"] = "NEEDS_HUMAN"
    return report


def verify_readonly(conn, schema):
    """Require a real nonprivileged login; never demote a superuser implicitly."""
    role = conn.execute("SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
                        "FROM pg_roles WHERE rolname=current_user").fetchone()
    flags = list(role.values()) if isinstance(role, dict) else list(role)
    if not flags[0] or any(flags[1:]):
        raise ValueError("Tai khoan Enterprise phai la login SELECT-only, khong superuser/quyen quan tri.")
    bad = conn.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_toast' "
                       "AND c.relkind IN ('r','p','v','m','f') AND ("
                       "has_table_privilege(c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') "
                       "OR has_any_column_privilege(c.oid,'INSERT,UPDATE,REFERENCES')) LIMIT 1").fetchone()
    creates = conn.execute("SELECT nspname FROM pg_namespace WHERE has_schema_privilege(oid,'CREATE') "
                          "UNION ALL SELECT datname FROM pg_database WHERE datname=current_database() "
                          "AND has_database_privilege(oid,'CREATE,TEMP')").fetchone()
    if bad or creates:
        raise ValueError("Tai khoan Enterprise con quyen ghi/CREATE/TEMP; khong thuc thi AI SQL.")
    shadows = conn.execute("SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                           "WHERE n.nspname='public' AND p.proname=ANY(%s) LIMIT 1",
                           (sorted(SAFE_FUNCTIONS),)).fetchone()
    custom_ops = conn.execute("SELECT o.oprname FROM pg_operator o JOIN pg_namespace n ON n.oid=o.oprnamespace "
                              "WHERE n.nspname='public' AND o.oprname=ANY(%s) LIMIT 1",
                              (sorted(SAFE_OPERATORS),)).fetchone()
    if shadows or custom_ops:
        raise ValueError("public co ham/operator trung allowlist co the shadow builtin; khong thuc thi AI SQL.")
    for table in schema:
        row = conn.execute("SELECT has_table_privilege(%s,'SELECT')", (f"public.{table}",)).fetchone()
        if not (next(iter(row.values())) if isinstance(row, dict) else row[0]):
            raise ValueError(f"Thieu SELECT tren public.{table}")
    return True


def execute_readonly(sql, config, schema):
    if not config.get("user"):
        return {"status": "not_run", "row_count": None,
                "reason": "Chua cau hinh tai khoan Enterprise SELECT-only; khong dung postgres thay the."}
    started = time.perf_counter()
    try:
        with psycopg.connect(**config["connection"], autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute("SET LOCAL search_path = pg_catalog, public")
                conn.execute("SET LOCAL TIME ZONE 'UTC'")
                conn.execute("SELECT set_config('statement_timeout',%s,true)", (str(config["timeout_ms"]),))
                try:
                    verify_readonly(conn, schema)
                except ValueError as exc:
                    return {"status": "not_run", "row_count": None, "reason": str(exc)}
                # PREPARE-style binding/type checks occur only after AST and privilege checks.
                conn.execute("EXPLAIN (FORMAT JSON) " + sql)
                with conn.cursor(name="model_a_readonly") as cur:
                    cur.execute(sql)
                    count = 0
                    columns = None
                    while True:
                        rows = cur.fetchmany(1000)
                        columns = [c.name for c in cur.description] if cur.description else columns
                        count += len(rows)
                        if count > config["max_rows"]:
                            return {"status": "executed_with_rows", "row_count": None,
                                    "row_count_lower_bound": count, "result_truncated": True,
                                    "columns": columns, "warning": "Dung doc tai gioi han; chua dem het ket qua."}
                        if not rows:
                            break
                return {"status": "executed_with_rows" if count else "executed_empty",
                        "row_count": count, "columns": columns,
                        "runtime_ms": round((time.perf_counter()-started)*1000, 3)}
    except psycopg.errors.QueryCanceled as exc:
        return {"status": "timeout", "row_count": None, "error": str(exc)}
    except psycopg.OperationalError:
        return {"status": "not_run", "row_count": None,
                "reason": "Khong ket noi duoc Enterprise SELECT-only; kiem tra cau hinh/quyen."}
    except psycopg.Error as exc:
        return {"status": "execution_error", "row_count": None,
                "sqlstate": exc.sqlstate, "error": str(exc)}


def validate(candidate, request, schema, references, corpus, execution_config,
             high=.85, review=.65, executor=execute_readonly):
    report = {"passed_basic": False, "semantic_valid": None, "model_b_reviewed": False,
              "checks": {}, "errors": [], "warnings": [
                  "Basic Validator khong chung minh ngu nghia, do kho thuc chat hay tinh moi cua de.",
                  "Can duyet dieu kien NULL, thoi gian, tien te, dong hang va thu tu dau ra."],
              "execution": {"status": "not_run", "row_count": None, "reason": "Chua qua kiem tra co ban."}}
    def check(name, action):
        try:
            value = action()
            report["checks"][name] = {"passed": True, "detail": value}
            return value
        except (ValueError, TypeError, KeyError, parser.ParseError) as exc:
            report["checks"][name] = {"passed": False, "error": str(exc)}
            report["errors"].append(f"{name}: {exc}")
            return None

    def json_check():
        if not isinstance(candidate, dict):
            raise ValueError("Output phai la JSON object.")
        for key in ("title", "question", "difficulty", "primary_skill_group", "business_domain",
                    "business_goal", "difficulty_reason", "reference_sql"):
            if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                raise ValueError(f"Truong {key} phai la chuoi khong rong.")
        for key in ("skills", "tables_used", "source_question_ids"):
            if not isinstance(candidate.get(key), list) or not candidate[key] or not all(
                    isinstance(v, str) and v for v in candidate[key]):
                raise ValueError(f"Truong {key} phai la mang chuoi khong rong.")
            if len(set(candidate[key])) != len(candidate[key]):
                raise ValueError(f"Truong {key} co phan tu trung.")
        sig = candidate.get("logic_signature")
        if not isinstance(sig, dict) or not all(isinstance(sig.get(k), str) and sig[k].strip()
                for k in ("output_grain", "analysis_goal", "filter_pattern", "aggregation_pattern")):
            raise ValueError("logic_signature thieu bon truong chuoi bat buoc.")
        if not isinstance(candidate.get("required_columns"), dict):
            raise ValueError("required_columns phai la object bang -> mang cot.")
        return "required_fields_valid"
    if check("json", json_check) is None:
        return report
    tree = check("sql_safety", lambda: parse_select(candidate["reference_sql"]))
    if tree is None:
        return report
    # Do not duplicate the complete AST in persisted reports.
    report["checks"]["sql_safety"]["detail"] = "pglast PostgreSQL AST; one SELECT; conservative allowlists"

    def schema_check():
        for table in candidate["tables_used"]:
            if table not in schema or table not in request["context_tables"]:
                raise ValueError(f"Bang ngoai context/schema: {table}")
        if set(candidate["required_columns"]) != set(candidate["tables_used"]):
            raise ValueError("required_columns phai co dung cac bang tables_used.")
        for table, cols in candidate["required_columns"].items():
            if not isinstance(cols, list) or not all(isinstance(c, str) and c in schema[table] for c in cols):
                raise ValueError(f"Cot metadata sai: {table}")
        resolver = SQLSchema(schema)
        outputs = resolver.query(tree)
        if resolver.tables != set(candidate["tables_used"]):
            raise ValueError(f"tables_used lech SQL thuc te: {sorted(resolver.tables)}")
        for table in resolver.tables:
            if not resolver.columns[table].issubset(set(candidate["required_columns"][table])):
                raise ValueError(f"required_columns thieu cot SQL cua {table}: {sorted(resolver.columns[table])}")
        return {"actual_tables": sorted(resolver.tables),
                "actual_columns": {t: sorted(resolver.columns[t]) for t in sorted(resolver.tables)},
                "output_columns": list(outputs), "limitation": "Static scope binding; server type resolution requires SELECT-only login."}
    check("schema", schema_check)

    def metadata_check():
        if candidate["difficulty"] != request["difficulty"] or candidate["primary_skill_group"] != request["skill"]:
            raise ValueError("Khong duoc doi difficulty/primary_skill nguoi dung.")
        if request.get("domain") and candidate["business_domain"] != request["domain"]:
            raise ValueError("Sai vung nghiep vu yeu cau.")
        if candidate["business_domain"] not in request["allowed_domains"]:
            raise ValueError("Business domain khong co trong Core/Rules.")
        if request["skill"] not in candidate["skills"] or not set(candidate["skills"]).issubset(set(request["allowed_skills"])):
            raise ValueError("skills phai chua primary skill va chi dung ma Core.")
        if len(candidate["source_question_ids"]) != 5 or set(candidate["source_question_ids"]) != set(references):
            raise ValueError("source_question_ids phai dung nam reference da chon.")
        tags = Counter(tag for tag, _ in walk(tree))
        joins = tags["JoinExpr"]
        aggregate = any(tag == "FuncCall" and strings(node["funcname"])[-1] in
                        {"count", "sum", "avg", "min", "max", "string_agg", "array_agg"}
                        for tag, node in walk(tree))
        ctes = tags["CommonTableExpr"]
        window = any(tag == "FuncCall" and node.get("over") for tag, node in walk(tree))
        skill = request["skill"]
        if skill == "S1" and (joins or aggregate or ctes or tags["SubLink"] or window or tags["SelectStmt"] > 1):
            found = [name for name, hit in (("JOIN", joins), ("aggregate", aggregate), ("CTE", ctes),
                                            ("subquery", tags["SubLink"]), ("window", window),
                                            ("nested SELECT", tags["SelectStmt"] > 1)) if hit]
            raise ValueError("S1 khong phai trong tam loc/chon truc tiep (dang dung: " + ", ".join(found) + ").")
        if skill == "S2" and not (joins or sum(1 for tag, _ in walk(tree) if tag == "RangeVar") >= 2):
            raise ValueError("S2 thieu dau hieu ket noi quan he.")
        if skill == "S3" and not aggregate:
            raise ValueError("S3 thieu aggregation.")
        if skill == "S4" and not (tags["SubLink"] or tags["RangeSubselect"] or joins):
            raise ValueError("S4 thieu subquery/EXISTS/anti-join tuong duong.")
        if skill == "S5" and not (ctes or window):
            raise ValueError("S5 thieu CTE/window.")
        recursive = any(tag == "withClause" and node.get("recursive") for tag, node in walk(tree))
        if skill == "S6" and not (recursive or (window and tags["SelectStmt"] >= 3)):
            raise ValueError("S6 can dau hieu de quy hoac xu ly lich su/tich luy nhieu tang.")
        if request["difficulty"] == "easy" and (ctes or window or tags["SubLink"]):
            raise ValueError("Easy khong nen can CTE/window/subquery; thiet ke lai theo Rules.")
        return {"technical_signals": dict(tags), "reasoning_difficulty_confirmed": False}
    check("metadata", metadata_check)
    if report["errors"]:
        return report
    duplicate = detect_duplicate(candidate, corpus, high, review)
    report["duplicate"] = duplicate
    report["logic_signature"] = candidate["logic_signature"]
    report["candidate_metadata"] = {k: v for k, v in candidate.items() if k != "reference_sql"}
    if duplicate["exact_duplicate"] or duplicate["logic_duplicate"]:
        report["errors"].append("duplicate: Trung de/logic ro rang; doi muc tieu nghiep vu, khong paraphrase/doi nguong.")
        return report
    if duplicate["suspected_duplicate"]:
        report["warnings"].append("suspected_duplicate: can Model B/nguoi duyet kiem tra.")
    report["execution"] = executor(candidate["reference_sql"], execution_config, schema)
    if report["execution"]["status"] in {"execution_error", "timeout"}:
        report["errors"].append("execution: " + report["execution"].get("error", "timeout"))
    elif report["execution"]["status"] == "not_run":
        report["warnings"].append("SQL chua thuc thi; static checks khong thay the server/semantic validation.")
    report["passed_basic"] = not report["errors"]
    return report
