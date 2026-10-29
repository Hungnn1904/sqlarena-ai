from fastapi import APIRouter

from ..db import begin, q, q1

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/healthz")
def health():
    """Liveness + tình trạng hàng đợi (không chứa bí mật)."""
    with begin() as conn:
        conn.exec_driver_sql("SELECT 1")
        jobs = {r["status"]: r["n"] for r in q(conn, "SELECT status, count(*) AS n FROM draft.generation_jobs GROUP BY status")}
        drafts = {r["status"]: r["n"] for r in q(conn, "SELECT status, count(*) AS n FROM draft.question_drafts GROUP BY status")}
        stale = q1(conn, "SELECT (SELECT count(*) FROM draft.generation_jobs WHERE status='running' AND lease_expires_at < now()) AS stale_jobs, "
                         "(SELECT count(*) FROM draft.question_drafts WHERE status='reviewing' AND review_lease_expires_at < now()) AS stale_drafts")
    return {"status": "ok", "jobs": jobs, "drafts": drafts, **stale}
