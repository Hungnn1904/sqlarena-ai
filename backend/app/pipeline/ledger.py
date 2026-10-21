"""BudgetGuard + llm_call_ledger: reserve trước khi gọi provider, atomic theo ngày ứng dụng."""
from sqlalchemy import text

from ..config import get_settings
from ..db import begin, ex, q1
from ..services import settings_registry as sr
from . import engine as eng


def used_today(conn) -> int:
    tz = get_settings().app_timezone
    return conn.execute(text(
        "SELECT count(*) FROM draft.llm_call_ledger WHERE status <> 'cancelled' "
        "AND (created_at AT TIME ZONE :tz)::date = (now() AT TIME ZONE :tz)::date"), {"tz": tz}).scalar_one()


def reserve(ctx: eng.LlmContext, meta: dict) -> int:
    """Transaction ngắn, khóa advisory để nhiều worker không vượt trần do race."""
    with begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('llm_budget'))"))
        limit = sr.get(conn, "generation.daily_budget_calls")
        if used_today(conn) >= limit:
            raise eng.BudgetExceeded(f"Đã chạm trần {limit} lần gọi LLM trong ngày")
        row = q1(conn, """INSERT INTO draft.llm_call_ledger
              (job_id, draft_id, stage, attempt_no, provider, model, prompt_name, prompt_version, prompt_hash, request_hash, status)
              VALUES (:job, :draft, :stage, :att, 'ollama', :model, :pn, :pv, :ph, :rh, 'reserved') RETURNING call_id""",
                 job=ctx.job_id, draft=ctx.draft_id, stage=ctx.stage, att=ctx.attempt_no, model=meta["model"],
                 pn=ctx.prompt_name, pv=ctx.prompt_version, ph=meta["prompt_hash"], rh=meta["request_hash"])
        return row["call_id"]


def finish(call_id: int, status: str, extra: dict | None) -> None:
    extra = extra or {}
    with begin() as conn:
        if status == "running":
            ex(conn, "UPDATE draft.llm_call_ledger SET status='running', started_at=now() WHERE call_id=:c", c=call_id)
        else:
            ex(conn, """UPDATE draft.llm_call_ledger SET status=:s, finished_at=now(), latency_ms=:l, input_tokens=:i,
                        output_tokens=:o, error_code=:e WHERE call_id=:c""",
               s=status, l=extra.get("latency_ms"), i=extra.get("input_tokens"), o=extra.get("output_tokens"),
               e=extra.get("error_code"), c=call_id)


def recover_orphans(older_than_seconds: int = 900) -> int:
    """Crash giữa chừng: call chưa terminal quá lâu → failed(orphaned); không xóa lịch sử."""
    with begin() as conn:
        return ex(conn, """UPDATE draft.llm_call_ledger SET status='failed', error_code='orphaned', finished_at=now()
                           WHERE status IN ('reserved','running') AND created_at < now() - make_interval(secs => :s)""",
                  s=older_than_seconds)


def install() -> None:
    eng.install_ledger(reserve, finish)
