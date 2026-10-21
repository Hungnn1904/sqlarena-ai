"""Kiểm duyệt của admin, ngân sách runtime, lease/fencing, idempotent promote, retire/restore."""
import threading

import pytest
from conftest import enqueue_job, new_worker
from fakes import GOOD_SQL, WRONG_SQL, FakeOllama

from app import db
from app.pipeline import engine as eng
from app.pipeline.leases import LeaseLost
from app.services import promotion, queue

NO_ORDER_SQL = "SELECT employee_id, full_name, job_title, hire_date FROM employees WHERE status = 'active' AND hire_date >= DATE '2024-01-01'"


def _needs_human_draft(admin_id):
    eng.set_transport(FakeOllama(solver_sqls=[GOOD_SQL, GOOD_SQL, WRONG_SQL]))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        assert db.q1(conn, "SELECT status FROM draft.question_drafts")["status"] == "needs_human"


def _run_with_sql(sql_text):
    with db.begin() as conn:
        return db.q1(conn, "SELECT run_id FROM draft.self_solve_runs WHERE model_sql=:s ORDER BY run_id LIMIT 1", s=sql_text)["run_id"]


def test_admin_approve_runs_gates_again_and_promotes(client, admin_id, admin_h):
    _needs_human_draft(admin_id)
    r = client.post("/api/v1/admin/drafts/1/approve", json={}, headers=admin_h)
    assert r.status_code == 400                                           # thiếu selected_run_id: không đoán đáp án
    r = client.post("/api/v1/admin/drafts/1/approve", json={"selected_run_id": _run_with_sql(GOOD_SQL), "note": "đã đối chiếu"}, headers=admin_h)
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["promoted_question"]["status"] == "ready"
    with db.begin() as conn:
        assert db.q1(conn, "SELECT count(*) n FROM live.test_cases")["n"] == 1
        assert db.q1(conn, "SELECT action FROM live.admin_overrides")["action"] == "approve"
        assert db.q1(conn, "SELECT count(*) n FROM live.audit_logs WHERE action='draft.approve'")["n"] == 1
    # Approve lần hai: trạng thái không còn needs_human
    again = client.post("/api/v1/admin/drafts/1/approve", json={"selected_run_id": 1}, headers=admin_h)
    assert again.status_code == 409 and again.json()["code"] == "INVALID_STATE"


def test_admin_cannot_override_mandatory_gate(client, admin_id, admin_h):
    """Đề yêu cầu ORDER BY; lời giải không có ORDER BY → cổng bắt buộc, admin không thể phê duyệt."""
    eng.set_transport(FakeOllama(solver_sqls=[NO_ORDER_SQL]))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d = db.q1(conn, "SELECT status, status_reason FROM draft.question_drafts")
    assert d["status"] == "needs_human" and "required_order_by_missing" in d["status_reason"]
    r = client.post("/api/v1/admin/drafts/1/approve", json={"selected_run_id": _run_with_sql(NO_ORDER_SQL)}, headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "MANDATORY_GATE_FAILED"
    with db.begin() as conn:
        assert db.q1(conn, "SELECT status FROM draft.question_drafts")["status"] == "needs_human"      # trả về hàng đợi, không kẹt
        assert db.q1(conn, "SELECT count(*) n FROM live.questions")["n"] == 0


def test_admin_reject_and_state_guard(client, admin_id, admin_h):
    _needs_human_draft(admin_id)
    assert client.post("/api/v1/admin/drafts/1/reject", json={"reason": "x"}, headers=admin_h).status_code == 400   # lý do quá ngắn
    r = client.post("/api/v1/admin/drafts/1/reject", json={"reason": "Đề mơ hồ, không cứu được"}, headers=admin_h)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert client.post("/api/v1/admin/drafts/1/reject", json={"reason": "lần hai"}, headers=admin_h).status_code == 409
    assert client.post("/api/v1/admin/drafts/999/approve", json={"selected_run_id": 1}, headers=admin_h).status_code == 404


def test_runtime_budget_stops_job_and_counts_every_attempt(admin_id):
    with db.begin() as conn:
        db.ex(conn, "UPDATE core.system_settings SET value='2' WHERE key='generation.daily_budget_calls'")
    fake = FakeOllama(); eng.set_transport(fake)
    job_id = enqueue_job(admin_id, quantity=3)
    new_worker().run_once()
    with db.begin() as conn:
        j = db.q1(conn, "SELECT status, error_message FROM draft.generation_jobs WHERE job_id=:j", j=job_id)
        used = db.q1(conn, "SELECT count(*) n FROM draft.llm_call_ledger")["n"]
        pending = db.q1(conn, "SELECT count(*) n FROM draft.question_drafts WHERE status='approved'")["n"]
    assert used <= 2 and fake.calls["model_a"] + fake.calls["solver"] + fake.calls["auditor"] <= 2     # trần cứng, không vượt
    assert pending == 0
    # draft đã tạo (nếu có) không bị kẹt `reviewing`
    with db.begin() as conn:
        assert db.q1(conn, "SELECT count(*) n FROM draft.question_drafts WHERE status='reviewing'")["n"] == 0
    assert j["status"] in ("done", "failed")


def test_ollama_down_fails_job_fast_without_burning_budget(admin_id):
    eng.set_transport(FakeOllama(fail_with=ValueError("Ollama khong phan hoi/timeout. Khoi dong Ollama")))
    job_id = enqueue_job(admin_id, quantity=5)
    new_worker().run_once()
    with db.begin() as conn:
        j = db.q1(conn, "SELECT status, error_message, failed_count FROM draft.generation_jobs WHERE job_id=:j", j=job_id)
        n = db.q1(conn, "SELECT count(*) n FROM draft.llm_call_ledger")["n"]
        st = {r["status"] for r in db.q(conn, "SELECT status FROM draft.llm_call_ledger")}
    assert j["status"] == "failed" and "system" in j["error_message"] and j["failed_count"] == 2
    assert n == 2 and st == {"timed_out"}                                    # dừng sau 2 slot hỏng liên tiếp, không đốt 5×3 call


def test_job_claim_is_exclusive_under_concurrency(admin_id):
    enqueue_job(admin_id)
    got, barrier = [], threading.Barrier(4)

    def claim(i):
        barrier.wait()
        with db.begin() as conn:
            got.append(queue.claim_job(conn, f"w{i}"))
    ts = [threading.Thread(target=claim, args=(i,)) for i in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sum(1 for g in got if g) == 1                                     # SKIP LOCKED: đúng một worker giữ job


def test_fencing_rejects_stale_worker_after_lease_takeover(admin_id):
    enqueue_job(admin_id)
    with db.begin() as conn:
        old = queue.claim_job(conn, "w-old")
        db.ex(conn, "UPDATE draft.generation_jobs SET lease_expires_at = now() - interval '1 second'")
    with db.begin() as conn:
        new = queue.claim_job(conn, "w-new")
    assert new["lease_version"] == old["lease_version"] + 1 and new["attempt_count"] == 2
    from app.pipeline.generation import GenerationRunner
    stale = GenerationRunner(eng.load_engine_config(), "w-old")
    with pytest.raises(LeaseLost):
        stale._finish(old, "done", None)                                     # worker cũ không ghi đè được
    with db.begin() as conn:
        assert db.q1(conn, "SELECT status FROM draft.generation_jobs")["status"] == "running"


def test_job_exceeding_max_attempts_fails_instead_of_looping(admin_id):
    enqueue_job(admin_id)
    for i in range(3):
        with db.begin() as conn:
            assert queue.claim_job(conn, f"w{i}")
            db.ex(conn, "UPDATE draft.generation_jobs SET lease_expires_at = now() - interval '1 second'")
    with db.begin() as conn:
        queue.recover_stale_jobs(conn)
        j = db.q1(conn, "SELECT status, error_message FROM draft.generation_jobs")
        assert queue.claim_job(conn, "w9") is None
    assert j["status"] == "failed" and "system" in j["error_message"]


def test_stale_review_goes_back_to_queue_then_to_human(admin_id):
    eng.set_transport(FakeOllama()); enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:                                                 # giả lập worker chết giữa lúc review
        db.ex(conn, "UPDATE draft.question_drafts SET status='reviewing', locked_by='dead', review_lease_expires_at=now()-interval '1s', review_attempts=1")
        assert queue.recover_stale_drafts(conn) == {"to_needs_human": 0, "to_pending": 1}
        db.ex(conn, "UPDATE draft.question_drafts SET status='reviewing', review_lease_expires_at=now()-interval '1s', review_attempts=3")
        assert queue.recover_stale_drafts(conn) == {"to_needs_human": 1, "to_pending": 0}


def test_promote_is_idempotent_and_requires_evidence(admin_id):
    eng.set_transport(FakeOllama()); enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d = db.q1(conn, "SELECT * FROM draft.question_drafts")
        tc = db.q1(conn, "SELECT * FROM live.test_cases")
        er = tc["expected_result"]
        case = {"dataset_ref": tc["dataset_ref"], "dataset_version": "fp", "compare_mode": "ordered", "expected_columns": er["columns"],
                "expected_rows": er["rows"], "row_count": er["row_count"], "result_hash": er["result_hash"]}
        a = promotion.promote(conn, d, 1, "ordered", d["reference_sql"], [case])
        b = promotion.promote(conn, d, 1, "ordered", d["reference_sql"], [case])
        assert a == b and db.q1(conn, "SELECT count(*) n FROM live.questions")["n"] == 1
        assert db.q1(conn, "SELECT count(*) n FROM live.test_cases")["n"] == 1
        with pytest.raises(ValueError):
            promotion.promote(conn, d, 1, "ordered", d["reference_sql"], [])      # không bằng chứng → không promote


def test_retire_and_restore_pipeline_question(client, admin_id, admin_h):
    eng.set_transport(FakeOllama()); enqueue_job(admin_id)
    new_worker().run_once()
    assert client.post("/api/v1/admin/questions/1/retire", json={"reason": "sai dữ liệu"}, headers=admin_h).json()["status"] == "retired"
    assert client.post("/api/v1/admin/questions/1/retire", json={"reason": "lần hai"}, headers=admin_h).status_code == 409
    assert client.post("/api/v1/admin/questions/1/restore", json={}, headers=admin_h).json()["status"] == "ready"
    assert client.post("/api/v1/admin/questions/1/restore", json={}, headers=admin_h).status_code == 409


def test_dataset_schema_endpoint(client, learner_h):
    s = client.get("/api/v1/dataset/schema", headers=learner_h).json()
    names = {t["name"] for t in s["tables"]}
    assert {"employees", "orders", "products"} <= names
    emp = next(t for t in s["tables"] if t["name"] == "employees")
    assert any(c["pk"] for c in emp["columns"]) and any("references" in c for c in emp["columns"])


def test_admin_can_edit_needs_human_draft_and_pipeline_reviews_again(client, admin_id, admin_h):
    _needs_human_draft(admin_id)
    assert client.patch("/api/v1/admin/drafts/1", json={}, headers=admin_h).status_code == 400
    edited = client.patch("/api/v1/admin/drafts/1", json={"title": "Nhân viên vào công ty từ 2024 (đã chỉnh)", "note": "làm rõ tiêu đề"}, headers=admin_h)
    assert edited.status_code == 200 and edited.json()["status"] == "pending" and edited.json()["reference_sql"] is None       # không tự thành READY
    with db.begin() as conn:
        assert db.q1(conn, "SELECT count(*) n FROM live.questions")["n"] == 0
        assert db.q1(conn, "SELECT detail->'old'->>'title' AS t FROM live.audit_logs WHERE action='draft.admin_edited'")["t"].startswith("Nhân viên đang làm")
    eng.set_transport(FakeOllama())                                                   # lần review lại: Model B đồng thuận
    stats = new_worker().run_once()
    assert stats["reviewed"] == [(1, "approved")]
    with db.begin() as conn:
        rounds = {r["review_round"] for r in db.q(conn, "SELECT review_round FROM draft.self_solve_runs")}
        assert rounds == {1, 2}                                                       # vòng 1 (cũ) được giữ, vòng 2 ghi đủ bằng chứng mới
        assert db.q1(conn, "SELECT title FROM live.questions")["title"].endswith("(đã chỉnh)")


def test_rejected_draft_can_be_requeued_but_approved_cannot(client, admin_id, admin_h):
    _needs_human_draft(admin_id)
    client.post("/api/v1/admin/drafts/1/reject", json={"reason": "tạm loại để xem lại"}, headers=admin_h)
    assert client.post("/api/v1/admin/drafts/1/requeue", json={"note": "thử lại"}, headers=admin_h).json()["status"] == "pending"
    eng.set_transport(FakeOllama()); new_worker().run_once()
    assert client.post("/api/v1/admin/drafts/1/requeue", json={}, headers=admin_h).status_code == 409       # đã approved: không đụng được
    assert client.patch("/api/v1/admin/drafts/1", json={"title": "xyz đã duyệt"}, headers=admin_h).status_code == 409
