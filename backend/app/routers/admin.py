"""API quản trị: job sinh đề, draft/kiểm duyệt, câu hỏi đã xuất bản, kỹ năng, cấu hình, mức dùng LLM."""
import json

from fastapi import APIRouter, Body, Depends, Header, Query, Response

from ..db import begin, ex, q, q1
from ..errors import bad_request, not_found
from ..pipeline import engine as eng
from ..pipeline import ledger
from ..schemas import (ApproveBody, BulkApproveBody, DraftEditBody, GatewayKeyBody, JobCreate, ManualQuestionBody, QuestionGroupAddItemsBody,
                       QuestionGroupCreateBody, QuestionGroupItemsBody, QuestionGroupPublishBody, QuestionGroupUpdateBody, RejectBody, RequeueBody, RestoreBody,
                       RetireBody, SettingBody, SourceBody, WeeklyItemsBody, WeeklySetCreate)
from ..security import require_admin
from ..services import audit, drafts, groups, jobs, questions, weekly
from ..services import settings_registry as sr

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------- generation jobs
@router.post("/generation-jobs", status_code=202, tags=["admin-jobs"])
def create_job(body: JobCreate, response: Response, admin: dict = Depends(require_admin), idempotency_key: str | None = Header(None, max_length=100)):
    if body.skill_quantities:
        created_list: list[dict] = []
        any_created = False
        with begin() as conn:
            for idx, item in enumerate(body.skill_quantities):
                sub_key = (
                    idempotency_key
                    if (idempotency_key and len(body.skill_quantities) == 1)
                    else (f"{idempotency_key}:{idx}:{item.skill_id}"[:100] if idempotency_key else None)
                )
                sub_payload = {
                    "world_id": body.world_id,
                    "difficulty": body.difficulty,
                    "skill_ids": [item.skill_id],
                    "quantity": item.quantity,
                    "topic": body.topic,
                    "auto_run": body.auto_run,
                    "sync_run": body.sync_run,
                }
                job, created = jobs.create(conn, admin, sub_payload, sub_key)
                created_list.append(job)
                any_created = any_created or created
        if not any_created:
            response.status_code = 200
        return {**jobs.public(created_list[0]), "created_jobs": [jobs.public(j) for j in created_list]}

    with begin() as conn:
        job, created = jobs.create(conn, admin, body.model_dump(), idempotency_key)
    if not created:
        response.status_code = 200
    return jobs.public(job)


@router.post("/generation-jobs/run-worker", tags=["admin-jobs"])
def trigger_worker_once(admin: dict = Depends(require_admin)):
    """Kích hoạt 1 nhịp Worker thật (Model A + Model B) theo yêu cầu Admin."""
    stats = jobs.run_worker_until_idle()
    return {"status": "ok", "stats": stats}


@router.get("/generation-jobs", tags=["admin-jobs"])
def list_jobs(status: str | None = Query(None, pattern="^(queued|running|done|failed)$"), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return jobs.list_jobs(conn, status, page, page_size)


@router.get("/generation-jobs/{job_id}", tags=["admin-jobs"])
def get_job(job_id: int):
    with begin() as conn:
        return jobs.detail(conn, job_id)


# ---------------------------------------------------------------- drafts / review
@router.get("/drafts", tags=["admin-drafts"])
def list_drafts(status: str | None = Query(None, pattern="^(pending|reviewing|approved|rejected|needs_human)$"), job_id: int | None = None,
                difficulty: int | None = Query(None, ge=1, le=3), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return drafts.list_drafts(conn, status, job_id, difficulty, page, page_size)


@router.post("/drafts/bulk-approve", tags=["admin-drafts"])
def bulk_approve_drafts(body: BulkApproveBody, admin: dict = Depends(require_admin)):
    return drafts.bulk_approve(admin, body.draft_ids, body.note)


@router.get("/drafts/{draft_id}", tags=["admin-drafts"])
def get_draft(draft_id: int):
    with begin() as conn:
        return drafts.detail(conn, draft_id)


@router.patch("/drafts/{draft_id}", tags=["admin-drafts"])
def edit_draft(draft_id: int, body: DraftEditBody, admin: dict = Depends(require_admin)):
    """Sửa title/question của draft needs_human/rejected; draft quay lại `pending` để chạy lại toàn bộ cổng kiểm duyệt."""
    with begin() as conn:
        return drafts.edit(conn, admin, draft_id, body.title, body.question, body.note)


@router.post("/drafts/{draft_id}/requeue", tags=["admin-drafts"])
def requeue_draft(draft_id: int, body: RequeueBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return drafts.requeue(conn, admin, draft_id, body.note)


@router.post("/drafts/{draft_id}/return-needs-human", tags=["admin-drafts"])
def return_draft_needs_human(
    draft_id: int,
    body: RequeueBody = Body(default_factory=RequeueBody),
    admin: dict = Depends(require_admin),
):
    with begin() as conn:
        return drafts.return_needs_human(conn, admin, draft_id, body.note)


@router.post("/drafts/{draft_id}/approve", tags=["admin-drafts"])
def approve_draft(draft_id: int, body: ApproveBody, admin: dict = Depends(require_admin)):
    return drafts.approve(admin, draft_id, body.selected_run_id, body.note, body.custom_sql)     # tự quản lý transaction (chạy lại SQL có thể lâu)


@router.post("/drafts/{draft_id}/reject", tags=["admin-drafts"])
def reject_draft(draft_id: int, body: RejectBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return drafts.reject(conn, admin, draft_id, body.reason)


# ---------------------------------------------------------------- published questions
@router.get("/questions", tags=["admin-questions"])
def admin_questions(status: str | None = Query(None, pattern="^(ready|archived|retired)$"), difficulty: int | None = Query(None, ge=1, le=3),
                    skill_id: int | None = None, q: str | None = Query(None, max_length=100), unassigned_only: bool = Query(False),
                    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return questions.admin_list(conn, status, difficulty, skill_id, q, page, page_size, unassigned_only=unassigned_only)


@router.post("/questions/manual", status_code=201, tags=["admin-questions"])
def create_manual_question(body: ManualQuestionBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return questions.create_manual(conn, admin, body.model_dump())


# ---------------------------------------------------------------- question groups
@router.get("/question-groups", tags=["admin-groups"])
def list_question_groups():
    with begin() as conn:
        return groups.list_groups(conn)


@router.post("/question-groups", status_code=201, tags=["admin-groups"])
def create_question_group(body: QuestionGroupCreateBody, admin: dict = Depends(require_admin)):
    return groups.create(admin, body.name, body.description, body.question_ids, body.draft_ids)


@router.get("/question-groups/{group_id}", tags=["admin-groups"])
def get_question_group(group_id: int):
    with begin() as conn:
        return groups.get(conn, group_id)


@router.patch("/question-groups/{group_id}", tags=["admin-groups"])
def update_question_group(group_id: int, body: QuestionGroupUpdateBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return groups.update(conn, admin, group_id, body.name, body.description, body.model_fields_set)


@router.put("/question-groups/{group_id}/items", tags=["admin-groups"])
def replace_question_group_items(group_id: int, body: QuestionGroupItemsBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return groups.replace_items(conn, admin, group_id, body.question_ids)


@router.post("/question-groups/{group_id}/add-items", tags=["admin-groups"])
def add_question_group_items(group_id: int, body: QuestionGroupAddItemsBody, admin: dict = Depends(require_admin)):
    return groups.add_items(admin, group_id, body.question_ids, body.draft_ids)


@router.delete("/question-groups/{group_id}", tags=["admin-groups"])
def delete_question_group(group_id: int, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return groups.delete(conn, admin, group_id)


@router.post("/question-groups/{group_id}/publish", tags=["admin-groups"])
def publish_question_group(group_id: int, body: QuestionGroupPublishBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return groups.publish(conn, admin, group_id, body.mode, body.set_title)


@router.get("/questions/{question_id}", tags=["admin-questions"])
def admin_question(question_id: int):
    with begin() as conn:
        return questions.admin_detail(conn, question_id)


@router.post("/questions/{question_id}/retire", tags=["admin-questions"])
def retire_question(question_id: int, body: RetireBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return questions.retire(conn, admin, question_id, body.reason)


@router.post("/questions/{question_id}/restore", tags=["admin-questions"])
def restore_question(question_id: int, body: RestoreBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return questions.restore(conn, admin, question_id, body.note)


@router.patch("/questions/{question_id}/source", tags=["admin-questions"])
def question_source(question_id: int, body: SourceBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return questions.set_source(conn, admin, question_id, body.is_source)


# ---------------------------------------------------------------- weekly sets
@router.get("/weekly-sets", tags=["admin-weekly"])
def list_weekly_sets(status: str | None = Query(None, pattern="^(draft|published|closed)$"), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return weekly.list_sets(conn, status, page, page_size)


@router.post("/weekly-sets", status_code=201, tags=["admin-weekly"])
def create_weekly_set(body: WeeklySetCreate, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return weekly.create(conn, admin, body.week_start, body.title)


@router.get("/weekly-sets/{set_id}", tags=["admin-weekly"])
def get_weekly_set(set_id: int):
    with begin() as conn:
        return weekly.get(conn, set_id)


@router.put("/weekly-sets/{set_id}/items", tags=["admin-weekly"])
def put_weekly_items(set_id: int, body: WeeklyItemsBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return weekly.replace_items(conn, admin, set_id, body.question_ids)


@router.delete("/weekly-sets/{set_id}/items/{question_id}", tags=["admin-weekly"])
def delete_weekly_item(set_id: int, question_id: int, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return weekly.remove_item(conn, admin, set_id, question_id)


@router.post("/weekly-sets/{set_id}/publish", tags=["admin-weekly"])
def publish_weekly_set(set_id: int, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return weekly.publish(conn, admin, set_id)


@router.post("/weekly-sets/{set_id}/close", tags=["admin-weekly"])
def close_weekly_set(set_id: int, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return weekly.close(conn, admin, set_id)


# ---------------------------------------------------------------- catalog / settings / usage
@router.get("/skills", tags=["admin-catalog"])
def skills():
    with begin() as conn:
        return {"items": q(conn, "SELECT skill_id, code, name, category, base_difficulty, is_active FROM core.skills ORDER BY skill_id")}


@router.get("/settings", tags=["admin-settings"])
def get_settings_all():
    with begin() as conn:
        return {"items": sr.list_all(conn)}


@router.put("/settings/{key}", tags=["admin-settings"])
def put_setting(key: str, body: SettingBody, admin: dict = Depends(require_admin)):
    value = sr.validate(key, body.value)
    with begin() as conn:
        old = sr.get(conn, key)
        ex(conn, "INSERT INTO core.system_settings (key, value, description) VALUES (:k, CAST(:v AS jsonb), :d) "
                 "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()",
           k=key, v=json.dumps(value), d=sr.REGISTRY[key].description)
        audit.log(conn, admin["user_id"], "setting.update", "setting", key, {"old": old, "new": value})
    return {"key": key, "value": value, "restart_required": sr.REGISTRY[key].restart_required}


@router.get("/gateway-status", tags=["admin-settings"])
def gateway_status():
    """Trả trạng thái kết nối apithat.dev Secret-Blind (không bao giờ trả plaintext API key)."""
    return eng.get_gateway_status()


@router.post("/gateway-key", tags=["admin-settings"])
def update_gateway_key(body: GatewayKeyBody, admin: dict = Depends(require_admin)):
    """Xác thực APITHAT_API_KEY trực tiếp với https://apithat.dev và kích hoạt ngay lập tức."""
    try:
        info = eng.set_runtime_gateway_key(
            api_key=body.api_key,
            base_url=body.base_url,
            preferred_model=body.preferred_model,
            persist_env=body.persist_env,
        )
    except ValueError as exc:
        raise bad_request(str(exc))
    with begin() as conn:
        audit.log(
            conn,
            admin["user_id"],
            "gateway.key_updated",
            "gateway",
            "apithat.dev",
            {"masked_key": info["masked_key"], "base_url": info["base_url"], "preferred_model": info["preferred_model"]},
        )
    return info


def _normalize_call_model(model_val: str | None, stage: str | None) -> str:
    from ..services import draft_dossier
    fallback = "Model A" if stage == "model_a" else ("Auditor" if stage == "checklist_b" else "Model B")
    return draft_dossier.clean_model_name(model_val, fallback)


@router.get("/llm-usage", tags=["admin-settings"])
def llm_usage():
    gw = eng.get_gateway_status()
    active_provider = "apithat.dev" if gw.get("valid") else "ai-pipeline"
    pref = gw.get("preferred_model") or "gpt-5.6-sol"
    models = (
        {"generator": pref, "reviewer": pref, "auditor": pref}
        if gw.get("valid")
        else {"generator": "Model A", "reviewer": "Model B", "auditor": "Auditor"}
    )
    with begin() as conn:
        cap = sr.get(conn, "generation.daily_budget_calls")
        by = q(conn, "SELECT stage, status, count(*) AS n FROM draft.llm_call_ledger WHERE (created_at AT TIME ZONE :tz)::date = (now() AT TIME ZONE :tz)::date "
                     "GROUP BY stage, status ORDER BY stage, status", tz=__import__("app.config", fromlist=["x"]).get_settings().app_timezone)
        raw_recent = q(conn, """SELECT l.call_id, l.job_id, l.draft_id, l.stage, l.attempt_no, l.model, l.prompt_name, l.status,
                                       l.started_at, l.finished_at, l.latency_ms, l.input_tokens, l.output_tokens, l.error_code,
                                       d.title AS title, d.title AS draft_title
                                FROM draft.llm_call_ledger l
                                LEFT JOIN draft.question_drafts d ON d.draft_id = l.draft_id
                                ORDER BY l.call_id DESC
                                LIMIT 15""")
        from ..services import draft_dossier
        recent = []
        for r in raw_recent:
            s_no, k_tot, r_no = draft_dossier.parse_solve_prompt_tag(r.get("prompt_name"))
            recent.append({
                **r,
                "model": _normalize_call_model(r.get("model"), r.get("stage")),
                "sample_no": s_no,
                "samples_total": k_tot,
                "repair_round": r_no,
                "error_alert": draft_dossier.format_error_alert(r.get("error_code")),
            })
        recent_drafts = q(conn, """SELECT d.draft_id, d.job_id, d.title, d.difficulty, d.status, d.created_at, d.updated_at,
                                          lq.question_id AS live_question_id,
                                          (SELECT wsi.position FROM live.weekly_set_items wsi WHERE wsi.question_id = lq.question_id ORDER BY wsi.set_id DESC LIMIT 1) AS weekly_position
                                   FROM draft.question_drafts d
                                   LEFT JOIN live.questions lq ON lq.source_draft_id = d.draft_id
                                   ORDER BY d.draft_id DESC
                                   LIMIT 10""")
        return {
            "daily_cap": cap,
            "used_today": ledger.used_today(conn),
            "by_stage_status": by,
            "active_provider": active_provider,
            "models": models,
            "recent_calls": recent,
            "recent_drafts": recent_drafts,
        }
