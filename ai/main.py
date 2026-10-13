"""Manual SQLArena Model A v1. Only Draft INSERTs, never database migrations."""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from validator import skill_contract, validate_question
from context_policy import choose_context_group, matching_fk


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_VERSION = "model_a_v2.1_topic_groups"
DRAFT_FIELDS = ("world_id", "question", "compare_mode", "difficulty", "skills",
                "traps", "parent_ids", "depth", "status", "gen_model", "gen_prompt_version",
                "retry_count", "schema_context", "schema_text", "validation_report")


def load_config():
    config = {**dotenv_values(HERE / ".env"), **os.environ}
    if config.get("AI_PROVIDER") != "ollama":
        raise ValueError("AI_PROVIDER chi ho tro ollama trong Model A v1.")
    for key in ("MAX_RETRIES", "STATEMENT_TIMEOUT_MS", "MAX_RESULT_ROWS",
                "OLLAMA_TIMEOUT_SECONDS", "OLLAMA_CONTEXT_SIZE"):
        config[key] = int(config[key])
        if config[key] < (0 if key == "MAX_RETRIES" else 1):
            raise ValueError(f"Cau hinh khong hop le: {key}")
    for key in ("DUPLICATE_HIGH", "DUPLICATE_REVIEW"):
        config[key] = float(config[key])
    if not 0 <= config["DUPLICATE_REVIEW"] <= config["DUPLICATE_HIGH"] <= 1:
        raise ValueError("Nguong duplicate phai 0 <= review <= high <= 1.")
    if not config.get("MODEL_NAME") or not config.get("OLLAMA_HOST", "").startswith(("http://", "https://")):
        raise ValueError("MODEL_NAME/OLLAMA_HOST khong hop le.")
    return config


def connection_config(config, prefix):
    return {"host": config[f"{prefix}_DB_HOST"], "port": int(config[f"{prefix}_DB_PORT"]),
            "dbname": config[f"{prefix}_DB_NAME"], "user": config[f"{prefix}_DB_USER"],
            "password": config.get(f"{prefix}_DB_PASSWORD", ""), "connect_timeout": 5}


def connect(config, prefix, readonly=True):
    kwargs = connection_config(config, prefix)
    kwargs["options"] = "-c statement_timeout=15000" + (
        " -c default_transaction_read_only=on" if readonly else "")
    return psycopg.connect(**kwargs, row_factory=dict_row)


def read_rules(config):
    path = ROOT / config["RULES_PATH"]
    if not path.is_file():
        raise ValueError(f"Khong tim thay Rules: {path}. Dung sinh, khong tu doan taxonomy.")
    text = path.read_text(encoding="utf-8-sig")
    # Use actual Markdown section boundaries; original quotas are never new-run quotas.
    sections = {}
    for match in re.finditer(r"(?m)^##\s+(\d+)\.\s+", text):
        start = match.start()
        end_match = re.search(r"(?m)^##\s+\d+\.\s+", text[match.end():])
        end = match.end() + end_match.start() if end_match else len(text)
        sections[int(match[1])] = text[start:end].strip()
    taxonomy = sections.get(2, "")
    definitions = {}
    for level in ("Easy", "Medium", "Hard"):
        match = re.search(rf"\*\*{level}:\*\*\s*(.*?)(?=\n\n|\Z)", taxonomy, re.S)
        if not match:
            raise ValueError(f"Rules thieu dinh nghia {level}.")
        definitions[level.lower()] = match[0]
    skills = {}
    for match in re.finditer(r"(?m)^\| (S[1-6]) \| ([^|]+)\|", sections.get(3, "")):
        skills[match[1]] = match[2].strip()
    quota_matrix = {}
    for match in re.finditer(r"(?m)^\| (S[1-6]) \|[^|]+\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
                             sections.get(3, "")):
        quota_matrix[match[1]] = {"easy": int(match[2]), "medium": int(match[3]), "hard": int(match[4])}
    if len(quota_matrix) != 6:
        raise ValueError("Rules thieu ma tran ky nang x do kho (muc 3).")
    if len(skills) != 6 or not sections.get(5):
        raise ValueError("Rules thieu S1-S6 hoac quy tac chat luong.")
    principle = re.search(r"\*\*Độ khó được đánh giá.*?(?=\n\n|\Z)", taxonomy, re.S)
    if not principle:
        raise ValueError("Rules thieu nguyen tac loi giai don gian hop ly nhat.")
    classifications = sections[3].split("**Quy tắc phân loại:**", 1)[-1]
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "definitions": definitions, "skills": skills, "principle": principle[0],
            "classification": classifications, "quality": sections[5], "quota_matrix": quota_matrix,
            "boundary": sections[1]}


def feasible_pairs(rules):
    """skill -> difficulties the Rules taxonomy actually defines (non-zero cell).
    Counts are NOT quotas for a new run; a zero cell means 'this pairing does not exist'."""
    return {skill: {level for level, n in levels.items() if n > 0}
            for skill, levels in (rules.get("quota_matrix") or {}).items()}


def check_feasible(rules, request):
    pairs = feasible_pairs(rules)
    if pairs and request["difficulty"] not in pairs.get(request["skill"], set()):
        valid = [d for d in ("easy", "medium", "hard") if d in pairs.get(request["skill"], set())]
        raise ValueError(f"Rules khong dinh nghia {request['skill']} o muc {request['difficulty']}. "
                         f"{request['skill']} chi hop le voi: {', '.join(valid) or 'khong co'}.")


def inspect_database(config, rules):
    with connect(config, "ARENA") as conn:
        world = conn.execute("SELECT * FROM core.worlds WHERE world_id=%s", (config["WORLD_ID"],)).fetchone()
        if not world or world["dialect"] != "postgresql":
            raise ValueError("Core world khong ton tai hoac khong phai PostgreSQL.")
        skills = conn.execute("SELECT * FROM core.skills ORDER BY skill_id").fetchall()
        if {s["skill_id"] for s in skills} != set(rules["skills"]):
            raise ValueError("Core skills khong khop S1-S6 trong Rules.")
        sources = conn.execute("SELECT * FROM core.source_questions WHERE world_id=%s ORDER BY question_id",
                               (world["world_id"],)).fetchall()
        if not sources:
            raise ValueError("Core khong co cau nguon.")
        columns = conn.execute("SELECT column_name,udt_name,is_nullable,column_default,is_identity "
                               "FROM information_schema.columns WHERE table_schema='draft' "
                               "AND table_name='question_drafts' ORDER BY ordinal_position").fetchall()
        column_map = {c["column_name"]: c for c in columns}
        blockers = []
        missing = sorted(set(DRAFT_FIELDS) - set(column_map))
        if missing:
            blockers.append("Draft thieu bang/cot: " + ", ".join(missing) + ". Nguoi dung tu bo sung; khong migration.")
        for field in ("skills", "traps", "parent_ids", "schema_context", "validation_report"):
            if field in column_map and column_map[field]["udt_name"] != "jsonb":
                blockers.append(f"draft.question_drafts.{field} phai la JSONB; mapping hien tai khong ho tro kieu khac.")
        if "schema_text" in column_map and column_map["schema_text"]["udt_name"] != "text":
            blockers.append("draft.question_drafts.schema_text phai la TEXT.")
        for col in columns:
            if col["column_name"] not in DRAFT_FIELDS and col["is_nullable"] == "NO" and not (
                    col["column_default"] or col["is_identity"] == "YES"):
                blockers.append(f"Cot bat buoc ngoai mapping khong co default: {col['column_name']}")
        constraints = conn.execute("SELECT pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k "
                                   "WHERE k.conrelid=to_regclass('draft.question_drafts')").fetchall()
        compare = [r["definition"] for r in constraints if r["definition"].startswith("CHECK")
                   and "compare_mode" in r["definition"]]
        if compare and not all("'unordered'" in c and "'ordered'" in c for c in compare):
            blockers.append("compare_mode khong tuong thich ordered/unordered; can cap nhat mapping theo schema.")
        triggers = conn.execute("SELECT tgname FROM pg_trigger WHERE tgrelid=to_regclass('draft.question_drafts') "
                                "AND NOT tgisinternal AND tgenabled <> 'D'").fetchall()
        if triggers:
            blockers.append("Draft co user trigger; khong INSERT khi chua xac minh tac dong: " +
                            ", ".join(t["tgname"] for t in triggers))
        drafts = conn.execute("SELECT * FROM draft.question_drafts WHERE world_id=%s ORDER BY draft_id",
                              (world["world_id"],)).fetchall() if columns else []
    tables = world["schema_description"]["tables"]
    schema = {t["table"]: {c["name"]: c["postgres_type"] for c in t["columns"]} for t in tables}
    if world["database_name"] != config["CATALOG_DB_NAME"] or world["database_name"] != config["ENTERPRISE_DB_NAME"]:
        raise ValueError("Core database_name khong khop database Enterprise da cau hinh.")
    with connect(config, "CATALOG") as conn:
        live = conn.execute("SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod) AS type "
                            "FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
                            "JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "WHERE n.nspname='public' AND c.relkind IN ('r','p') "
                            "AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum").fetchall()
        actual = {}
        for row in live:
            actual.setdefault(row["relname"], {})[row["attname"]] = row["type"]
        if actual != schema:
            raise ValueError("Schema Enterprise thuc te lech Core; dung sinh, khong sua database.")
    return {"world": world, "skills": skills, "sources": sources, "drafts": drafts,
            "schema": schema, "columns": column_map, "constraints": constraints, "blockers": blockers}


def corpus_from(data):
    corpus = [{**q, "id": q["question_id"], "origin": "core"} for q in data["sources"]]
    for q in data["drafts"]:
        meta = (q.get("validation_report") or {}).get("candidate_metadata", {})
        corpus.append({**meta, "id": q["draft_id"], "question": q["question"], "origin": "draft"})
    return corpus


def prompt_input(data, input_fn=input, print_fn=print, feasible=None):
    print_fn("========== SQLARENA MODEL A ==========\n")
    while True:
        try:
            count = int(input_fn("Số câu muốn sinh: "))
            if count > 0:
                break
        except ValueError:
            pass
        print_fn("Nhập số nguyên dương.")
    def menu(title, choices):
        print_fn("\n" + title)
        for i, (_, label) in enumerate(choices, 1):
            print_fn(f"{i}. {label}")
        while True:
            try:
                index = int(input_fn("Lựa chọn: ")) - 1
                if 0 <= index < len(choices):
                    return choices[index][0]
            except ValueError:
                pass
            print_fn("Lựa chọn không hợp lệ.")
    difficulty = menu("Chọn độ khó:", [(d, d.title()) for d in ("easy", "medium", "hard")])
    skill_choices = [(s["skill_id"], f"{s['skill_id']} - {s['name']}") for s in data["skills"]
                     if feasible is None or difficulty in feasible.get(s["skill_id"], ())]
    shown = {c[0] for c in skill_choices}
    hidden = [s["skill_id"] for s in data["skills"] if s["skill_id"] not in shown]
    if hidden:
        print_fn(f"(Ẩn {', '.join(hidden)}: Rules không định nghĩa tổ hợp với độ khó {difficulty}.)")
    if not skill_choices:
        raise ValueError(f"Khong co ky nang hop le cho do kho {difficulty}.")
    skill = menu("Chọn kỹ năng:", skill_choices)
    domains = sorted({q["primary_business_domain"] for q in data["sources"]})
    domain = menu("Chọn vùng nghiệp vụ:", [(d, d) for d in domains] + [(None, "Không giới hạn")])
    while True:
        tables = [v.strip() for v in input_fn("Nhập bảng ưu tiên (Enter để bỏ qua): ").split(",") if v.strip()]
        if set(tables).issubset(data["schema"]) and len(tables) <= 6:
            break
        print_fn("Bảng không tồn tại hoặc vượt 6 bảng cho context cục bộ. Nhập lại.")
    extra = input_fn("Yêu cầu bổ sung (Enter để bỏ qua): ")
    request = {"count": count, "difficulty": difficulty, "skill": skill, "domain": domain,
               "preferred_tables": list(dict.fromkeys(tables)), "extra": extra,
               "allowed_domains": domains, "allowed_skills": [s["skill_id"] for s in data["skills"]]}
    print_fn("\n-------------------------------------")
    print_fn(f"Số câu: {count}\nĐộ khó: {difficulty.title()}\nKỹ năng: {skill}\n"
             f"Nghiệp vụ: {domain or 'Không giới hạn'}\nBảng ưu tiên: {', '.join(tables) or 'Tự chọn'}")
    return request if input_fn("Xác nhận sinh đề? (Y/N): ").strip().casefold() == "y" else None


def select_tables(data, request, index):
    return choose_context_group(data, request, index)["tables"]


def select_references(data, request, tables, index):
    pool = [q for q in data["sources"] if q["difficulty"] == request["difficulty"]]
    if len(pool) < 5:
        raise ValueError(f"Chi co {len(pool)} source {request['difficulty']}; can it nhat 5 cung do kho.")
    def score(q):
        return (12 * (q["primary_skill_group"] == request["skill"]) +
                6 * (q["primary_business_domain"] == request["domain"]) +
                2 * len(set(q["metadata"].get("tables_used", [])) & set(tables)))
    # Rotate within preference tiers, not between difficulty pools.
    positions = {q["question_id"]: (i - index) % len(pool) for i, q in enumerate(pool)}
    pool.sort(key=lambda q: (-score(q), positions[q["question_id"]]))
    selected, goals = [], set()
    for q in pool:
        goal = q["metadata"].get("business_goal", q["title"])
        if goal in goals:
            continue
        goals.add(goal)
        selected.append(q)
        if len(selected) == 5:
            break
    if len(selected) < 5:
        selected += [q for q in pool if q not in selected][:5-len(selected)]
    return selected


def build_context(data, rules, request, index):
    group = choose_context_group(data, request, index)
    tables = group["tables"]
    scoped_request = {**request, "domain": group["domain"]}
    refs = select_references(data, scoped_request, tables, index)
    schema_tables = []
    for t in data["world"]["schema_description"]["tables"]:
        if t["table"] in tables:
            schema_tables.append({"table": t["table"], "columns": [
                {"name": c["name"], "type": c["postgres_type"], "nullable": c["nullable"]}
                for c in t["columns"]], "primary_key": t["primary_key"],
                "checks": [c["definition"] for c in t["constraints"] if c["kind"] == "c"]})
    relevant_rules = []
    for rule in data["world"]["business_rules"]["rules"]:
        excerpt = rule.get("dataset_v1_validator_excerpt", "")
        related = sorted(t for t in data["schema"] if re.search(rf"\b{re.escape(t)}\b", excerpt))
        if set(related) & set(tables):
            relevant_rules.append({"code": rule["code"], "title": rule.get("title_from_document"),
                                   "related_tables": related, "applied_dataset_v1_rule": excerpt})
    abstract_refs, limitations = [], []
    for q in refs:
        meta = q["metadata"]
        abstract = {"source_id": q["question_id"], "difficulty": q["difficulty"],
                    "skill": q["primary_skill_group"], "business_domain": q["primary_business_domain"],
                    "scope_compatible": set(meta.get("tables_used", [])).issubset(tables)}
        for key, source_key in (("logic_pattern", "logic_signature"), ("output_grain", "output_grain"),
                                ("business_goal_to_avoid", "business_goal")):
            if meta.get(source_key) is not None:
                abstract[key] = meta[source_key]
            else:
                limitations.append(f"{q['question_id']} metadata thieu {source_key}.")
        if isinstance(abstract.get("logic_pattern"), dict):
            # Real source metadata, reduced to analytic mechanics rather than repeated titles.
            abstract["logic_pattern"] = {k: v for k, v in abstract["logic_pattern"].items()
                                         if k in ("transformation", "predicate", "filter_pattern",
                                                  "aggregation_pattern", "analysis_features")}
        abstract_refs.append(abstract)
    schema_context = {"dialect": data["world"]["dialect"], "tables": schema_tables,
                      "context_group": group,
                      "fk_relations": [f for f in data["world"]["fk_relations"] if
                                       {f["table_name"], f["referenced_table"]}.issubset(tables)],
                      "business_rules": relevant_rules,
                      "business_rule_precedence": data["world"]["business_rules"].get("precedence"),
                      "business_rule_alignment_notes": data["world"]["business_rules"].get("alignment_notes"),
                      "allowed_sql_features": data["world"]["allowed_sql_features"]}
    skill_line = next((line for line in rules["classification"].splitlines()
                       if line.startswith(f"- {request['skill']}:")), "")
    context = {"user_request": scoped_request, "world_schema": schema_context,
               "blueprint": {"allowed_tables": tables,
                             "skill_contract": skill_contract(request["skill"], request["difficulty"])},
               "difficulty_rules": {"selected": rules["definitions"][request["difficulty"]],
                                    "principle": rules["principle"],
                                    "skill_classification": skill_line,
                                    "quality": rules["quality"].split("### 5.1.", 1)[-1]},
               "source_references": abstract_refs, "metadata_limitations": limitations,
               "rules_source": {"path": rules["path"], "sha256": rules["sha256"]}}
    return context, tables, [q["question_id"] for q in refs]


def build_prompt(context, feedback):
    request = context["user_request"]
    skill, difficulty = request["skill"], request["difficulty"]
    allowed = (context.get("blueprint") or {}).get("allowed_tables") or request.get("context_tables") or []
    # Physical usage is model-declared and name-checked; only parent IDs are assigned by code.
    fields = {"title": "...", "question": "...", "difficulty": difficulty, "primary_skill_group": skill,
              "skills": [skill], "business_domain": request.get("domain") or "one allowed_domains value",
              "business_goal": "...", "difficulty_reason": "...",
              "logic_signature": {"output_grain": "...", "analysis_goal": "...",
                                  "filter_pattern": "...", "aggregation_pattern": "..."},
              "tables_used": ["physical_table"], "required_columns": {"physical_table": ["physical_column"]},
              "table_roles": {"physical_table": "specific data this table supplies for this question"},
              "join_relations": [{"table_name": "child_table", "columns": ["fk_column"],
                                  "referenced_table": "parent_table", "referenced_columns": ["pk_column"]}],
              "output_columns": ["output_column_or_alias"]}
    world = dict(context.get("world_schema") or {})
    for noisy in ("business_rule_precedence", "business_rule_alignment_notes"):
        world.pop(noisy, None)
    world["business_rules"] = [{"code": r["code"], "title": r["title"]}
                               for r in (world.get("business_rules") or [])[:4]]
    body = {"world_schema": world}
    for key in ("difficulty_rules", "metadata_limitations"):
        if context.get(key):
            body[key] = context[key]
    body["source_references"] = [{"source_id": r["source_id"], "difficulty": r.get("difficulty"),
        "skill": r.get("skill"), "scope_compatible": r.get("scope_compatible", False),
        "analysis_pattern": (r.get("logic_pattern") or {}).get("transformation")
                            if isinstance(r.get("logic_pattern"), dict) else r.get("logic_pattern"),
        "goal_to_avoid": r.get("business_goal_to_avoid") if r.get("scope_compatible") else
                         "Outside this topic group: use only the abstract technique, never its business goal."}
        for r in context.get("source_references", [])]
    group = world.get("context_group")
    task = {k: request[k] for k in ("difficulty", "skill", "domain", "preferred_tables", "extra")
            if k in request}
    contract = [f"difficulty must be exactly '{difficulty}', primary_skill_group exactly '{skill}', "
                f"skills exactly ['{skill}'].",
                *skill_contract(skill, difficulty),
                "ALLOWED TABLES (nothing else): " + ", ".join(allowed) + ".",
                "Generate only the question and metadata. Do not include reference_sql, answer, solution code "
                "or SQL snippets in any field.",
                "tables_used contains ONLY physical tables needed by this question, not every context table.",
                "required_columns contains existing physical columns for exactly those tables; include columns "
                "needed for filters, joins and calculations. Put calculated aliases only in output_columns.",
                "table_roles explains why each declared table is needed. Do not add unused tables just to meet a count.",
                "join_relations must copy exact FK fields from world_schema.fk_relations, including all composite "
                "key columns. Include every join key in required_columns. The declared joins must connect all used tables."]
    if group:
        contract += [f"Topic is {group['domain']}. Scope: {group['focus']}",
                     f"Use {group['min_tables']}..{group['max_tables']} tables, including at least one of "
                     f"{group['primary_tables']}. Table count is a generation diversity policy, not difficulty proof."]
    if skill == "S1":
        contract.append("S1 uses only one physical table; join_relations must be [].")
    parts = [
        "You are SQLArena Model A. Output exactly ONE JSON object, no markdown.",
        "Write title/question/business_goal/difficulty_reason in Vietnamese. Do not write an SQL answer.",
        "TASK: " + json.dumps(task, ensure_ascii=False),
        "HARD CONTRACT (checked by code; a violation means the candidate is rejected):\n- " +
        "\n- ".join(contract),
        "QUALITY: Create a genuinely new business analysis goal, not a paraphrase, changed threshold/date/Top N, "
        "or mechanical merge of references. References are abstract inspiration; never implement a "
        "business_goal_to_avoid. Judge difficulty by the simplest reasonable solution. "
        "The question must specify output columns, NULL handling, ordering/ties and VND money semantics when relevant. "
        "For no aggregation/filter use the string 'none' in logic_signature. Do not invent policies or assume data "
        "values. Business-rule headings are summaries, not full policies. user_request.extra is a required "
        "constraint. Do not output source_question_ids; code assigns the five actual parents.",
        "CONTEXT:\n" + json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    ]
    if feedback:
        parts.append("PREVIOUS ATTEMPT FAILED. Apply every FIX line, then write a different candidate:\n" +
                     "\n".join("- " + line for line in feedback))
    parts.append("OUTPUT OBJECT (replace placeholders):\n" + json.dumps(fields, ensure_ascii=False))
    return "\n\n".join(parts)


def normalize_candidate(raw, schema, refs, context_tables, fk_relations=()):
    """Preserve declared tables/columns; no SQL or invented metadata fallback."""
    if not isinstance(raw, dict):
        return raw, {}
    declared = {k: raw[k] for k in ("tables_used", "required_columns", "source_question_ids") if k in raw}
    candidate = dict(raw)
    added = {}
    required = candidate.get("required_columns")
    tables, joins = candidate.get("tables_used"), candidate.get("join_relations")
    if isinstance(required, dict) and isinstance(tables, list) and isinstance(joins, list):
        required = {t: list(cols) if isinstance(cols, list) else cols for t, cols in required.items()}
        candidate["required_columns"] = required
        for relation in joins:
            fk = matching_fk(relation, fk_relations)
            if not fk or fk["table_name"] not in tables or fk["referenced_table"] not in tables:
                continue
            for table, columns in ((fk["table_name"], fk["columns"]),
                                   (fk["referenced_table"], fk["referenced_columns"])):
                if table not in context_tables or not isinstance(required.get(table), list):
                    continue
                for column in columns:
                    if column in schema.get(table, {}) and column not in required[table]:
                        required[table].append(column)
                        added.setdefault(table, []).append(column)
    candidate["source_question_ids"] = list(refs)
    note = {"declared_by_model": declared, "derived_from_sql": False,
            "set_by_code": ["source_question_ids"] + (["required_columns_join_keys"] if added else []),
            "join_keys_added_by_code": added}
    candidate["_normalization"] = note
    return candidate, note


def focus_columns(context, retry, size=3):
    names = [f"{t['table']}.{c['name']}" for t in (context.get("world_schema") or {}).get("tables", [])
             for c in t.get("columns", []) if not c["name"].endswith("_id")]
    if not names:
        return []
    start = (retry * size) % len(names)
    return [names[(start + i) % len(names)] for i in range(min(size, len(names)))]


def build_feedback(errors, local_request, context, tried_goals, retry):
    lines = list(errors) + ["FIX: Return only question/metadata, no reference_sql or SQL snippets. "
                          "Check physical tables/columns against world_schema; follow OUTPUT OBJECT.",
                          "Allowed tables are exactly: " + ", ".join(local_request["context_tables"])]
    group = local_request.get("context_group")
    if group:
        lines.append(f"FIX: Stay in topic {group['domain']}: {group['focus']}; use "
                     f"{group['min_tables']}..{group['max_tables']} genuinely needed tables. "
                     "Supply table_roles and real connected join_relations; include FK columns in required_columns.")
    if tried_goals:
        lines.append("Goals already tried and rejected (pick a clearly different entity and measure): " +
                     json.dumps(tried_goals, ensure_ascii=False))
    focus = focus_columns(context, retry)
    if focus:
        lines.append("Suggested new focus columns: " + ", ".join(focus))
    return lines


def ollama_request(config, path, body=None):
    url = config["OLLAMA_HOST"].rstrip("/") + path
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=config["OLLAMA_TIMEOUT_SECONDS"]) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Ollama HTTP {exc.code}: {exc.read(1000).decode(errors='replace')}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError("Ollama khong phan hoi/timeout. Khoi dong Ollama (ollama serve) va kiem tra host.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Ollama tra HTTP JSON khong hop le.") from exc
    if not isinstance(result, dict) or result.get("error"):
        raise ValueError(f"Loi Ollama: {result.get('error') if isinstance(result, dict) else 'not object'}")
    return result


def question_output_schema():
    string = {"type": "string", "minLength": 1}
    strings = {"type": "array", "items": string, "minItems": 1}
    signature = {k: string for k in ("output_grain", "analysis_goal", "filter_pattern", "aggregation_pattern")}
    relation = {"table_name": string, "columns": strings, "referenced_table": string, "referenced_columns": strings}
    properties = {k: string for k in ("title", "question", "business_domain", "business_goal", "difficulty_reason")}
    properties.update({"difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "primary_skill_group": {"type": "string", "enum": [f"S{i}" for i in range(1, 7)]},
        "skills": strings, "tables_used": strings, "output_columns": strings,
        "required_columns": {"type": "object", "additionalProperties": strings},
        "table_roles": {"type": "object", "additionalProperties": string},
        "logic_signature": {"type": "object", "properties": signature, "required": list(signature), "additionalProperties": False},
        "join_relations": {"type": "array", "items": {"type": "object", "properties": relation,
            "required": list(relation), "additionalProperties": False}}})
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def generate(config, prompt, smoke=False):
    result = ollama_request(config, "/api/generate", {"model": config["MODEL_NAME"], "prompt": prompt,
        "stream": False, "format": "json" if smoke else question_output_schema(), "options": {"num_ctx": config["OLLAMA_CONTEXT_SIZE"],
        "num_predict": 64 if smoke else 1200, "temperature": 0 if smoke else .35}})
    if not result.get("done", True) or result.get("done_reason") == "length":
        raise ValueError("Ollama dung vi gioi han token; JSON/SQL co the bi cat. Giam context/do dai cau.")
    if result.get("prompt_eval_count", 0) >= config["OLLAMA_CONTEXT_SIZE"] - 128:
        raise ValueError("Context gan/vuot cua so model; khong chap nhan de khi prompt co the bi cat.")
    try:
        obj = json.loads(result["response"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Model tra response khong phai JSON hop le.") from exc
    if not isinstance(obj, dict):
        raise ValueError("Model phai tra JSON object.")
    if not smoke:
        obj["_generation_metrics"] = {k: result.get(k) for k in
            ("prompt_eval_count", "eval_count", "total_duration", "prompt_eval_duration", "eval_duration")}
    return obj


def check_ollama(config):
    tags = ollama_request(config, "/api/tags")
    desired = config["MODEL_NAME"]
    names = {m["name"] for m in tags.get("models", [])}
    if desired not in names and desired + ":latest" not in names:
        raise ValueError(f"Model {desired} chua cai. Tu chay: ollama pull {desired}. Khong tu tai model.")
    smoke = generate(config, 'Return exactly {"ok":true}.', smoke=True)
    if smoke != {"ok": True}:
        raise ValueError(f"Ollama JSON smoke khong dat: {smoke}")
    return {"available": True, "installed_models": sorted(names), "json_smoke": smoke}


def fingerprint(config, data):
    snapshot = {"core": {}, "enterprise": {}, "enterprise_catalog": None}
    with connect(config, "ARENA") as conn:
        for table in ("worlds", "skills", "templates", "source_questions"):
            row = conn.execute(f"SELECT count(*) AS count,md5(coalesce(string_agg(h,'' ORDER BY h),'')) AS hash "
                               f"FROM (SELECT md5(row_to_json(t)::text) h FROM core.{table} t) x").fetchone()
            snapshot["core"][table] = row
    with connect(config, "CATALOG") as conn:
        for table in sorted(data["schema"]):
            query = psycopg.sql.SQL("SELECT count(*) AS count,md5(coalesce(string_agg(h,'' ORDER BY h),'')) AS hash "
                                    "FROM (SELECT md5(row_to_json(t)::text) h FROM public.{} t) x").format(
                                        psycopg.sql.Identifier(table))
            snapshot["enterprise"][table] = conn.execute(query).fetchone()
        rows = conn.execute("SELECT n.nspname,c.relname,a.attname,format_type(a.atttypid,a.atttypmod) type," 
                            "a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid) default_expression "
                            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "JOIN pg_attribute a ON a.attrelid=c.oid LEFT JOIN pg_attrdef d "
                            "ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='public' "
                            "AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum").fetchall()
        constraints = conn.execute("SELECT c.relname,k.conname,pg_get_constraintdef(k.oid) definition "
                                   "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid "
                                   "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
                                   "ORDER BY c.relname,k.conname").fetchall()
        snapshot["enterprise_catalog"] = hashlib.sha256(json.dumps(
            [rows, constraints], sort_keys=True, default=str).encode()).hexdigest()
    return snapshot


def render_schema_text(world_schema, tables_used):
    definitions = {t["table"]: t for t in world_schema["tables"]}
    sections = []
    for name in sorted(tables_used):
        lines = [f"public.{name}"]
        for c in definitions[name]["columns"]:
            lines.append(f"  - {c['name']}: {c['type']} {'NULL' if c['nullable'] else 'NOT NULL'}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def insert_draft(config, data, candidate, report, context, references, retry_count):
    schema_context = {**context["world_schema"], "tables_used": candidate["tables_used"],
                      "required_columns": candidate["required_columns"],
                      "rules_source": context["rules_source"]}
    values = {"world_id": data["world"]["world_id"], "question": candidate["question"],
              "compare_mode": "unordered",
              "difficulty": candidate["difficulty"], "skills": Jsonb(candidate["skills"]),
              "traps": Jsonb([]), "parent_ids": Jsonb(references), "depth": 1, "status": "pending",
              "gen_model": config["MODEL_NAME"], "gen_prompt_version": PROMPT_VERSION,
              "retry_count": retry_count, "schema_context": Jsonb(schema_context),
              "schema_text": render_schema_text(context["world_schema"], candidate["tables_used"]),
              "validation_report": Jsonb(report)}
    statement = psycopg.sql.SQL("INSERT INTO draft.question_drafts ({}) VALUES ({}) RETURNING draft_id").format(
        psycopg.sql.SQL(",").join(map(psycopg.sql.Identifier, DRAFT_FIELDS)),
        psycopg.sql.SQL(",").join(psycopg.sql.Placeholder() for _ in DRAFT_FIELDS))
    with connect(config, "ARENA", readonly=False) as conn:
        draft_id = conn.execute(statement, [values[f] for f in DRAFT_FIELDS]).fetchone()["draft_id"]
    # Context manager has committed before announcing success.
    return draft_id


def create_output():
    folder = HERE / "outputs"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for suffix in range(10000):
        path = folder / f"generation_{stamp}{'_' + str(suffix) if suffix else ''}.json"
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write("{}\n")
            return path
        except FileExistsError:
            continue
    raise ValueError("Khong tao duoc ten output rieng.")


def checkpoint(path, session):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(session, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def run_session(config, data, rules, request, output, dry_run=False):
    session = {"prompt_version": PROMPT_VERSION, "started_at": datetime.now().astimezone().isoformat(),
               "input": request, "rules_source": {"path": rules["path"], "sha256": rules["sha256"]},
               "configuration": {k: config[k] for k in ("MODEL_NAME", "OLLAMA_HOST", "MAX_RETRIES",
                   "STATEMENT_TIMEOUT_MS", "DUPLICATE_HIGH", "DUPLICATE_REVIEW")},
               "successes": [], "failures": [], "status": "running", "dry_run": dry_run}
    before = fingerprint(config, data)
    session["before_fingerprint"] = before
    checkpoint(output, session)
    corpus = corpus_from(data)
    try:
        for index in range(request["count"]):
            context, tables, refs = build_context(data, rules, request, index)
            local_request = {**request, "context_tables": tables,
                             "context_group": context["world_schema"].get("context_group"),
                             "fk_relations": context["world_schema"].get("fk_relations", [])}
            print("Context: " + context["user_request"].get("domain", "") + " | " + ", ".join(tables), flush=True)
            attempts, feedback, tried_goals = [], [], []
            for retry in range(config["MAX_RETRIES"] + 1):
                print(f"Câu {index+1}/{request['count']}, lần {retry+1}: gọi {config['MODEL_NAME']}...", flush=True)
                candidate = None
                try:
                    raw = generate(config, build_prompt(context, feedback))
                    candidate, _ = normalize_candidate(raw, data["schema"], refs, tables, local_request["fk_relations"])
                    report = validate_question(candidate, local_request, data["schema"], refs, corpus,
                                               config["DUPLICATE_HIGH"], config["DUPLICATE_REVIEW"])
                    attempts.append({"retry_count": retry, "candidate": candidate, "validation": report})
                    goal = candidate.get("business_goal") if isinstance(candidate, dict) else None
                    if isinstance(goal, str) and goal and goal not in tried_goals:
                        tried_goals.append(goal)
                    if not report["passed_basic"]:
                        feedback = build_feedback(report["errors"], local_request, context, tried_goals, retry + 1)
                        print("Chưa đạt: " + "; ".join(report["errors"]), flush=True)
                        continue
                    # Refresh existing Drafts before insert so other runs are not ignored.
                    fresh = inspect_database(config, rules)
                    if fresh["blockers"]:
                        raise ValueError("; ".join(fresh["blockers"]))
                    fresh_corpus = corpus_from(fresh) + [q for q in corpus if q.get("origin") == "session"]
                    report = validate_question(candidate, local_request, data["schema"], refs, fresh_corpus,
                                               config["DUPLICATE_HIGH"], config["DUPLICATE_REVIEW"])
                    attempts[-1]["validation"] = report
                    if not report["passed_basic"]:
                        feedback = build_feedback(report["errors"], local_request, context, tried_goals, retry + 1)
                        continue
                    try:
                        draft_id = None if dry_run else insert_draft(config, data, candidate, report, context, refs, retry)
                    except psycopg.Error as exc:
                        attempts[-1]["insert_error"] = f"{exc.sqlstate}: {exc}"
                        # Do not regenerate and risk a second insert after ambiguous connection failure.
                        print("INSERT thất bại/chưa xác nhận commit. Kiểm tra Draft; không tự insert lại.", flush=True)
                        break
                    session["successes"].append({"slot": index+1, "draft_id": draft_id,
                        "status": "dry_run" if dry_run else "pending", "candidate": candidate, "reference_ids": refs,
                        "schema_context": {**context["world_schema"], "tables_used": candidate["tables_used"],
                                           "required_columns": candidate["required_columns"]},
                        "schema_text": render_schema_text(context["world_schema"], candidate["tables_used"]),
                        "validation": report, "retry_count": retry, "attempts": attempts})
                    corpus.append({**candidate, "id": draft_id, "origin": "session"})
                    print(("Dry-run, không INSERT" if dry_run else f"Đã lưu Draft {draft_id}, pending") +
                          "; chỉ sinh đề/metadata, không sinh đáp án SQL; cần người duyệt.", flush=True)
                    break
                except (ValueError, psycopg.Error) as exc:
                    feedback = build_feedback([str(exc)], local_request, context, tried_goals, retry + 1)
                    attempts.append({"retry_count": retry, "candidate": candidate, "errors": [str(exc)]})
                    print("Lỗi: " + str(exc), flush=True)
                finally:
                    session["current_slot"] = {"slot": index+1, "reference_ids": refs, "attempts": attempts}
                    checkpoint(output, session)
            else:
                pass
            if not any(q["slot"] == index+1 for q in session["successes"]):
                session["failures"].append({"slot": index+1, "reference_ids": refs, "attempts": attempts})
            session.pop("current_slot", None)
            checkpoint(output, session)
        session["status"] = "completed" if len(session["successes"]) == request["count"] else "partial"
    except KeyboardInterrupt:
        session["status"] = "interrupted"
    except Exception as exc:
        session["status"] = "error"
        session["session_error"] = str(exc)
    finally:
        try:
            after = fingerprint(config, data)
            session["after_fingerprint"] = after
            session["protected_data_unchanged"] = before == after
            if before != after:
                session["status"] = "protected_data_changed_requires_investigation"
        except psycopg.Error as exc:
            session["protected_data_unchanged"] = None
            session["fingerprint_error"] = str(exc)
        session["finished_at"] = datetime.now().astimezone().isoformat()
        checkpoint(output, session)
    session["saved_count"] = sum(q["draft_id"] is not None for q in session["successes"])
    checkpoint(output, session)
    print(f"\nĐạt sơ bộ {len(session['successes'])}/{request['count']}; đã lưu {session['saved_count']} câu pending. JSON: {output}")
    return session


def main(argv=None):
    args = argparse.ArgumentParser(description="SQLArena Model A v1")
    args.add_argument("--check", action="store_true", help="Chi kiem tra Rules/Core/Draft/Ollama, khong sinh/insert")
    args.add_argument("--dry-run", action="store_true", help="Sinh de/metadata, khong INSERT Draft")
    options = args.parse_args(argv)
    try:
        config = load_config()
        rules = read_rules(config)
        data = inspect_database(config, rules)
        print(f"Pipeline: {PROMPT_VERSION} (chỉ sinh đề và metadata, không sinh đáp án SQL).")
        print(f"Rules: {rules['path']}\nCore: {len(data['sources'])} câu, {len(data['skills'])} kỹ năng, "
              f"{len(data['schema'])} bảng Enterprise.")
        for blocker in data["blockers"]:
            print("Chặn sinh: " + blocker)
        check_ollama(config)
        print(f"Ollama: {config['MODEL_NAME']}, JSON smoke OK.")
        if options.check:
            return 1 if data["blockers"] else 0
        if data["blockers"]:
            return 1
        request = prompt_input(data, feasible=feasible_pairs(rules))
        if request is None:
            print("Đã hủy. Không sinh và không INSERT.")
            return 0
        check_feasible(rules, request)
        if len([q for q in data["sources"] if q["difficulty"] == request["difficulty"]]) < 5:
            raise ValueError("Khong du nam cau nguon cung difficulty.")
        output = create_output()
        result = run_session(config, data, rules, request, output, dry_run=options.dry_run)
        return 0 if result["status"] == "completed" else 1
    except (ValueError, psycopg.Error, OSError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nĐã dừng nhập liệu. Không sinh thêm.")
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
