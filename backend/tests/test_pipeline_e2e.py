"""Luồng thật: job → Model A → draft → Model B (guard/consensus/audit, SQL chạy thật trên Enterprise DB) → promote → API người học."""
from conftest import enqueue_job, new_worker
from fakes import AUDIT_PASS, GOOD_SQL, GOOD_SQL_ALT, WRONG_SQL, FakeOllama

from app import db
from app.pipeline import engine as eng


def test_happy_path_publishes_question_with_tests(client, admin_id, learner_h, admin_h):
    fake = FakeOllama(); eng.set_transport(fake)
    job_id = enqueue_job(admin_id)
    stats = new_worker().run_once()
    assert stats["job"] == (job_id, "done") and stats["reviewed"] == [(1, "approved")]
    with db.begin() as conn:
        q = db.q1(conn, "SELECT * FROM live.questions")
        tests = db.q(conn, "SELECT * FROM live.test_cases")
        d = db.q1(conn, "SELECT status, reference_sql, compare_mode FROM draft.question_drafts")
        calls = db.q(conn, "SELECT stage, status, count(*) n FROM draft.llm_call_ledger GROUP BY 1,2 ORDER BY 1")
        runs = db.q(conn, "SELECT is_selected, matched_datasets, total_datasets, exec_status FROM draft.self_solve_runs ORDER BY sample_index")
    assert d["status"] == "approved" and d["reference_sql"] and d["compare_mode"] == "ordered"
    assert q["status"] == "ready" and q["source_draft_id"] == 1 and q["tables_used"] == ["employees"]
    assert len(tests) == 1 and tests[0]["expected_result"]["row_count"] > 0 and tests[0]["expected_result"]["result_hash"]
    assert {(c["stage"], c["n"]) for c in calls} == {("model_a", 1), ("solve_b", 3), ("checklist_b", 1)}      # ledger đủ mọi call
    assert [r["is_selected"] for r in runs].count(True) == 1 and all(r["exec_status"] == "ok" for r in runs)
    # Câu vừa promote chưa thuộc bộ đề published ⇒ người học chưa thấy
    assert client.get(f"/api/v1/questions/{q['question_id']}", headers=learner_h).status_code == 404
    from conftest import set_week_target
    set_week_target(client, admin_h, 1, 0, 0)
    sid = client.post("/api/v1/admin/weekly-sets", json={"week_start": "2026-10-19"}, headers=admin_h).json()["set_id"]
    assert client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h).status_code == 200
    lst = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert lst["total"] == 1 and lst["items"][0]["question_id"] == q["question_id"]
    detail = client.get(f"/api/v1/questions/{q['question_id']}", headers=learner_h)
    assert detail.status_code == 200
    text = detail.text
    assert "reference_sql" not in text and "expected" not in text and "SELECT employee_id" not in text
    # Admin thấy bằng chứng đầy đủ
    adm = client.get(f"/api/v1/admin/questions/{q['question_id']}", headers=admin_h).json()
    assert adm["test_cases"][0]["row_count"] and adm["reference_sql"]
    dd = client.get("/api/v1/admin/drafts/1", headers=admin_h).json()
    assert [l["stage"] for l in dd["review_logs"]][-1] == "decision" and dd["promoted_question"]["question_id"] == q["question_id"]


def test_job_progress_endpoint(client, admin_id, admin_h):
    eng.set_transport(FakeOllama())
    job_id = enqueue_job(admin_id)
    new_worker().run_once()
    j = client.get(f"/api/v1/admin/generation-jobs/{job_id}", headers=admin_h).json()
    assert j["status"] == "done" and j["created_count"] == 1 and j["drafts_by_status"] == {"approved": 1}
    assert {c["stage"] for c in j["llm_calls"]} == {"model_a", "solve_b", "checklist_b"}


def test_disagreeing_solvers_never_auto_approve(client, admin_id):
    eng.set_transport(FakeOllama(solver_sqls=[GOOD_SQL, GOOD_SQL, WRONG_SQL]))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d = db.q1(conn, "SELECT status, status_reason, reference_sql FROM draft.question_drafts")
        assert db.q1(conn, "SELECT count(*) n FROM live.questions")["n"] == 0
    assert d["status"] == "needs_human" and "consensus_disagreement" in d["status_reason"] and d["reference_sql"] is None


def test_semantic_auditor_flag_blocks_approval(admin_id):
    bad = {**AUDIT_PASS, "verdict": "needs_human", "issues": ["Đề mơ hồ về mốc thời gian"]}
    eng.set_transport(FakeOllama(audit=bad))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        assert db.q1(conn, "SELECT status FROM draft.question_drafts")["status"] == "needs_human"
        assert db.q1(conn, "SELECT count(*) n FROM live.questions")["n"] == 0


def test_model_a_invalid_output_fails_slot_not_draft(admin_id):
    eng.set_transport(FakeOllama(model_a={"title": "x"}))          # thiếu gần hết trường → không qua Blueprint gate
    job_id = enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        j = db.q1(conn, "SELECT status, created_count, failed_count FROM draft.generation_jobs WHERE job_id=:j", j=job_id)
        assert db.q1(conn, "SELECT count(*) n FROM draft.question_drafts")["n"] == 0
    assert (j["status"], j["created_count"], j["failed_count"]) == ("done", 0, 1)


def test_duplicate_of_existing_source_is_flagged(admin_id):
    """Đề gần như trùng ENT-005 (đề nguồn) phải bị phát hiện trùng → không auto-approve."""
    from fakes import MODEL_A_GOOD
    dup = {**MODEL_A_GOOD, "title": "Sản phẩm đang bán giá niêm yết từ 1 triệu", "business_domain": "Product & Inventory",
           "question": ("Liệt kê sản phẩm is_active=true có list_price >= 1000000. Cột kết quả theo thứ tự: product_id, product_name, sku, list_price, cost_price. "
                        "Sắp xếp: list_price giảm dần, product_id tăng."),
           "tables_used": ["products"], "output_columns": ["product_id", "product_name", "sku", "list_price", "cost_price"],
           "required_columns": {"products": ["product_id", "product_name", "sku", "list_price", "cost_price", "is_active"]},
           "table_roles": {"products": "Bảng sản phẩm"}}
    sql = "SELECT product_id, product_name, sku, list_price, cost_price FROM products WHERE is_active = true AND list_price >= 1000000 ORDER BY list_price DESC, product_id"
    eng.set_transport(FakeOllama(model_a=dup, solver_sqls=[sql]))
    enqueue_job(admin_id, topic="Product & Inventory")
    new_worker().run_once()
    with db.begin() as conn:
        d = db.q1(conn, "SELECT status, status_reason FROM draft.question_drafts")
    assert d["status"] != "approved"                                  # không bao giờ tự xuất bản bản sao của đề nguồn
