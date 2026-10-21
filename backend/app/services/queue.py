"""Hàng đợi PostgreSQL: claim bằng FOR UPDATE SKIP LOCKED, lease + fencing token, thu hồi job/draft kẹt."""
from sqlalchemy import Connection

from ..db import ex, q1
from . import settings_registry as sr


def recover_stale_jobs(conn: Connection) -> int:
    """running + lease hết hạn + đã đủ max_attempts → failed (lỗi hệ thống). Còn lại để claim thông thường (running→queued ngầm)."""
    mx = sr.get(conn, "generation.max_attempts")
    return ex(conn, """UPDATE draft.generation_jobs SET status='failed', error_message='system: quá số lần claim tối đa (worker chết/treo)',
                       finished_at=now(), locked_by=NULL, lease_expires_at=NULL
                       WHERE status='running' AND lease_expires_at < now() AND attempt_count >= :mx""", mx=mx)


def claim_job(conn: Connection, worker_id: str) -> dict | None:
    secs = sr.get(conn, "generation.lease_seconds")
    return q1(conn, """
        WITH c AS (SELECT job_id FROM draft.generation_jobs
                   WHERE status='queued' OR (status='running' AND lease_expires_at < now())
                   ORDER BY created_at, job_id FOR UPDATE SKIP LOCKED LIMIT 1)
        UPDATE draft.generation_jobs j SET status='running', locked_by=:w, locked_at=now(),
               lease_expires_at = now() + make_interval(secs => :s), lease_version = j.lease_version + 1,
               attempt_count = j.attempt_count + 1, started_at = COALESCE(j.started_at, now()), error_message = NULL
        FROM c WHERE j.job_id = c.job_id RETURNING j.*""", w=worker_id, s=secs)


def recover_stale_drafts(conn: Connection) -> dict:
    """reviewing + lease hết hạn: còn lượt → pending; hết lượt → needs_human (không để draft kẹt vĩnh viễn)."""
    mx = sr.get(conn, "generation.max_attempts")
    to_human = ex(conn, """UPDATE draft.question_drafts SET status='needs_human', status_reason='system: review không hoàn tất sau nhiều lần claim',
                           locked_by=NULL, review_lease_expires_at=NULL, updated_at=now()
                           WHERE status='reviewing' AND review_lease_expires_at < now() AND review_attempts >= :mx""", mx=mx)
    to_pending = ex(conn, """UPDATE draft.question_drafts SET status='pending', locked_by=NULL, review_lease_expires_at=NULL, updated_at=now()
                             WHERE status='reviewing' AND review_lease_expires_at < now() AND review_attempts < :mx""", mx=mx)
    return {"to_needs_human": to_human, "to_pending": to_pending}


def claim_draft(conn: Connection, worker_id: str) -> dict | None:
    secs = sr.get(conn, "generation.lease_seconds")
    return q1(conn, """
        WITH c AS (SELECT draft_id FROM draft.question_drafts WHERE status='pending'
                   ORDER BY created_at, draft_id FOR UPDATE SKIP LOCKED LIMIT 1)
        UPDATE draft.question_drafts d SET status='reviewing', locked_by=:w, locked_at=now(),
               review_lease_expires_at = now() + make_interval(secs => :s), review_lease_version = d.review_lease_version + 1,
               review_attempts = d.review_attempts + 1, updated_at = now()
        FROM c WHERE d.draft_id = c.draft_id RETURNING d.*""", w=worker_id, s=secs)


def release_draft(conn: Connection, draft: dict, refund_attempt: bool) -> int:
    """reviewing → pending (fenced). Lỗi hạ tầng/ngân sách không tính là một lượt review."""
    return ex(conn, """UPDATE draft.question_drafts SET status='pending', locked_by=NULL, review_lease_expires_at=NULL,
                       review_attempts = GREATEST(review_attempts - :r, 0), updated_at=now()
                       WHERE draft_id=:id AND status='reviewing' AND locked_by=:w AND review_lease_version=:v""",
              r=1 if refund_attempt else 0, id=draft["draft_id"], w=draft["locked_by"], v=draft["review_lease_version"])
