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
