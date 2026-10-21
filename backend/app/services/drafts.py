"""Hàng đợi kiểm duyệt: xem draft + bằng chứng review, admin approve/reject các draft `needs_human`."""
import json

from sqlalchemy import Connection

from ..db import begin, ex, q, q1
from ..errors import ApiError, bad_request, conflict, not_found
from ..pipeline import engine as eng
from ..pipeline import review as pr
from ..pipeline.catalog import load_engine_data, verify_catalog
from ..pipeline.leases import Heartbeat, LeaseLost
from . import audit, promotion
from . import settings_registry as sr

rv = eng.rv
LIST_COLS = "draft_id, job_id, title, difficulty, skill_ids, status, status_reason, tables_used, gen_model, retry_count, review_attempts, created_at, updated_at"
_ATTEST = {"verdict": "pass", "issues": [], "checks": [{"requirement": r, "status": "pass", "finding": "admin_attested"} for r in (
    "output columns and aliases", "WHERE, HAVING, aggregate thresholds", "joins, row grain, EXISTS and correlated subqueries",
    "NULL, date, rounding, unit edge cases", "ordering and tie breakers")], "attested_by_admin": True}


def list_drafts(conn: Connection, status, job_id, difficulty, page: int, size: int) -> dict:
    conds, p = [], {}
    for col, val in (("status", status), ("job_id", job_id), ("difficulty", difficulty)):
        if val is not None:
            conds.append(f"{col}=:{col}")
            p[col] = val
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = q1(conn, f"SELECT count(*) AS n FROM draft.question_drafts {where}", **p)["n"]
    rows = q(conn, f"SELECT {LIST_COLS} FROM draft.question_drafts {where} ORDER BY draft_id DESC LIMIT :l OFFSET :o", l=size, o=(page - 1) * size, **p)
    return {"items": rows, "total": total, "page": page, "page_size": size}


def detail(conn: Connection, draft_id: int) -> dict:
    d = q1(conn, "SELECT * FROM draft.question_drafts WHERE draft_id=:i", i=draft_id)
    if not d:
        raise not_found("Không tìm thấy draft")
    bp = d["blueprint"] or {}
    cand = bp.get("candidate", {})
    runs = q(conn, "SELECT run_id, sample_index, model_sql, is_selected, matched_datasets, total_datasets, mismatch_detail, exec_status, row_count, "
                   "result_hash, error, review_model, review_round FROM draft.self_solve_runs WHERE draft_id=:i ORDER BY review_round, sample_index", i=draft_id)
    logs = q(conn, "SELECT log_id, stage, passed, score, reasons, review_model, rubric_version, created_at FROM draft.review_logs WHERE draft_id=:i ORDER BY log_id", i=draft_id)
    question = q1(conn, "SELECT question_id, status FROM live.questions WHERE source_draft_id=:i", i=draft_id)
    skills = q(conn, "SELECT skill_id, code, name FROM core.skills WHERE skill_id = ANY(:s) ORDER BY skill_id", s=list(d["skill_ids"]))
    out = {k: d[k] for k in ("draft_id", "world_id", "job_id", "title", "question", "reference_sql", "compare_mode", "difficulty", "tables_used", "schema_text",
                             "status", "status_reason", "gen_model", "gen_prompt_version", "retry_count", "review_attempts", "created_at", "updated_at")}
    out.update(skills=skills, source_question_ids=bp.get("source_question_ids", []),
               blueprint={k: cand.get(k) for k in ("business_domain", "business_goal", "difficulty_reason", "output_columns", "required_columns",
                                                    "table_roles", "logic_signature", "join_relations")},
               validation_report=d["validation_report"], self_solve_runs=runs, review_logs=logs, promoted_question=question)
    return out


def _requeue(conn: Connection, admin: dict, draft_id: int, title, question, note, action: str) -> dict:
    """needs_human/rejected → pending để Model B + các cổng chạy lại trên nội dung mới. Không bao giờ tự thành approved."""
    d = q1(conn, "SELECT * FROM draft.question_drafts WHERE draft_id=:i FOR UPDATE", i=draft_id)
    if not d:
        raise not_found("Không tìm thấy draft")
    if d["status"] not in ("needs_human", "rejected"):
        raise conflict("INVALID_STATE", f"Chỉ draft needs_human/rejected mới sửa/đưa lại hàng đợi được (hiện: {d['status']})", {"status": d["status"]})
    ex(conn, """UPDATE draft.question_drafts SET title=COALESCE(:t, title), question=COALESCE(:q, question), status='pending',
                reference_sql=NULL, compare_mode=NULL, review_attempts=0, locked_by=NULL, review_lease_expires_at=NULL,
                status_reason=:r, updated_at=now() WHERE draft_id=:i""",
       t=title, q=question, r=(f"{action}: {note}" if note else action)[:500], i=draft_id)
    audit.log(conn, admin["user_id"], f"draft.{action}", "draft", draft_id,
              {"from_status": d["status"], "old": {"title": d["title"], "question": d["question"]}, "new": {"title": title, "question": question}, "note": note})
    return detail(conn, draft_id)


def edit(conn: Connection, admin: dict, draft_id: int, title, question, note) -> dict:
    if title is None and question is None:
        raise bad_request("Cần ít nhất một trong title/question")
    return _requeue(conn, admin, draft_id, title, question, note, "admin_edited")


def requeue(conn: Connection, admin: dict, draft_id: int, note) -> dict:
    return _requeue(conn, admin, draft_id, None, None, note, "admin_requeued")


def reject(conn: Connection, admin: dict, draft_id: int, reason: str) -> dict:
    n = ex(conn, """UPDATE draft.question_drafts SET status='rejected', status_reason=:r, locked_by=NULL, review_lease_expires_at=NULL, updated_at=now()
                    WHERE draft_id=:i AND status='needs_human'""", r=reason, i=draft_id)
    if n == 0:
        d = q1(conn, "SELECT status FROM draft.question_drafts WHERE draft_id=:i", i=draft_id)
        if not d:
            raise not_found("Không tìm thấy draft")
        raise conflict("INVALID_STATE", f"Chỉ draft needs_human mới reject được (hiện: {d['status']})", {"status": d["status"]})
    ex(conn, "INSERT INTO live.admin_overrides (admin_id, draft_id, action, note) VALUES (:a, :d, 'reject', :n)", a=admin["user_id"], d=draft_id, n=reason)
    audit.log(conn, admin["user_id"], "draft.reject", "draft", draft_id, {"reason": reason})
    return detail(conn, draft_id)


def approve(admin: dict, draft_id: int, selected_run_id: int | None, note: str | None) -> dict:
    """needs_human → approved bởi admin. Admin KHÔNG bỏ qua mandatory gate: SQL được chạy lại trên mọi dataset qua cùng guard/consensus/
    contract của engine; chỉ các lý do 'phán đoán của người' (ADMIN_OVERRIDABLE) được xác nhận. Semantic audit LLM được thay bằng xác nhận của admin."""
    worker = f"admin:{admin['user_id']}"
    with begin() as conn:
        lease = sr.get(conn, "generation.lease_seconds")
        draft = q1(conn, """UPDATE draft.question_drafts SET status='reviewing', locked_by=:w, locked_at=now(),
                    review_lease_expires_at = now() + make_interval(secs => :s), review_lease_version = review_lease_version + 1, updated_at=now()
                    WHERE draft_id=:i AND status='needs_human' RETURNING *""", w=worker, s=lease, i=draft_id)
        if not draft:
            cur = q1(conn, "SELECT status FROM draft.question_drafts WHERE draft_id=:i", i=draft_id)
            if not cur:
                raise not_found("Không tìm thấy draft")
            raise conflict("INVALID_STATE", f"Chỉ draft needs_human mới approve được (hiện: {cur['status']})", {"status": cur["status"]})
        sql = draft["reference_sql"]
        if not sql:
            if selected_run_id is None:
                _back_to_human(conn, draft)
                raise bad_request("Cần selected_run_id: chọn một lời giải Model B làm đáp án tham chiếu", {"draft_id": draft_id})
            run = q1(conn, "SELECT model_sql, exec_status FROM draft.self_solve_runs WHERE run_id=:r AND draft_id=:d", r=selected_run_id, d=draft_id)
            if not run or run["exec_status"] not in (None, "ok"):
                _back_to_human(conn, draft)
                raise bad_request("selected_run_id không thuộc draft hoặc lời giải không chạy được", {"selected_run_id": selected_run_id})
            sql = run["model_sql"]
        world = q1(conn, "SELECT name, dataset_version FROM core.worlds WHERE world_id=:w", w=draft["world_id"])
        data = load_engine_data(conn, world["name"])
        round_no = (q1(conn, "SELECT COALESCE(MAX(review_round),0)+1 AS r FROM draft.self_solve_runs WHERE draft_id=:d", d=draft_id))["r"]
        lease_s, hb_s = lease, sr.get(conn, "generation.heartbeat_seconds")
    cfg = eng.load_engine_config()
    try:
        verify_catalog(cfg, data)
        datasets = rv.build_datasets(cfg)
        ctx = pr.build_context(draft, data, 0)
        with Heartbeat("draft", draft_id, worker, draft["review_lease_version"], lease_s, hb_s) as hb:
            res = rv.review_draft(ctx, datasets, lambda prompt, seed, temp, model=None: (sql, {}), 1, 0, "needs_human",
                                  models=["admin_selected"], auditor=lambda c, s: dict(_ATTEST), repair_rounds=0)
            hb.check()
        res = _admin_resolve(res, datasets)
    except (rv.InfraError, ValueError) as exc:
        with begin() as conn:
            _back_to_human(conn, draft)
        raise ApiError(503, "REVIEW_INFRA_ERROR", f"Không chạy lại được các cổng kiểm tra: {exc}")
    if res["status"] != "approved":
        with begin() as conn:
            _back_to_human(conn, draft, f"admin approve bị chặn bởi: {', '.join(res['reasons'])}")
        raise conflict("MANDATORY_GATE_FAILED", "Lời giải không qua cổng bắt buộc; admin không được bỏ qua", {"reasons": res["reasons"]})
    cfg = {**cfg, "REVIEW_MODELS": ["admin_selected"]}
    try:
        with begin() as conn:
            n = ex(conn, """UPDATE draft.question_drafts SET status='approved', reference_sql=:sql, compare_mode=:m, status_reason=:r, locked_by=NULL,
                            review_lease_expires_at=NULL, updated_at=now()
                            WHERE draft_id=:i AND status='reviewing' AND locked_by=:w AND review_lease_version=:v""",
                   sql=res["reference_sql"], m=res["mode"], r=f"admin_approved: {note}"[:500] if note else "admin_approved", i=draft_id, w=worker,
                   v=draft["review_lease_version"])
            if n == 0:
                raise LeaseLost(f"draft {draft_id}")
            pr.write_review_records(conn, {**draft, "draft_id": draft_id}, cfg, res, datasets, round_no)
            qid = promotion.promote(conn, draft, world["dataset_version"], res["mode"], res["reference_sql"], res["testcases"])
            ex(conn, "INSERT INTO live.admin_overrides (admin_id, draft_id, action, note) VALUES (:a, :d, 'approve', :n)", a=admin["user_id"], d=draft_id, n=note)
            audit.log(conn, admin["user_id"], "draft.approve", "draft", draft_id, {"question_id": qid, "overridden_reasons": res.get("overridden", []), "selected_run_id": selected_run_id})
    except LeaseLost:
        raise conflict("LEASE_LOST", "Draft đã bị xử lý bởi tiến trình khác; tải lại trang")
    with begin() as conn:
        return detail(conn, draft_id)


def _back_to_human(conn: Connection, draft: dict, reason: str | None = None) -> None:
    ex(conn, """UPDATE draft.question_drafts SET status='needs_human', locked_by=NULL, review_lease_expires_at=NULL,
                status_reason=COALESCE(:r, status_reason), updated_at=now()
                WHERE draft_id=:i AND status='reviewing' AND locked_by=:w AND review_lease_version=:v""",
       r=reason, i=draft["draft_id"], w=draft["locked_by"], v=draft["review_lease_version"])


def _admin_resolve(res: dict, datasets: list) -> dict:
    """Nếu engine dừng ở needs_human chỉ vì lý do 'phán đoán của người', admin được xác nhận: dựng test case từ chính kết quả đã chạy."""
    if res["status"] == "approved":
        return res
    reasons = set(res["reasons"])
    selected = next((s for s in res.get("samples", []) if s.get("is_selected")), None)
    if res["status"] != "needs_human" or not reasons or not reasons <= pr.ADMIN_OVERRIDABLE or not selected or not res.get("reference_sql"):
        return res
    mode = res["mode"]
    tcs = []
    for ds in datasets:
        r = selected["results"][ds.ref]
        if r["status"] != "ok" or r["truncated"]:
            return res                     # kết quả bị cắt/lỗi: không thể làm đáp án chấm điểm
        tcs.append({"dataset_ref": ds.ref, "dataset_version": ds.version, "compare_mode": mode, "reference_sql": selected["sql"],
                    "expected_columns": r["columns"], "expected_rows": r["rows"], "row_count": r["row_count"],
                    "result_hash": rv.result_hash(r["rows"], mode)})
    return {**res, "status": "approved", "testcases": tcs, "overridden": sorted(reasons)}
