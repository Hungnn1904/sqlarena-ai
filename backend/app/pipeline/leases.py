"""Lease + heartbeat + fencing token cho job sinh đề và draft đang review."""
import threading

from ..db import begin, ex


class LeaseLost(Exception):
    """Worker không còn là chủ sở hữu hiện hành (hết lease/bị claim lại): phải bỏ kết quả."""


_HEARTBEAT_SQL = {
    "job": ("UPDATE draft.generation_jobs SET lease_expires_at = now() + make_interval(secs => :s) "
            "WHERE job_id=:id AND status='running' AND locked_by=:w AND lease_version=:v"),
    "draft": ("UPDATE draft.question_drafts SET review_lease_expires_at = now() + make_interval(secs => :s) "
              "WHERE draft_id=:id AND status='reviewing' AND locked_by=:w AND review_lease_version=:v"),
}


class Heartbeat:
    """Gia hạn lease định kỳ trong luồng riêng (transaction ngắn); đặt cờ `lost` nếu fencing token không còn khớp."""

    def __init__(self, kind: str, entity_id: int, worker_id: str, version: int, lease_seconds: int, interval: float):
        self.kind, self.id, self.worker, self.version = kind, entity_id, worker_id, version
        self.lease_seconds, self.interval = lease_seconds, interval
        self.lost = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"heartbeat-{kind}-{entity_id}")

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                with begin() as conn:
                    n = ex(conn, _HEARTBEAT_SQL[self.kind], s=self.lease_seconds, id=self.id, w=self.worker, v=self.version)
                if n == 0:
                    self.lost.set()
                    return
            except Exception:       # lỗi DB tạm thời: thử lại ở nhịp sau; lease hết hạn sẽ tự bảo vệ
                continue

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join(timeout=5)

    def check(self) -> None:
        if self.lost.is_set():
            raise LeaseLost(f"{self.kind} {self.id}: mất quyền sở hữu lease")
