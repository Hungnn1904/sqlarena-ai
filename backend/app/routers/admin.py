"""API quản trị: job sinh đề, draft/kiểm duyệt, câu hỏi đã xuất bản, kỹ năng, cấu hình, mức dùng LLM."""
import json

from fastapi import APIRouter, Depends, Header, Query, Response

from ..db import begin, ex, q, q1
from ..errors import not_found
from ..pipeline import ledger
from ..schemas import (ApproveBody, DraftEditBody, RequeueBody, JobCreate, RejectBody, RestoreBody, RetireBody, SettingBody, SourceBody, WeeklyItemsBody,
                       WeeklySetCreate)
from ..security import require_admin
from ..services import audit, drafts, jobs, questions, weekly
from ..services import settings_registry as sr

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------- generation jobs
@router.post("/generation-jobs", status_code=202, tags=["admin-jobs"])
def create_job(body: JobCreate, response: Response, admin: dict = Depends(require_admin), idempotency_key: str | None = Header(None, max_length=100)):
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


@router.post("/drafts/{draft_id}/approve", tags=["admin-drafts"])
def approve_draft(draft_id: int, body: ApproveBody, admin: dict = Depends(require_admin)):
    return drafts.approve(admin, draft_id, body.selected_run_id, body.note)     # tự quản lý transaction (chạy lại SQL có thể lâu)


@router.post("/drafts/{draft_id}/reject", tags=["admin-drafts"])
def reject_draft(draft_id: int, body: RejectBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return drafts.reject(conn, admin, draft_id, body.reason)


# ---------------------------------------------------------------- published questions
@router.get("/questions", tags=["admin-questions"])
def admin_questions(status: str | None = Query(None, pattern="^(ready|archived|retired)$"), difficulty: int | None = Query(None, ge=1, le=3),
                    skill_id: int | None = None, q: str | None = Query(None, max_length=100), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return questions.admin_list(conn, status, difficulty, skill_id, q, page, page_size)


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


@router.get("/llm-usage", tags=["admin-settings"])
def llm_usage():
    with begin() as conn:
        cap = sr.get(conn, "generation.daily_budget_calls")
        by = q(conn, "SELECT stage, status, count(*) AS n FROM draft.llm_call_ledger WHERE (created_at AT TIME ZONE :tz)::date = (now() AT TIME ZONE :tz)::date "
                     "GROUP BY stage, status ORDER BY stage, status", tz=__import__("app.config", fromlist=["x"]).get_settings().app_timezone)
        return {"daily_cap": cap, "used_today": ledger.used_today(conn), "by_stage_status": by}
