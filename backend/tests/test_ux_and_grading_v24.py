"""TDD v2.4: Admin User Detail Modal API, ORDER BY Prompt Synchronization & Multi-Test-Case Grading."""
import json
from datetime import date

from app import db


def _publish_ordered_categories_question(conn, *, with_sort_text: bool = False) -> int:
    w = db.q1(conn, "SELECT world_id, dataset_version FROM core.worlds LIMIT 1")
    from app.services import submissions

    ref_sql = "SELECT employee_id, full_name FROM employees ORDER BY employee_id ASC"
    res = submissions.execute_sandbox_sql(ref_sql)
    assert res["row_count"] >= 2
    q_text = (
        "Liệt kê mã nhân viên và họ tên nhân viên. Sắp xếp: employee_id tăng dần."
        if with_sort_text
        else "Liệt kê mã nhân viên (employee_id) và họ tên nhân viên (full_name) của tất cả nhân viên."
    )
    qrow = db.q1(
        conn,
        """INSERT INTO live.questions
           (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text, status, is_source)
           VALUES (:w, 'Danh sách danh mục', :qt, :sql, 'ordered', 1, ARRAY[1], ARRAY['employees'], 'employees(employee_id, full_name)', 'ready', false)
           RETURNING question_id""",
        w=w["world_id"],
        qt=q_text,
        sql=ref_sql,
    )
    qid = qrow["question_id"]
    exp = json.dumps(
        {
            "columns": res["columns"],
            "rows": [[submissions.json_value(r.get(c)) for c in res["columns"]] for r in res["rows"]],
            "row_count": res["row_count"],
            "compare_mode": "ordered",
        }
    )
    db.ex(
        conn,
        """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
           VALUES (:q, 'enterprise/base', :ver, 'standard', CAST(:e AS jsonb), false)""",
        q=qid,
        ver=w["dataset_version"],
        e=exp,
    )
    ws = db.q1(
        conn,
        """INSERT INTO live.weekly_sets (title, week_start, status, published_at)
           VALUES ('Bộ đề v2.4', :ws, 'published', now()) RETURNING set_id""",
        ws=date.today().replace(day=1),
    )
    db.ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, 1)", s=ws["set_id"], q=qid)
    return qid


def test_admin_user_detail_returns_profile_stats_and_recent_submissions(client, admin_h, learner_h):
    with db.begin() as conn:
        qid = _publish_ordered_categories_question(conn, with_sort_text=True)
        learner_uid = db.q1(conn, "SELECT user_id FROM live.users WHERE email='learner@test.io'")["user_id"]

    # Learner cannot access admin user detail
    assert client.get(f"/api/v1/admin/users/{learner_uid}", headers=learner_h).status_code == 403
    assert client.get("/api/v1/admin/users/999999", headers=admin_h).status_code == 404

    # Learner submits 1 wrong query and 1 passing query
    r_fail = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT employee_id, full_name FROM employees WHERE 1 = 0"},
    )
    assert r_fail.status_code == 200 and r_fail.json()["passed"] is False

    r_pass = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT employee_id, full_name FROM employees ORDER BY employee_id ASC"},
    )
    assert r_pass.status_code == 200 and r_pass.json()["passed"] is True

    detail = client.get(f"/api/v1/admin/users/{learner_uid}", headers=admin_h)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["user_id"] == learner_uid
    assert body["email"] == "learner@test.io"
    assert body["role"] == "learner"
    assert body["status"] == "active"
    assert body["stats"]["total_submissions"] == 2
    assert body["stats"]["passed_submissions"] == 1
    assert body["stats"]["failed_submissions"] == 1
    assert body["stats"]["solved_questions"] == 1
    assert body["stats"]["accuracy_percent"] == 50
    assert len(body["recent_submissions"]) == 2
    assert body["recent_submissions"][0]["question_title"] == "Danh sách danh mục"
    assert body["recent_submissions"][0]["submission_status"] == "passed"


def test_order_by_sync_on_manual_promotion_and_startup_heal(client, admin_h, learner_h, skill_id):
    # 1. Manual question WITH ORDER BY in SQL but missing sort instruction in Vietnamese prompt
    r_ord = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Nhân viên theo mã giảm dần",
            "question": "Liệt kê employee_id và full_name của toàn bộ nhân viên.",
            "reference_sql": "SELECT employee_id, full_name FROM employees ORDER BY employee_id DESC",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    )
    assert r_ord.status_code == 201, r_ord.text
    qid_ord = r_ord.json()["question_id"]
    adm_q = client.get(f"/api/v1/admin/questions/{qid_ord}", headers=admin_h).json()
    assert adm_q["compare_mode"] == "ordered"
    assert "sắp xếp" in adm_q["question"].lower()
    assert "employee_id" in adm_q["question"]
    assert "giảm dần" in adm_q["question"].lower()

    # 2. Manual question WITHOUT top-level ORDER BY normalizes compare_mode to 'unordered' even if caller passed 'ordered'
    r_unord = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Tập nhân viên không ràng buộc thứ tự",
            "question": "Liệt kê employee_id và full_name của toàn bộ nhân viên.",
            "reference_sql": "SELECT employee_id, full_name FROM employees",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
            "compare_mode": "ordered",
        },
    )
    assert r_unord.status_code == 201, r_unord.text
    qid_unord = r_unord.json()["question_id"]
    adm_unord = client.get(f"/api/v1/admin/questions/{qid_unord}", headers=admin_h).json()
    assert adm_unord["compare_mode"] == "unordered"

    # 3. Existing legacy question in DB missing sort text gets backfilled idempotently by ensure_runtime_schema()
    with db.begin() as conn:
        legacy_qid = _publish_ordered_categories_question(conn, with_sort_text=False)
    db.ensure_runtime_schema()
    db.ensure_runtime_schema()  # idempotent second call must not duplicate
    lq = client.get(f"/api/v1/questions/{legacy_qid}", headers=learner_h)
    assert lq.status_code == 200
    lq_text = lq.json()["question"]
    assert lq_text.lower().count("yêu cầu sắp xếp") == 1
    assert "employee_id" in lq_text and "tăng dần" in lq_text.lower()
    assert "expected" not in lq.text


def test_submissions_return_multi_testcase_verdicts_for_pass_wrong_order_and_syntax_error(client, learner_h):
    with db.begin() as conn:
        qid = _publish_ordered_categories_question(conn, with_sort_text=True)

    # 1. Passing submission -> >= 3 test cases, all True, labeled "Test case 1..3"
    ok = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT employee_id, full_name FROM employees ORDER BY employee_id ASC"},
    ).json()
    assert ok["passed"] is True
    assert len(ok["test_cases"]) >= 3
    assert [tc["label"] for tc in ok["test_cases"][:3]] == ["Test case 1", "Test case 2", "Test case 3"]
    assert all(tc["passed"] is True for tc in ok["test_cases"])
    assert ok["passed_tests"] == ok["total_tests"] == len(ok["test_cases"])

    # 2. Wrong order (same columns & same multiset rows, reversed ORDER BY) -> TC1 & TC2 pass, TC3 fails!
    wrong_order = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT employee_id, full_name FROM employees ORDER BY employee_id DESC"},
    ).json()
    assert wrong_order["passed"] is False
    assert len(wrong_order["test_cases"]) >= 3
    assert wrong_order["test_cases"][0]["passed"] is True
    assert wrong_order["test_cases"][1]["passed"] is True
    assert wrong_order["test_cases"][2]["passed"] is False

    # 3. Runtime SQL error (unknown column) -> still returns >= 3 test cases, all False!
    err_sub = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT missing_col FROM employees"},
    )
    assert err_sub.status_code == 200
    err_body = err_sub.json()
    assert err_body["passed"] is False
    assert len(err_body["test_cases"]) >= 3
    assert all(tc["passed"] is False for tc in err_body["test_cases"])
    # Zero answer leakage: "expected*" must never appear in learner submission payload
    assert "expected" not in err_sub.text
    assert "expected" not in json.dumps(ok)


def test_bola_unpublished_question_and_admin_self_demotion_and_sql_parser_edges(client, admin_h, learner_h, skill_id):
    from app.services.order_spec import extract_top_level_order_by

    # 1. SQL parser edge cases: comments, dollar-quotes, double-quoted identifiers, UNION
    assert extract_top_level_order_by("SELECT id FROM emp ORDER BY id ASC -- trailing comment with DESC\n") == [("id", "ASC")]
    assert extract_top_level_order_by("SELECT id FROM emp ORDER BY id DESC -- trailing comment") == [("id", "DESC")]
    assert extract_top_level_order_by("SELECT id FROM emp ORDER BY id /* inline comment */ DESC NULLS LAST") == [("id", "DESC")]
    assert extract_top_level_order_by("SELECT $$ORDER BY fake DESC$$ AS txt FROM emp") == []
    assert extract_top_level_order_by('SELECT id AS "ORDER BY" FROM emp') == []
    assert extract_top_level_order_by('SELECT id FROM emp ORDER BY "last, first" DESC') == [("last, first", "DESC")]
    assert extract_top_level_order_by("SELECT id FROM a ORDER BY id DESC UNION SELECT id FROM b") == []

    # 2. Unpublished question (not in any published weekly set) -> 404 on learner run & submit (BOLA guard)
    r_unpub = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Câu chưa phát hành lên kệ",
            "question": "Liệt kê employee_id từ bảng employees.",
            "reference_sql": "SELECT employee_id FROM employees",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    )
    assert r_unpub.status_code == 201
    unpub_qid = r_unpub.json()["question_id"]
    assert client.post("/api/v1/submissions", headers=learner_h, json={"question_id": unpub_qid, "sql": "SELECT employee_id FROM employees"}).status_code == 404
    assert client.post("/api/v1/sql/run", headers=learner_h, json={"question_id": unpub_qid, "sql": "SELECT employee_id FROM employees"}).status_code == 404

    # 3. Admin cannot self-demote to learner
    with db.begin() as conn:
        adm_uid = db.q1(conn, "SELECT user_id FROM live.users WHERE email='admin@test.io'")["user_id"]
    demote_res = client.patch(f"/api/v1/admin/users/{adm_uid}", headers=admin_h, json={"role": "learner"})
    assert demote_res.status_code == 400


def test_draft_live_progress_stepper_and_five_block_acceptance_dossier(client, admin_id, admin_h):
    """Kiểm chứng Phần 1 (thanh tiến trình 5 bước + thông số mẫu giải/vòng sửa/lỗi trực tiếp) và Phần 2 (Hồ sơ nghiệm thu 5 khối khi bấm Xem đề)."""
    from conftest import enqueue_job, new_worker
    from fakes import FakeOllama, GOOD_SQL, GOOD_SQL_ALT, MODEL_A_GOOD, WRONG_SQL
    from app.pipeline import engine as eng

    # 1. Draft #1: đạt chuẩn 5/5 công đoạn -> approved
    eng.set_transport(FakeOllama())
    enqueue_job(admin_id, quantity=1, difficulty=1, code="S1", topic="Human Resources")
    stats1 = new_worker().run_once()
    assert stats1["reviewed"] == [(1, "approved")]

    # 2. Draft #2: bất đồng kết quả giữa các mẫu giải -> tự sửa tối đa 2 vòng rồi dừng ở needs_human (consensus_disagreement)
    conflict_cand = {
        **MODEL_A_GOOD,
        "title": "Đối soát nhân sự đang làm việc kèm kiểm tra đồng thuận",
        "question": (
            "Liệt kê nhân viên có status='active' và hire_date >= 2024-02-01. "
            "Cột kết quả theo thứ tự: employee_id, full_name, job_title, hire_date. "
            "Sắp xếp: hire_date giảm dần, employee_id tăng."
        ),
        "logic_signature": {
            "output_grain": "Mỗi dòng 1 nhân sự",
            "analysis_goal": "Kiểm chứng hồ sơ nghiệm thu khi lệch đồng thuận",
            "filter_pattern": "status active tu 2024-02-01",
            "aggregation_pattern": "none",
        },
    }
    eng.set_transport(FakeOllama(model_a=conflict_cand, solver_sqls=[GOOD_SQL, GOOD_SQL_ALT, WRONG_SQL]))
    enqueue_job(admin_id, quantity=1, difficulty=1, code="S1", topic="Human Resources")
    stats2 = new_worker().run_once()
    assert stats2["reviewed"][0][1] == "needs_human"
    d2_id = stats2["reviewed"][0][0]

    # Giả lập thêm 1 dòng lỗi HTTP 403 trên llm_call_ledger cho draft #2 để kiểm chứng cảnh báo lỗi trực tiếp
    with db.begin() as conn:
        db.ex(
            conn,
            """INSERT INTO draft.llm_call_ledger
               (job_id, draft_id, stage, attempt_no, provider, model, prompt_name, prompt_version, prompt_hash, request_hash, status, error_code, latency_ms)
               VALUES (2, :d, 'solve_b', 9, 'ollama', 'qwen2.5-coder:7b', 'solve_b:s2_k3_r1', 'v1', 'ph', 'rh', 'failed', 'http_403_quota_exceeded', 420)""",
            d=d2_id,
        )

    # Kiểm tra Phần 1 trên GET /api/v1/admin/drafts
    lst = client.get("/api/v1/admin/drafts", headers=admin_h).json()["items"]
    by_id = {it["draft_id"]: it for it in lst}
    lp1 = by_id[1]["live_progress"]
    assert lp1["step"] == 5 and lp1["total_steps"] == 5
    assert lp1["samples_done"] >= 3 and lp1["samples_total"] == 3
    for banned in ("qwen", "llama", "deepseek", "ollama"):
        assert banned not in (lp1["active_model"] or "").lower()

    lp2 = by_id[d2_id]["live_progress"]
    assert lp2["error_alert"] and "403" in lp2["error_alert"]
    for banned in ("qwen", "llama", "deepseek", "ollama"):
        assert banned not in (lp2["active_model"] or "").lower()

    # Kiểm tra Phần 2 (5 khối hồ sơ nghiệm thu) trên GET /api/v1/admin/drafts/{id}
    det1 = client.get("/api/v1/admin/drafts/1", headers=admin_h).json()
    dos1 = det1["acceptance_dossier"]
    # Khối 1: Verdict
    assert dos1["verdict"]["status"] == "approved"
    assert dos1["verdict"]["compare_mode"] in ("ordered", "unordered")
    assert "5/5" in dos1["verdict"]["reason_summary"]
    # Khối 2: Originality
    orig1 = dos1["originality"]
    assert 0 <= orig1["similarity_pct"] <= 100
    assert round(orig1["similarity_pct"] + orig1["originality_pct"], 1) == 100.0
    assert orig1["exact_duplicate"] is False and orig1["logic_duplicate"] is False
    # Khối 3: Consensus & Matrix
    cons1 = dos1["consensus"]
    assert cons1["matching_count"] == 3 and cons1["total_samples"] == 3 and cons1["consensus_pct"] == 100.0
    assert any(s["is_selected"] and s.get("selection_reason") for s in cons1["samples"])
    assert all("result_hash" in s and "latency_ms" in s for s in cons1["samples"])
    # Khối 4: 6-point Checklist
    chk1 = dos1["checklist"]
    assert len(chk1) == 6
    assert all(c["passed"] is True for c in chk1)
    # Khối 5: Repair History & Pedagogical Traps
    rt1 = dos1["repair_and_traps"]
    assert isinstance(rt1["traps"], list) and len(rt1["traps"]) >= 1

    # Kiểm tra hồ sơ của Draft #2 (needs_human có lịch sử tự sửa vòng 1..2 + lý do consensus_disagreement)
    det2 = client.get(f"/api/v1/admin/drafts/{d2_id}", headers=admin_h).json()
    dos2 = det2["acceptance_dossier"]
    assert dos2["verdict"]["status"] == "needs_human"
    assert any(r["code"] == "consensus_disagreement" for r in dos2["verdict"]["reasons"])
    assert dos2["repair_and_traps"]["repair_history"]["attempted"] >= 1
    assert len(dos2["repair_and_traps"]["repair_history"]["rounds"]) >= 1

    # 3. Khi Admin phê duyệt Draft #2 bằng custom_sql hợp lệ -> chu kỳ review mới không bị nhiễm lỗi/vòng sửa cũ
    app_res = client.post(
        f"/api/v1/admin/drafts/{d2_id}/approve",
        headers=admin_h,
        json={"custom_sql": GOOD_SQL, "note": "Chuẩn hóa đáp án"},
    )
    assert app_res.status_code == 200
    dos2_after = client.get(f"/api/v1/admin/drafts/{d2_id}", headers=admin_h).json()["acceptance_dossier"]
    assert dos2_after["verdict"]["status"] == "approved"
    assert all(c["passed"] is True for c in dos2_after["checklist"])
    assert dos2_after["repair_and_traps"]["repair_history"]["attempted"] == 0

    # 4. In-sample retry trên vòng 0 (4 solver calls cho k=3 do sample 1 thử lại) -> repair_round vẫn bằng 0, samples_done = 3
    retry_cand = {
        **MODEL_A_GOOD,
        "title": "Tra cứu danh sách nhân sự chính thức sau đầu năm 2024",
        "question": (
            "Hiển thị nhân sự đang có status='active' gia nhập từ ngày 2024-01-01 trở đi. "
            "Cột kết quả theo thứ tự: employee_id, full_name, job_title, hire_date. "
            "Sắp xếp: hire_date giảm dần, employee_id tăng."
        ),
        "logic_signature": {
            "output_grain": "Một dòng cho mỗi nhân viên chính thức",
            "analysis_goal": "Kiểm chứng retry nội bộ trong cùng 1 mẫu giải",
            "filter_pattern": "status='active' AND hire_date >= 2024-01-01",
            "aggregation_pattern": "none",
        },
    }
    eng.set_transport(FakeOllama(model_a=retry_cand, solver_sqls=["SELECT broken_syntax FROM", GOOD_SQL, GOOD_SQL, GOOD_SQL]))
    enqueue_job(admin_id, quantity=1, difficulty=1, code="S1", topic="Human Resources")
    stats3 = new_worker().run_once()
    d3_id = stats3["reviewed"][0][0]
    lp3 = {it["draft_id"]: it for it in client.get("/api/v1/admin/drafts", headers=admin_h).json()["items"]}[d3_id]["live_progress"]
    assert lp3["repair_round"] == 0 and lp3["samples_done"] == 3

    # 5. Không rò rỉ tên local model (ollama/qwen/llama/deepseek) qua error_message của job hoặc sample error
    eng.set_transport(FakeOllama(fail_with=ValueError("err_ollama_down: qwen2.5 timeout")))
    fail_jid = enqueue_job(admin_id, quantity=2, difficulty=1, code="S1", topic="Human Resources")
    new_worker().run_once()
    jobs_payload = json.dumps(client.get("/api/v1/admin/generation-jobs", headers=admin_h).json()).lower()
    for banned in ("qwen", "llama", "deepseek", "ollama"):
        assert banned not in jobs_payload and fail_jid >= 1
