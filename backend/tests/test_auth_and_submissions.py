"""Kiểm thử tích hợp Auth, User Management, SQL Sandbox, Submission Grading, Progress & Leaderboard trên PostgreSQL thật."""
import json
from datetime import date

from app import db


def _seed_question_with_expected(conn) -> int:
    w = db.q1(conn, "SELECT world_id FROM core.worlds LIMIT 1")["world_id"]
    qrow = db.q1(conn, """INSERT INTO live.questions
                          (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text, status, is_source)
                          VALUES (:w, 'Đếm tổng số danh mục', 'Trả về tổng số dòng của bảng categories với cột cnt',
                                  'SELECT COUNT(*)::int AS cnt FROM categories', 'ordered', 1, ARRAY[1], ARRAY['categories'], 'categories(category_id)', 'ready', true)
                          RETURNING question_id""", w=w)
    qid = qrow["question_id"]
    from app.services import submissions
    res = submissions.execute_sandbox_sql("SELECT COUNT(*)::int AS cnt FROM categories")
    assert res["row_count"] == 1
    exp = json.dumps({"columns": res["columns"], "rows": res["rows"], "row_count": res["row_count"], "compare_mode": "ordered"})
    db.ex(conn, """INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result, is_hidden)
                   VALUES (:q, 'enterprise/base', 1, 'standard', CAST(:e AS jsonb), false)""", q=qid, e=exp)
    ws = db.q1(conn, """INSERT INTO live.weekly_sets (title, week_start, status, published_at)
                        VALUES ('Tuần Test', :ws, 'published', now()) RETURNING set_id""", ws=date(2026, 10, 26))
    db.ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, 1)", s=ws["set_id"], q=qid)
    return qid


def test_auth_register_login_profile_and_admin_users(client, admin_h):
    # 1. Register new learner
    r = client.post("/api/v1/auth/register", json={
        "email": "newbie@ptit.edu.vn",
        "username": "newbie_ptit",
        "password": "secret123",
        "display_name": "Tân Sinh Viên PTIT"
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["access_token"]
    assert data["user"]["role"] == "learner"
    token = data["access_token"]
    uh = {"Authorization": f"Bearer {token}"}

    # 2. Login with username or email
    r2 = client.post("/api/v1/auth/login", json={"identifier": "newbie_ptit", "password": "secret123"})
    assert r2.status_code == 200
    assert r2.json()["user"]["email"] == "newbie@ptit.edu.vn"

    # 3. Get & Update profile
    me = client.get("/api/v1/auth/me", headers=uh)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Tân Sinh Viên PTIT"

    up = client.put("/api/v1/auth/me", headers=uh, json={"display_name": "Nguyên PTIT Pro", "bio": "SQL Master"})
    assert up.status_code == 200
    assert up.json()["bio"] == "SQL Master"

    # 4. Change password
    cp = client.post("/api/v1/auth/change-password", headers=uh, json={"current_password": "secret123", "new_password": "newpassword456"})
    assert cp.status_code == 200
    r3 = client.post("/api/v1/auth/login", json={"identifier": "newbie@ptit.edu.vn", "password": "newpassword456"})
    assert r3.status_code == 200

    # 5. Admin list & update user
    ul = client.get("/api/v1/admin/users?q=newbie", headers=admin_h)
    assert ul.status_code == 200
    assert ul.json()["total"] >= 1
    uid = data["user"]["user_id"]
    adm_up = client.patch(f"/api/v1/admin/users/{uid}", headers=admin_h, json={"status": "locked"})
    assert adm_up.status_code == 200
    assert adm_up.json()["status"] == "locked"


def test_sql_sandbox_grading_progress_and_leaderboard(client, learner_h):
    with db.begin() as conn:
        qid = _seed_question_with_expected(conn)

    # 1. Run SQL Sandbox (valid SELECT vs blocked DML)
    run_ok = client.post("/api/v1/sql/run", headers=learner_h, json={"sql": "SELECT COUNT(*)::int AS cnt FROM categories", "question_id": qid})
    assert run_ok.status_code == 200
    assert run_ok.json()["passed_policy"] is True
    assert run_ok.json()["row_count"] == 1

    run_bad = client.post("/api/v1/sql/run", headers=learner_h, json={"sql": "DROP TABLE categories", "question_id": qid})
    assert run_bad.status_code == 400

    # 2. Submit wrong SQL -> failed
    sub_fail = client.post("/api/v1/submissions", headers=learner_h, json={"sql": "SELECT 0 AS cnt", "question_id": qid})
    assert sub_fail.status_code == 200
    assert sub_fail.json()["submission_status"] == "failed"
    assert sub_fail.json()["score"] == 0

    # 3. Submit correct SQL -> passed (100 points)
    sub_pass = client.post("/api/v1/submissions", headers=learner_h, json={"sql": "SELECT COUNT(*)::int AS cnt FROM categories", "question_id": qid})
    assert sub_pass.status_code == 200
    assert sub_pass.json()["submission_status"] == "passed"
    assert sub_pass.json()["score"] == 100

    # 4. Check weekly set question solved flag
    wq = client.get("/api/v1/weekly/current/questions", headers=learner_h)
    assert wq.status_code == 200
    assert wq.json()["items"][0]["solved"] is True

    # 5. Check progress & leaderboards
    prog = client.get("/api/v1/progress", headers=learner_h)
    assert prog.status_code == 200
    prog_data = prog.json()
    assert prog_data["summary"]["solved_questions"] == 1
    assert "career" in prog_data
    assert prog_data["career"]["xp"] > 0
    assert prog_data["career"]["level"] >= 1
    assert len(prog_data["career"]["badges"]) >= 5

    # 6. Check Explain Plan, Per-Question Submission History & AI SQL Coach (3 modes)
    exp_res = client.post("/api/v1/sql/explain", headers=learner_h, json={"sql": "SELECT COUNT(*)::int AS cnt FROM categories", "question_id": qid})
    assert exp_res.status_code == 200
    assert "plan_nodes" in exp_res.json()

    hist_res = client.get(f"/api/v1/questions/{qid}/submissions", headers=learner_h)
    assert hist_res.status_code == 200
    assert len(hist_res.json()["items"]) == 2

    for mode in ("review", "nl2sql", "interview"):
        coach_res = client.post(
            "/api/v1/sql/ai-coach",
            headers=learner_h,
            json={"question_id": qid, "sql": "SELECT * FROM categories", "mode": mode, "prompt": "Đếm tổng số danh mục"},
        )
        assert coach_res.status_code == 200
        cdata = coach_res.json()
        assert cdata["mode"] == mode
        assert cdata["clean_score"] > 0
        assert cdata["suggested_sql"]
        if mode == "interview":
            assert cdata["interview_q"]
            assert cdata["interview_answer"]

    lb_w = client.get("/api/v1/leaderboard/weekly", headers=learner_h)
    assert lb_w.status_code == 200
    assert len(lb_w.json()["items"]) == 1
    assert lb_w.json()["items"][0]["total_score"] == 100

    lb_m = client.get("/api/v1/leaderboard/monthly", headers=learner_h)
    assert lb_m.status_code == 200
    assert len(lb_m.json()["items"]) == 1
