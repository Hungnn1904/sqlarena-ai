"""TDD Regression Suite cho phản hồi của nhóm (Đạt & Hưng) và các lỗi ngầm phát hiện qua /mykit:review."""
from datetime import date, timedelta

from conftest import enqueue_job, make_question, new_worker
from fakes import FakeOllama

from app import db
from app.pipeline import engine as eng


def test_learner_code_search_exact_position_never_matches_internal_question_id_or_prefix(client, learner_h):
    """Tìm 'sql2', 'SQL02', '#2', '2' chỉ khớp đúng bài ở position=2 (SQL2), không dính position=20/22 hay câu có question_id=2 ở vị trí khác."""
    q_first = make_question(1, title="Nhân viên không có quản lý trực tiếp")
    q_second = make_question(1, title="Danh bạ địa chỉ mặc định")
    q_third = make_question(1, title="Quy mô khách hàng theo trạng thái")
    q_twenty = make_question(2, title="Chuỗi tăng lương liên tiếp")

    # Đặt q_second (có question_id == 2) sang position=9 (SQL9), còn q_third đặt ở position=2 (SQL2), q_twenty ở position=20 (SQL20)
    with db.begin() as conn:
        ws = db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Tuần Kiểm Thử Search', :ws, 'published', now()) RETURNING set_id",
            ws=date.today() - timedelta(days=date.today().weekday()),
        )
        db.ex(
            conn,
            "INSERT INTO live.weekly_set_items (set_id, question_id, position) "
            "VALUES (:s, :q1, 1), (:s, :q3, 2), (:s, :q2, 9), (:s, :q20, 20)",
            s=ws["set_id"],
            q1=q_first,
            q3=q_third,
            q2=q_second,
            q20=q_twenty,
        )

    assert q_second == 2 and q_third != 2

    for query in ("sql2", "SQL2", "SQL02", "#2", "2"):
        res = client.get("/api/v1/weekly/current/questions", params={"q": query}, headers=learner_h)
        assert res.status_code == 200
        items = res.json()["items"]
        assert [(it["position"], it["question_id"]) for it in items] == [(2, q_third)], f"Query={query!r} returned {items}"


def test_reapprove_draft_with_custom_sql_refreshes_live_test_cases_for_grading(client, admin_id, admin_h, learner_h):
    """Khi trả draft từ approved -> needs_human rồi approve lại kèm custom_sql mới, live.test_cases phải cập nhật đáp án mới."""
    with db.begin() as conn:
        db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Tuần Chấm Lại', :ws, 'published', now()) RETURNING set_id",
            ws=date.today() - timedelta(days=date.today().weekday()),
        )

    eng.set_transport(FakeOllama())
    enqueue_job(admin_id)
    stats = new_worker().run_once()
    assert stats["reviewed"] == [(1, "approved")]

    ret = client.post("/api/v1/admin/drafts/1/return-needs-human", headers=admin_h, json={"note": "Đổi câu SQL chuẩn"})
    assert ret.status_code == 200

    new_sql = "SELECT category_id FROM categories ORDER BY category_id ASC LIMIT 2"
    re_app = client.post(
        "/api/v1/admin/drafts/1/approve",
        headers=admin_h,
        json={"note": "Duyệt với đáp án 2 dòng", "custom_sql": new_sql},
    )
    assert re_app.status_code == 200, re_app.text
    qid = re_app.json()["promoted_question"]["question_id"]

    sub = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": new_sql},
    )
    assert sub.status_code in (200, 201), sub.text
    assert sub.json()["submission_status"] == "passed", sub.json()


def test_group_publish_new_weekly_set_allows_auto_published_approved_drafts(client, admin_id, admin_h, learner_h):
    """Câu hỏi vừa được AI/Admin approve (đã tự gắn vào tuần hiện tại) vẫn gom nhóm tạo Bộ đề tuần mới được mà không văng 409."""
    q_old = make_question(1, title="Câu tuần cũ")
    with db.begin() as conn:
        ws = db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Tuần Cũ Đang Mở', :ws, 'published', now()) RETURNING set_id",
            ws=date.today() - timedelta(days=date.today().weekday()),
        )
        db.ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, 1)", s=ws["set_id"], q=q_old)

    eng.set_transport(FakeOllama())
    enqueue_job(admin_id)
    new_worker().run_once()

    with db.begin() as conn:
        q_approved = db.q1(conn, "SELECT question_id FROM live.questions WHERE source_draft_id = 1")["question_id"]

    grp = client.post(
        "/api/v1/admin/question-groups",
        headers=admin_h,
        json={"name": "Nhóm Đề Tuần Mới", "question_ids": [q_approved]},
    )
    assert grp.status_code == 201
    gid = grp.json()["group_id"]

    pub = client.post(
        f"/api/v1/admin/question-groups/{gid}/publish",
        headers=admin_h,
        json={"mode": "new_weekly_set", "set_title": "Tuần Mới Từ Approved Pool"},
    )
    assert pub.status_code == 200, pub.text
    cur = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [(it["position"], it["question_id"]) for it in cur["items"]] == [(1, q_approved)]
