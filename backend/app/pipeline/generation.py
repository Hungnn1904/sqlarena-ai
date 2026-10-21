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

        infra_streak = 0
        with Heartbeat("job", job["job_id"], self.worker_id, job["lease_version"], lease_s, hb_s) as hb:
            while True:
                hb.check()
                done = job["created_count"] + job["failed_count"]
                if done >= job["requested_count"]:
                    break
                index = done
                request = {"count": 1, "difficulty": diff, "skill": skills[index % len(skills)], "domain": domain,
                           "preferred_tables": [], "extra": extra, "allowed_domains": domains,
                           "allowed_skills": [s["skill_id"] for s in data["skills"]]}
                try:
                    outcome = self._generate_slot(job, data, rules, request, index)
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
                        return self._finish(job, "failed", f"system: Ollama/Model A không phản hồi — {outcome['error'][:300]}")
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
        cand, report, ctx = outcome["candidate"], outcome["report"], outcome["context"]
        codes = [c for c in dict.fromkeys([cand.get("primary_skill_group"), *cand.get("skills", [])]) if c in data["skill_pk"]]
        schema_context = {**ctx["world_schema"], "tables_used": cand["tables_used"], "required_columns": cand["required_columns"],
                          "rules_source": ctx["rules_source"]}
        blueprint = {"source_question_ids": outcome["refs"], "context_group": ctx["world_schema"].get("context_group"),
                     "skill_contract": ctx["blueprint"]["skill_contract"], "candidate": cand}
        with begin() as conn:
            n = ex(conn, f"UPDATE draft.generation_jobs SET created_count = created_count + 1 WHERE {self._fence_sql()} "
                         "AND created_count + failed_count < requested_count", id=job["job_id"], w=self.worker_id, v=job["lease_version"])
            if n == 0:
                raise LeaseLost(f"job {job['job_id']}")
            ex(conn, """INSERT INTO draft.question_drafts (world_id, job_id, title, question, difficulty, skill_ids, blueprint, tables_used,
                        traps, schema_text, schema_context, validation_report, status, gen_model, gen_prompt_version, retry_count)
                        VALUES (:w, :job, :t, :q, :d, :sk, CAST(:bp AS jsonb), :tu, '[]'::jsonb, :st, CAST(:sc AS jsonb),
                                CAST(:vr AS jsonb), 'pending', :gm, :gv, :rc)""",
               w=data["world"]["_pk"], job=job["job_id"], t=str(cand["title"])[:200], q=cand["question"],
               d=DIFF_NUM[cand["difficulty"]], sk=[data["skill_pk"][c] for c in codes], bp=_j(blueprint), tu=list(cand["tables_used"]),
               st=arena.render_schema_text(ctx["world_schema"], cand["tables_used"]), sc=_j(schema_context), vr=_j(report),
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
