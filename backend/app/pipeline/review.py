"""Giai đoạn kiểm duyệt (Model B) trong worker: claim draft → Model B giải k lần → guard/consensus/semantic audit (engine ai/review.py)
→ fenced commit: approved ⇒ promote sang live.questions + test_cases trong CÙNG transaction.

Fail-closed: thiếu bằng chứng/lỗi hạ tầng không bao giờ thành approved. Lỗi hạ tầng/ngân sách trả draft về `pending`.
"""
import json
import logging

from ..db import begin, ex, q, q1
from ..domain import DIFF_NAME
from ..services import promotion, queue
from ..services import settings_registry as sr
from . import engine as eng
from .catalog import load_engine_data, verify_catalog
from .leases import Heartbeat, LeaseLost

log = logging.getLogger("review")
rv = eng.rv

# Lý do "cần phán đoán của người" mà admin được phép xác nhận khi approve. Mọi lý do khác là mandatory gate: KHÔNG ai bỏ qua được.
ADMIN_OVERRIDABLE = {
    "empty_result", "output_columns_mismatch", "order_tiebreaker_missing", "subquery_alias_shadowing", "hardcoded_id_literal",
    "tables_mismatch", "unstated_string_literal", "suspected_duplicate", "one_to_many_join_may_duplicate_output_grain",
    "month_output_must_be_date", "semantic_audit_flagged", "consensus_disagreement", "order_disagreement", "insufficient_valid_solutions",
    "skill_s1_has_forbidden_features", "skill_s2_no_join", "skill_s3_no_aggregate", "skill_s4_no_subquery", "skill_s5_no_cte_or_window",
    "skill_s6_no_recursion_or_layers", "difficulty_easy_exceeded", "no_valid_solution",
}


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def engine_row(draft: dict, data: dict) -> dict:
    """Draft (schema ứng dụng) → dòng mà rv.draft_context() hiểu (skills = mã S1.., difficulty = easy/medium/hard)."""
    code_of = data["skill_code"]
    return {"draft_id": draft["draft_id"], "question": draft["question"], "difficulty": DIFF_NAME[draft["difficulty"]],
            "skills": [code_of[s] for s in draft["skill_ids"] if s in code_of],
            "parent_ids": (draft["blueprint"] or {}).get("source_question_ids", []),
            "schema_context": draft["schema_context"], "validation_report": draft["validation_report"], "schema_text": draft["schema_text"]}


def build_context(draft: dict, data: dict, fewshot: int) -> dict:
    ctx = rv.draft_context(engine_row(draft, data))
    pool = [s for s in data["sources"] if s["reference_sql"] and s["question_text"]]
    ctx["examples"] = rv.pick_examples(pool, ctx, fewshot, set(ctx["parent_ids"])) if fewshot else []
    return ctx


def log_rows(config: dict, result: dict, datasets: list, sample_rows: list[dict]) -> list[tuple]:
    """Kết quả engine → các dòng draft.review_logs (stage theo v7 + 'semantic_audit' + 'decision')."""
    stages, rows = result["stages"], []
    models = ",".join(config["REVIEW_MODELS"])
    info = [{"ref": d.ref, "version": d.version} for d in datasets]

    def add(stage, passed, reasons, raw, score=None):
        rows.append((stage, bool(passed), score, reasons, models, _j({"review_version": rv.REVIEW_VERSION, **raw})))

    add("code_check", stages["pre"]["passed"], stages["pre"]["reasons"], {"phase": "pre"})
    if "solve" in stages:
        k = stages["solve"]["k"]
        add("solve", stages["solve"]["passed"], [] if stages["solve"]["passed"] else ["not_all_samples_valid"],
            {"samples": [{k2: v for k2, v in r.items() if k2 != "sql"} for r in sample_rows], "datasets": info, "models": config["REVIEW_MODELS"]},
            round(100 * stages["solve"]["valid"] / k, 2))
    if "post" in stages:
        add("code_check", stages["post"]["passed"], stages["post"]["reasons"], {"phase": "post", "features": stages["post"]["features"], "notes": result["notes"]})
    if "semantic_audit" in stages:
        a = stages["semantic_audit"]
        add("semantic_audit", a["passed"], a.get("issues", []), {"verdict": a.get("verdict"), "issues": a.get("issues", []), "checks": a.get("checks", [])})
    rep = stages.get("repair") or {}
    if rep.get("attempted"):
        add("code_check", rep.get("approved_after_repair"), [] if rep.get("approved_after_repair") else ["repair_did_not_reach_approval"], {"phase": "repair", **rep})
    if result["testcases"]:
        add("test_case", True, [], {"datasets": [{"ref": t["dataset_ref"], "rows": t["row_count"], "hash": t["result_hash"]} for t in result["testcases"]]})
    add("decision", result["status"] == "approved", result["reasons"], {"status": result["status"], "mode": result["mode"], "datasets": info})
    return rows


def write_review_records(conn, draft: dict, config: dict, result: dict, datasets: list, round_no: int) -> None:
    sample_rows = rv.sample_rows(result, config["REVIEW_MODELS"][0])
    for r in sample_rows:
        ex(conn, """INSERT INTO draft.self_solve_runs (draft_id, sample_index, model_sql, is_selected, matched_datasets, total_datasets, mismatch_detail,
                    exec_status, row_count, result_hash, error, review_model, review_round)
                    VALUES (:d, :i, :sql, :sel, :m, :t, CAST(:md AS jsonb), :es, :rc, :h, :e, :rm, :rr)
                    ON CONFLICT (draft_id, review_round, sample_index) DO NOTHING""",
           d=draft["draft_id"], i=r["sample_index"], sql=r["sql"], sel=r["is_selected"], m=len(r["matched"]), t=len(datasets),
           md=_j(r["mismatch"]) if r["mismatch"] else None, es=r["exec_status"], rc=r["row_count"], h=r["hash"], e=r["error"],
           rm=r["model"], rr=round_no)
    for stage, passed, score, reasons, model, raw in log_rows(config, result, datasets, sample_rows):
        ex(conn, """INSERT INTO draft.review_logs (draft_id, stage, passed, score, reasons, review_model, rubric_version, raw_output)
                    VALUES (:d, :s, :p, :sc, CAST(:r AS jsonb), :m, :rv, :raw)""",
           d=draft["draft_id"], s=stage, p=passed, sc=score, r=_j(reasons), m=model, rv=rv.REVIEW_VERSION, raw=raw)


def commit_result(draft: dict, config: dict, result: dict, datasets: list, world_dataset_version: int, actor: str) -> dict:
    """Ghi kết quả bằng cập nhật có điều kiện theo fencing token; approved ⇒ promote cùng transaction."""
    status = result["status"]
    reason = ", ".join(result["reasons"])[:500] or None
    with begin() as conn:
        if status == "approved":
            n = ex(conn, """UPDATE draft.question_drafts SET status='approved', reference_sql=:sql, compare_mode=:m, status_reason=NULL,
                            locked_by=NULL, review_lease_expires_at=NULL, updated_at=now()
                            WHERE draft_id=:id AND status='reviewing' AND locked_by=:w AND review_lease_version=:v""",
                   sql=result["reference_sql"], m=result["mode"], id=draft["draft_id"], w=draft["locked_by"], v=draft["review_lease_version"])
        else:
            n = ex(conn, """UPDATE draft.question_drafts SET status=:s, status_reason=:r, locked_by=NULL, review_lease_expires_at=NULL, updated_at=now()
                            WHERE draft_id=:id AND status='reviewing' AND locked_by=:w AND review_lease_version=:v""",
                   s=status, r=reason, id=draft["draft_id"], w=draft["locked_by"], v=draft["review_lease_version"])
        if n == 0:
            raise LeaseLost(f"draft {draft['draft_id']}")
        round_no = q1(conn, "SELECT COALESCE(MAX(review_round), 0) + 1 AS r FROM draft.self_solve_runs WHERE draft_id=:d", d=draft["draft_id"])["r"]
        write_review_records(conn, draft, config, result, datasets, round_no)
        question_id = None
        if status == "approved":
            question_id = promotion.promote(conn, draft, world_dataset_version, result["mode"], result["reference_sql"], result["testcases"])
        ex(conn, "INSERT INTO live.audit_logs (actor_id, action, entity_type, entity_id, detail) VALUES (NULL, :a, 'draft', :e, CAST(:d AS jsonb))",
           a=f"draft.{status}", e=str(draft["draft_id"]), d=_j({"actor": actor, "reasons": result["reasons"], "question_id": question_id}))
    return {"status": status, "question_id": question_id}


class ReviewRunner:
    def __init__(self, config: dict, worker_id: str):
        self.config, self.worker_id = config, worker_id

    def review(self, draft: dict) -> dict:
        cfg = self.config
        with begin() as conn:
            world = q1(conn, "SELECT name, dataset_version FROM core.worlds WHERE world_id=:w", w=draft["world_id"])
            data = load_engine_data(conn, world["name"])
            k, lease_s, hb_s = sr.get(conn, "solve.samples_k"), sr.get(conn, "generation.lease_seconds"), sr.get(conn, "generation.heartbeat_seconds")
        try:
            verify_catalog(cfg, data)
            datasets = rv.build_datasets(cfg)
            ctx = build_context(draft, data, cfg["REVIEW_FEWSHOT"])
        except (rv.InfraError, ValueError) as exc:
            return self._release(draft, f"infra: {exc}")
        base_solver, base_auditor = rv.make_solver(cfg), rv.make_auditor(cfg)

        def solver(prompt, seed, temperature, model=None):
            with eng.llm_context(job_id=draft["job_id"], draft_id=draft["draft_id"], stage="solve_b", prompt_name="solve_b",
                                 prompt_version=rv.REVIEW_VERSION, attempt_no=1):
                return base_solver(prompt, seed, temperature, model)

        def auditor(c, sql):
            with eng.llm_context(job_id=draft["job_id"], draft_id=draft["draft_id"], stage="checklist_b", prompt_name="checklist_b",
                                 prompt_version=rv.REVIEW_VERSION, attempt_no=1):
                return base_auditor(c, sql)

        try:
            with Heartbeat("draft", draft["draft_id"], self.worker_id, draft["review_lease_version"], lease_s, hb_s) as hb:
                result = rv.review_draft(ctx, datasets, solver, k, cfg["REVIEW_SAMPLE_RETRIES"], cfg["REVIEW_ZERO_VALID_ACTION"],
                                         models=cfg["REVIEW_MODELS"], auditor=auditor, repair_rounds=cfg["REVIEW_REPAIR_ROUNDS"])
                hb.check()
                # dữ liệu Enterprise phải không đổi trong lúc chạy
                after = {d.ref: rv.catalog_version(cfg, d.kwargs["dbname"])[0] for d in datasets}
                if any(after[d.ref] != d.version for d in datasets):
                    return self._release(draft, "infra: dữ liệu Enterprise thay đổi trong lúc review; kết quả bị bỏ")
                return commit_result(draft, cfg, result, datasets, world["dataset_version"], f"worker:{self.worker_id}")
        except eng.BudgetExceeded as exc:
            return self._release(draft, f"budget: {exc}", refund=True)
        except rv.InfraError as exc:
            return self._release(draft, f"infra: {exc}", refund=True)

    def _release(self, draft: dict, why: str, refund: bool = True) -> dict:
        log.warning("draft %s trả về pending: %s", draft["draft_id"], why)
        with begin() as conn:
            queue.release_draft(conn, draft, refund_attempt=refund)
        return {"status": "released", "reason": why}
