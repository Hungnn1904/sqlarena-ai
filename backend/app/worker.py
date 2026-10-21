"""Generation/Review Worker: process riêng, cùng codebase. Polling queue PostgreSQL (SKIP LOCKED) + lease/heartbeat/fencing."""
import logging
import os
import socket
import time
import uuid

from .config import get_settings
from .db import begin
from .pipeline import engine as eng
from .pipeline import ledger
from .pipeline.generation import GenerationRunner
from .pipeline.leases import LeaseLost
from .pipeline.review import ReviewRunner
from .services import queue
from .services import settings_registry as sr

log = logging.getLogger("worker")


class Worker:
    def __init__(self, config: dict | None = None, worker_id: str | None = None):
        s = get_settings()
        self.worker_id = worker_id or f"{s.worker_id_prefix}-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.config = config or eng.load_engine_config()
        ledger.install()
        with begin() as conn:
            eng.set_concurrency(sr.get(conn, "llm.max_concurrent"))
        self.gen, self.rev = GenerationRunner(self.config, self.worker_id), ReviewRunner(self.config, self.worker_id)

    def run_once(self) -> dict:
        """Một nhịp: thu hồi kẹt → (1) một job sinh đề → (2) review draft pending. Trả thống kê để test/giám sát."""
        stats = {"job": None, "reviewed": []}
        with begin() as conn:
            queue.recover_stale_jobs(conn)
            queue.recover_stale_drafts(conn)
        ledger.recover_orphans()
        with begin() as conn:
            job = queue.claim_job(conn, self.worker_id)
        if job:
            try:
                stats["job"] = (job["job_id"], self.gen.run_job(job))
            except LeaseLost as exc:
                log.warning("job %s: mất lease, bỏ kết quả (%s)", job["job_id"], exc)
                stats["job"] = (job["job_id"], "lease_lost")
        while True:
            with begin() as conn:
                draft = queue.claim_draft(conn, self.worker_id)
            if not draft:
                break
            try:
                res = self.rev.review(draft)
            except LeaseLost as exc:
                log.warning("draft %s: mất lease, bỏ kết quả (%s)", draft["draft_id"], exc)
                res = {"status": "lease_lost"}
            stats["reviewed"].append((draft["draft_id"], res["status"]))
            if res["status"] == "released":
                break                      # hạ tầng/ngân sách có vấn đề: dừng nhịp này, đừng quay vòng vô hạn
        return stats

    def run_forever(self) -> None:
        poll = get_settings().worker_poll_seconds
        log.info("worker %s bắt đầu", self.worker_id)
        while True:
            try:
                s = self.run_once()
                idle = s["job"] is None and not s["reviewed"]
            except Exception:
                log.exception("lỗi trong vòng lặp worker")
                idle = True
            if idle:
                time.sleep(poll)
