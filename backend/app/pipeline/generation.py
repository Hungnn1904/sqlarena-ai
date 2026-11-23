"""Giai đoạn sinh đề (Model A) chạy trong worker: planner/context → Model A → JSON/Blueprint gate (validator) → draft `pending`.

Logic sinh/kiểm tra là của engine `ai/main.py` + `ai/validator.py`; module này chỉ điều phối theo job:
lease/heartbeat, fencing khi ghi draft, ghi ledger, đếm created/failed, và dừng khi hết ngân sách/Ollama hỏng.
"""
import json
import logging

from ..db import begin, ex, q, q1
from ..domain import DIFF_NAME, DIFF_NUM
from ..services import settings_registry as sr
from . import engine as eng
from .catalog import load_engine_data, verify_catalog
from .leases import Heartbeat, LeaseLost

log = logging.getLogger("generation")
arena, vd = eng.arena, eng.vd


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _is_infra_error(message: str) -> bool:
    return message.startswith(("Ollama", "Loi Ollama"))


def normalize_candidate_for_validation(candidate, world_schema: dict | None):
    """Tự động bổ sung table_roles mặc định và cột khóa ngoại nối giữa các bảng trong tables_used
    nếu Model A quên liệt kê (nhưng KHÔNG tự bịa nếu thiếu các trường gốc bắt buộc)."""
    if not isinstance(candidate, dict):
        return candidate
    tables_used = candidate.get("tables_used")
    question = candidate.get("question")
    title = candidate.get("title")
    if (
        not isinstance(tables_used, list)
        or not tables_used
        or not isinstance(question, str)
        or not question.strip()
        or not isinstance(title, str)
        or not title.strip()
    ):
        return candidate

    out = dict(candidate)
    ws = world_schema or {}
    schema_cols = {
        t["table"]: {c["name"] for c in t.get("columns", [])}
        for t in ws.get("tables", [])
        if isinstance(t, dict) and "table" in t
    }

    # 1. Bổ sung table_roles mặc định cho các bảng trong tables_used nếu thiếu
    raw_roles = out.get("table_roles")
    roles = dict(raw_roles) if isinstance(raw_roles, dict) else {}
    for tbl in tables_used:
        if isinstance(tbl, str) and tbl in schema_cols and not str(roles.get(tbl) or "").strip():
            roles[tbl] = f"Bảng dữ liệu {tbl} dùng trong truy vấn"
    out["table_roles"] = roles

    # 2. Bổ sung join_relations và cột FK trong required_columns giữa các bảng trong tables_used
    used = [t for t in tables_used if isinstance(t, str) and t in schema_cols]
    used_set = set(used)
    fks = [
        fk for fk in (ws.get("fk_relations") or [])
        if isinstance(fk, dict)
        and fk.get("table_name") in used_set
        and fk.get("referenced_table") in used_set
    ]
    raw_joins = out.get("join_relations")
    joins = [dict(j) for j in raw_joins if isinstance(j, dict)] if isinstance(raw_joins, list) else []

    if len(used_set) >= 2 and fks:
        # Xây đồ thị thành phần liên thông hiện tại của joins để chỉ bù những cạnh nối còn thiếu
        parent = {t: t for t in used}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> bool:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent[rb] = ra
            return True

        for rel in joins:
            tn, rt = rel.get("table_name"), rel.get("referenced_table")
            if tn in parent and rt in parent:
                union(tn, rt)

        for fk in fks:
            if union(fk["table_name"], fk["referenced_table"]):
                joins.append({
                    "table_name": fk["table_name"],
                    "columns": list(fk["columns"]),
                    "referenced_table": fk["referenced_table"],
                    "referenced_columns": list(fk["referenced_columns"]),
                })
    out["join_relations"] = joins

    raw_req = out.get("required_columns")
    if isinstance(raw_req, dict):
        req = {t: list(cols) if isinstance(cols, list) else cols for t, cols in raw_req.items()}
        for t in used:
            if t not in req or not isinstance(req[t], list):
                req[t] = []
        for rel in joins:
            fk = arena.matching_fk(rel, fks)
            if not fk:
                continue
            for tbl, cols in ((fk["table_name"], fk["columns"]), (fk["referenced_table"], fk["referenced_columns"])):
                if tbl in req and isinstance(req[tbl], list):
                    for col in cols:
                        if col in schema_cols.get(tbl, set()) and col not in req[tbl]:
                            req[tbl].append(col)
        out["required_columns"] = req
    return out


class GenerationRunner:
    def __init__(self, config: dict, worker_id: str):
        self.config, self.worker_id = config, worker_id

    # ------------------------------------------------------------------ job
    def run_job(self, job: dict) -> str:
        """Trả về trạng thái cuối: done | failed. Ném LeaseLost nếu mất quyền (kết quả bị bỏ)."""
        with begin() as conn:
            lease_s, hb_s = sr.get(conn, "generation.lease_seconds"), sr.get(conn, "generation.heartbeat_seconds")
            world = q1(conn, "SELECT name FROM core.worlds WHERE world_id=:w", w=job["world_id"])
        try:
            with begin() as conn:
                data = load_engine_data(conn, world["name"])
                existing_drafts = int(
                    q1(conn, "SELECT COUNT(*) AS n FROM draft.question_drafts WHERE world_id=:w", w=job["world_id"])["n"]
                )
            verify_catalog(self.config, data)
            rules = arena.read_rules(self.config)
        except ValueError as exc:
            return self._finish(job, "failed", f"config: {exc}")
        code_of = data["skill_code"]
        feasible = arena.feasible_pairs(rules)
        diff = DIFF_NAME[job["difficulty"]]
        skills = [code_of[s] for s in job["skill_ids"] if s in code_of and diff in feasible.get(code_of[s], {diff})]
        if not skills:
            return self._finish(job, "failed", f"Rules không định nghĩa kỹ năng đã chọn ở độ khó {diff}")
        domains = sorted({s["primary_business_domain"] for s in data["sources"]})
        topic = (job["topic"] or "").strip()
        domain = next((d for d in domains if d.casefold() == topic.casefold()), None) if topic else None
        extra = topic if topic and not domain else ""

        slot_offset = max(existing_drafts, max(0, int(job.get("job_id") or 1) - 1))
        infra_streak = 0
        with Heartbeat("job", job["job_id"], self.worker_id, job["lease_version"], lease_s, hb_s) as hb:
            while True:
                hb.check()
                done = job["created_count"] + job["failed_count"]
                if done >= job["requested_count"]:
                    break
                slot_index = slot_offset + done
                request = {"count": 1, "difficulty": diff, "skill": skills[done % len(skills)], "domain": domain,
                           "preferred_tables": [], "extra": extra, "allowed_domains": domains,
                           "allowed_skills": [s["skill_id"] for s in data["skills"]]}
                try:
                    outcome = self._generate_slot(job, data, rules, request, slot_index)
                except eng.BudgetExceeded as exc:
                    return self._finish(job, "failed", f"budget: {exc}")
                if outcome["ok"]:
                    infra_streak = 0
                    created = self._insert_draft(job, data, outcome)
                    job["created_count"] += created
                else:
                    infra_streak = infra_streak + 1 if outcome["infra"] else 0
                    self._bump(job, "failed_count")
                    job["failed_count"] += 1
                    if infra_streak >= 2:
                        return self._finish(job, "failed", f"system: AI Gateway / Model A không phản hồi — {outcome['error'][:300]}")
        return self._finish(job, "done", None)

    # ------------------------------------------------------------------ slot
    def _generate_slot(self, job: dict, data: dict, rules: dict, request: dict, index: int) -> dict:
        cfg = self.config
        context, tables, refs = arena.build_context(data, rules, request, index)
        local = {**request, "context_tables": tables, "context_group": context["world_schema"].get("context_group"),
                 "fk_relations": context["world_schema"].get("fk_relations", [])}
        with begin() as conn:                         # corpus mới nhất để phát hiện trùng với draft của job khác
            drafts = q(conn, "SELECT draft_id, question, validation_report FROM draft.question_drafts WHERE world_id=:w ORDER BY draft_id",
                       w=data["world"]["_pk"])
        corpus = arena.corpus_from({**data, "drafts": drafts})
        feedback, tried, last_error, infra = [], [], "", False
        for retry in range(cfg["MAX_RETRIES"] + 1):
            candidate = None
            try:
                with eng.llm_context(job_id=job["job_id"], draft_id=None, stage="model_a", prompt_name="model_a",
                                     prompt_version=arena.PROMPT_VERSION, attempt_no=retry + 1):
                    raw = arena.generate(cfg, arena.build_prompt(context, feedback))
                candidate, _ = arena.normalize_candidate(raw, data["schema"], refs, tables, local["fk_relations"])
                candidate = normalize_candidate_for_validation(candidate, context.get("world_schema"))
                report = vd.validate_question(candidate, local, data["schema"], refs, corpus, cfg["DUPLICATE_HIGH"], cfg["DUPLICATE_REVIEW"])
                goal = candidate.get("business_goal") if isinstance(candidate, dict) else None
                if isinstance(goal, str) and goal and goal not in tried:
                    tried.append(goal)
                if report["passed_basic"]:
                    return {"ok": True, "candidate": candidate, "report": report, "context": context, "refs": refs, "retry": retry}
                last_error = "; ".join(report["errors"])
                feedback = arena.build_feedback(report["errors"], local, context, tried, retry + 1)
            except eng.BudgetExceeded:
                raise
            except ValueError as exc:
                last_error = str(exc)
                infra = _is_infra_error(last_error)
                feedback = arena.build_feedback([last_error], local, context, tried, retry + 1)
                if infra:
                    break                              # đừng đốt ngân sách khi model/Ollama đang hỏng
        return {"ok": False, "infra": infra, "error": last_error or "không đạt kiểm tra sơ bộ"}

    # ------------------------------------------------------------------ writes (fenced)
    def _fence_sql(self) -> str:
        return "job_id=:id AND status='running' AND locked_by=:w AND lease_version=:v"

    def _bump(self, job: dict, column: str) -> None:
        with begin() as conn:
            n = ex(conn, f"UPDATE draft.generation_jobs SET {column} = {column} + 1 WHERE {self._fence_sql()} "
                         "AND created_count + failed_count < requested_count",
                   id=job["job_id"], w=self.worker_id, v=job["lease_version"])
            if n == 0:
                raise LeaseLost(f"job {job['job_id']}")

    def _insert_draft(self, job: dict, data: dict, outcome: dict) -> int:
        from ..services.draft_dossier import derive_pedagogical_traps

        cand, report, ctx = outcome["candidate"], outcome["report"], outcome["context"]
        codes = [c for c in dict.fromkeys([cand.get("primary_skill_group"), *cand.get("skills", [])]) if c in data["skill_pk"]]
        schema_context = {**ctx["world_schema"], "tables_used": cand["tables_used"], "required_columns": cand["required_columns"],
                          "rules_source": ctx["rules_source"]}
        blueprint = {"source_question_ids": outcome["refs"], "context_group": ctx["world_schema"].get("context_group"),
                     "skill_contract": ctx["blueprint"]["skill_contract"], "candidate": cand}
        traps = derive_pedagogical_traps(cand, ctx.get("world_schema"))
        with begin() as conn:
            n = ex(conn, f"UPDATE draft.generation_jobs SET created_count = created_count + 1 WHERE {self._fence_sql()} "
                         "AND created_count + failed_count < requested_count", id=job["job_id"], w=self.worker_id, v=job["lease_version"])
            if n == 0:
                raise LeaseLost(f"job {job['job_id']}")
            ex(conn, """INSERT INTO draft.question_drafts (world_id, job_id, title, question, difficulty, skill_ids, blueprint, tables_used,
                        traps, schema_text, schema_context, validation_report, status, gen_model, gen_prompt_version, retry_count)
                        VALUES (:w, :job, :t, :q, :d, :sk, CAST(:bp AS jsonb), :tu, CAST(:tr AS jsonb), :st, CAST(:sc AS jsonb),
                                CAST(:vr AS jsonb), 'pending', :gm, :gv, :rc)""",
               w=data["world"]["_pk"], job=job["job_id"], t=str(cand["title"])[:200], q=cand["question"],
               d=DIFF_NUM[cand["difficulty"]], sk=[data["skill_pk"][c] for c in codes], bp=_j(blueprint), tu=list(cand["tables_used"]),
               tr=_j(traps), st=arena.render_schema_text(ctx["world_schema"], cand["tables_used"]), sc=_j(schema_context), vr=_j(report),
               gm=self.config["MODEL_NAME"], gv=arena.PROMPT_VERSION, rc=outcome["retry"])
        return 1

    def _finish(self, job: dict, status: str, message: str | None) -> str:
        with begin() as conn:
            n = ex(conn, f"""UPDATE draft.generation_jobs SET status=:s, error_message=:m, finished_at=now(), locked_by=NULL,
                             lease_expires_at=NULL WHERE {self._fence_sql()}""",
                   s=status, m=message, id=job["job_id"], w=self.worker_id, v=job["lease_version"])
            if n == 0:
                raise LeaseLost(f"job {job['job_id']}")
        return status
