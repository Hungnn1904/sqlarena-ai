"""Tạo/xem job sinh đề: validate, idempotency, kiểm tra trần ngân sách LLM trước khi enqueue."""
import hashlib
import json
import logging
import threading
import time

from sqlalchemy import Connection

from ..db import begin, ex, q, q1
from ..domain import DIFF_NAME
from ..errors import ApiError, bad_request, conflict, not_found
from ..pipeline import ledger
from . import audit
from . import settings_registry as sr

log = logging.getLogger("jobs")
_FEASIBLE: dict | None = None
_worker_lock = threading.Lock()
_daemon_started = False
_wake_event = threading.Event()


def run_worker_until_idle() -> dict:
    """Chạy Worker().run_once() thật (Model A ai/main.py + Model B ai/review.py) cho tới khi hết job/draft trong hàng đợi."""
    from ..worker import Worker
    last_stats = {"job": None, "reviewed": []}
    with _worker_lock:
        worker = Worker()
        while True:
            s = worker.run_once()
            if s["job"] is not None or s["reviewed"]:
                last_stats = s
            if s["job"] is None and not s["reviewed"]:
                break
    return last_stats


def _background_worker_daemon() -> None:
    while True:
        try:
            run_worker_until_idle()
        except Exception:
            log.exception("Lỗi trong vòng lặp Worker nền tự động")
        _wake_event.wait(timeout=2.0)
        _wake_event.clear()


def _release_dead_reload_leases() -> None:
    """Khi Uvicorn --reload khởi động lại process mới, giải phóng ngay các lease của PID cũ đã tắt."""
    import os
    pid_tag = f"-{os.getpid()}-"
    try:
        with begin() as conn:
            ex(conn, """UPDATE draft.generation_jobs
                        SET status='queued', locked_by=NULL, lease_expires_at=NULL,
                            attempt_count=GREATEST(attempt_count - 1, 0)
                        WHERE status='running' AND (locked_by IS NULL OR position(:p in locked_by) = 0)""", p=pid_tag)
            ex(conn, """UPDATE draft.question_drafts
                        SET status='pending', locked_by=NULL, review_lease_expires_at=NULL,
                            review_attempts=GREATEST(review_attempts - 1, 0)
                        WHERE status='reviewing' AND (locked_by IS NULL OR position(:p in locked_by) = 0)""", p=pid_tag)
            ex(conn, """UPDATE draft.llm_call_ledger
                        SET status='cancelled', error_code='reload_restart', finished_at=now()
                        WHERE status IN ('reserved', 'running')""")
    except Exception:
        log.exception("Không thể giải phóng lease cũ khi khởi động Worker")


def start_background_worker_loop() -> None:
    """Khởi chạy daemon thread quét job/draft mỗi 2 giây (chỉ 1 loop trên mỗi tiến trình)."""
    global _daemon_started
    if _daemon_started:
        _wake_event.set()
        return
    _daemon_started = True
    _release_dead_reload_leases()
    threading.Thread(target=_background_worker_daemon, name="sqlarena-worker-daemon", daemon=True).start()


def _run_worker_in_background() -> None:
    time.sleep(0.15)
    _wake_event.set()
    try:
        run_worker_until_idle()
    except Exception:
        log.exception("Lỗi khi thực thi Worker nền cho generation job")


def _feasible_pairs() -> dict | None:
    """skill code → các độ khó Rules cho phép. Không đọc được Rules thì bỏ qua (worker vẫn kiểm tra lại)."""
    global _FEASIBLE
    if _FEASIBLE is None:
        try:
            from ..pipeline import engine as eng
            _FEASIBLE = eng.arena.feasible_pairs(eng.arena.read_rules(eng.load_engine_config()))
        except Exception:
            return None
    return _FEASIBLE


def estimate_calls(quantity: int, k: int) -> int:
    return quantity * (1 + k)          # 1 call Model A + k call Model B mỗi đề (chưa tính retry/audit; trần runtime vẫn chặn)


def create(conn: Connection, admin: dict, p: dict, idempotency_key: str | None) -> tuple[dict, bool]:
    """Trả (job, created). created=False khi phát lại cùng Idempotency-Key + cùng nội dung."""
    qty = p.get("quantity") or p.get("requested_count") or 3
    p["quantity"] = qty
    skills = {r["skill_id"]: r for r in q(conn, "SELECT skill_id, code, is_active FROM core.skills")}
    ids = list(dict.fromkeys(p["skill_ids"])) if p.get("skill_ids") else [i for i, v in skills.items() if v["is_active"]]
    bad = [i for i in ids if i not in skills or not skills[i]["is_active"]]
    if bad:
        raise bad_request("skill_ids không hợp lệ", {"skill_ids": bad})
    world = q1(conn, "SELECT world_id, is_active FROM core.worlds WHERE world_id=:w", w=p["world_id"]) if p.get("world_id") else \
        q1(conn, "SELECT world_id, is_active FROM core.worlds WHERE is_active ORDER BY world_id LIMIT 1")
    if not world or not world["is_active"]:
        raise bad_request("World không tồn tại hoặc đã tắt", {"world_id": p.get("world_id")})
    feas = _feasible_pairs()
    if feas is not None:
        ok = [i for i in ids if DIFF_NAME[p["difficulty"]] in feas.get(skills[i]["code"], {DIFF_NAME[p["difficulty"]]})]
        if not ok and p.get("auto_run"):
            # Chỉ tự động mở rộng khi gọi từ Web UI (auto_run=True); giữ nguyên kiểm tra chặt cho API contract
            ok = [i for i, v in skills.items() if v["is_active"] and DIFF_NAME[p["difficulty"]] in feas.get(v["code"], {DIFF_NAME[p["difficulty"]]})]
        if not ok:
            raise bad_request("Rules không định nghĩa các kỹ năng đã chọn ở độ khó này",
                              {"difficulty": p["difficulty"], "skill_ids": ids})
        ids = ok
    qty_max = sr.get(conn, "generation.max_quantity")
    if p["quantity"] > qty_max:
        raise bad_request(f"quantity tối đa {qty_max}", {"quantity": p["quantity"]})
    topic = (p.get("topic") or "").strip() or None
    req_hash = hashlib.sha256(json.dumps({"w": world["world_id"], "d": p["difficulty"], "s": sorted(ids), "t": topic, "q": p["quantity"]},
                                         sort_keys=True).encode()).hexdigest()
    if idempotency_key:
        old = q1(conn, "SELECT * FROM draft.generation_jobs WHERE triggered_by=:u AND idempotency_key=:k", u=admin["user_id"], k=idempotency_key)
        if old:
            if old["request_hash"] != req_hash:
                raise conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency-Key đã dùng cho yêu cầu khác")
            return old, False
    # Reserve ngân sách ở mức job (khóa advisory chống race giữa các request đồng thời)
    conn.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('llm_budget'))")
    k, cap = sr.get(conn, "solve.samples_k"), sr.get(conn, "generation.daily_budget_calls")
    queued = q1(conn, "SELECT COALESCE(SUM(requested_count - created_count - failed_count), 0) AS n FROM draft.generation_jobs "
                      "WHERE status IN ('queued','running')")["n"]
    need = estimate_calls(p["quantity"], k)
    used = ledger.used_today(conn)
    if used + estimate_calls(int(queued), k) + need > cap:
        raise ApiError(429, "LLM_BUDGET_EXCEEDED", "Vượt trần chi phí LLM trong ngày; giảm số lượng hoặc thử lại ngày mai",
                       {"used_today": used, "queued_estimate": estimate_calls(int(queued), k), "requested_estimate": need, "daily_cap": cap},
                       headers={"Retry-After": "3600"})
    job = q1(conn, """INSERT INTO draft.generation_jobs (world_id, triggered_by, difficulty, skill_ids, topic, requested_count, idempotency_key, request_hash)
                      VALUES (:w, :u, :d, :s, :t, :n, :k, :h) RETURNING *""",
             w=world["world_id"], u=admin["user_id"], d=p["difficulty"], s=ids, t=topic, n=p["quantity"], k=idempotency_key, h=req_hash)
    audit.log(conn, admin["user_id"], "job.create", "generation_job", job["job_id"], {"quantity": p["quantity"], "difficulty": p["difficulty"], "skill_ids": ids})
    if p.get("sync_run"):
        conn.commit()
        run_worker_until_idle()
        with begin() as c2:
            job = q1(c2, "SELECT * FROM draft.generation_jobs WHERE job_id=:j", j=job["job_id"]) or job
    elif p.get("auto_run"):
        _wake_event.set()
        threading.Thread(target=_run_worker_in_background, name=f"sqlarena-worker-{job['job_id']}", daemon=True).start()
    else:
        _wake_event.set()
    return job, True


def public(job: dict) -> dict:
    keys = ("job_id", "world_id", "difficulty", "skill_ids", "topic", "requested_count", "created_count", "failed_count", "status",
            "error_message", "created_at", "started_at", "finished_at")
    return {k: job[k] for k in keys}


def detail(conn: Connection, job_id: int) -> dict:
    job = q1(conn, "SELECT * FROM draft.generation_jobs WHERE job_id=:i", i=job_id)
    if not job:
        raise not_found("Không tìm thấy job")
    by_status = {r["status"]: r["n"] for r in q(conn, "SELECT status, count(*) AS n FROM draft.question_drafts WHERE job_id=:i GROUP BY status", i=job_id)}
    calls = q(conn, "SELECT stage, status, count(*) AS n FROM draft.llm_call_ledger WHERE job_id=:i GROUP BY stage, status ORDER BY stage, status", i=job_id)
    return {**public(job), "drafts_by_status": by_status, "llm_calls": calls}


def list_jobs(conn: Connection, status: str | None, page: int, size: int) -> dict:
    where, params = ("WHERE status=:s", {"s": status}) if status else ("", {})
    total = q1(conn, f"SELECT count(*) AS n FROM draft.generation_jobs {where}", **params)["n"]
    rows = q(conn, f"SELECT * FROM draft.generation_jobs {where} ORDER BY created_at DESC, job_id DESC LIMIT :l OFFSET :o", l=size, o=(page - 1) * size, **params)
    items = []
    for r in rows:
        drafts = q(conn, "SELECT draft_id, title, status, created_at FROM draft.question_drafts WHERE job_id = :jid ORDER BY draft_id DESC", jid=r["job_id"])
        items.append({**public(r), "drafts": [{"draft_id": d["draft_id"], "title": d["title"], "status": d["status"], "created_at": d["created_at"]} for d in drafts]})
    return {"items": items, "total": total, "page": page, "page_size": size}
