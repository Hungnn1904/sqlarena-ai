"""TDD Regression Suite cho phản hồi của nhóm (Đạt & Hưng) và các lỗi ngầm phát hiện qua /mykit:review."""
from datetime import date, timedelta

from conftest import enqueue_job, make_question, new_worker
from fakes import FakeOllama

from app import db
from app.pipeline import engine as eng
from app.services import auth


def test_auth_verify_password_never_accepts_hardcoded_plaintext_fallbacks():
    """Xác thực mật khẩu bắt buộc qua băm PBKDF2-HMAC-SHA256 thật trong DB, tuyệt đối không có mật khẩu mặc định cứng."""
    real_hash = auth.hash_password("mat_khau_that_2026")
    assert auth.verify_password("mat_khau_that_2026", real_hash) is True
    assert auth.verify_password("admin123", real_hash) is False
    assert auth.verify_password("admin123", "legacy_non_pbkdf2_value") is False
    assert auth.verify_password("demo123", "x") is False
    assert auth.verify_password("123456", "x") is False


def test_learner_code_search_exact_position_never_matches_internal_question_id_or_prefix(client, learner_h):
    """Lọc từ khóa '2' / 'sql2' khớp mọi bản ghi hiển thị có chứa từ khóa (SQL2, SQL20, SQL23, SQL24, tiêu đề), nhưng KHÔNG dính ngầm question_id=2 ở SQL9."""
    q_first = make_question(1, title="Nhân viên không có quản lý trực tiếp")
    q_second = make_question(1, title="Danh bạ địa chỉ mặc định")
    q_third = make_question(1, title="Quy mô khách hàng theo trạng thái")
    q_twenty = make_question(2, title="Chuỗi tăng lương liên tiếp")
    q_twenty_three = make_question(2, title="Doanh thu thuần theo chi nhánh")
    q_twenty_four = make_question(3, title="Tỷ trọng đơn hoàn trả")

    # Đặt q_second (có question_id == 2) sang position=9 (SQL9); các bài 2, 20, 23, 24 đều chứa chữ số '2' trên mã hiển thị
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
            "VALUES (:s, :q1, 1), (:s, :q3, 2), (:s, :q2, 9), (:s, :q20, 20), (:s, :q23, 23), (:s, :q24, 24)",
            s=ws["set_id"],
            q1=q_first,
            q3=q_third,
            q2=q_second,
            q20=q_twenty,
            q23=q_twenty_three,
            q24=q_twenty_four,
        )

    assert q_second == 2 and q_third != 2

    for query in ("2", "sql2", "SQL2"):
        res = client.get("/api/v1/weekly/current/questions", params={"q": query}, headers=learner_h)
        assert res.status_code == 200
        items = res.json()["items"]
        positions = [it["position"] for it in items]
        assert positions == [2, 20, 23, 24], f"Query={query!r} returned positions={positions}"
        assert all(it["question_id"] != q_second for it in items)

    # Tìm nhiều từ kết hợp (số thứ tự + từ trong tiêu đề)
    combo = client.get("/api/v1/weekly/current/questions", params={"q": "23 doanh thu"}, headers=learner_h)
    assert combo.status_code == 200
    assert [it["position"] for it in combo.json()["items"]] == [23]


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


def test_unpromoted_approved_draft_adds_into_group_and_publishes_cleanly(client, admin_id, admin_h, learner_h):
    """Bản nháp có status='approved' sẵn trong DB (như Nháp #45 chưa có dòng live.questions) khi bấm + Thêm / + Tạo nhóm phải tự động promote thành câu hỏi ready và đưa vào nhóm."""
    with db.begin() as conn:
        world_id = db.q1(conn, "SELECT world_id FROM core.worlds LIMIT 1")["world_id"]
        job = db.q1(
            conn,
            "INSERT INTO draft.generation_jobs (world_id, triggered_by, difficulty, skill_ids, topic, requested_count, created_count, status) "
            "VALUES (:w, :u, 1, ARRAY[1], 'Sản phẩm đang hoạt động', 2, 2, 'done') RETURNING job_id",
            w=world_id,
            u=admin_id,
        )
        d1 = db.q1(
            conn,
            """INSERT INTO draft.question_drafts
               (world_id, job_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, validation_report, status, status_reason, gen_model, gen_prompt_version)
               VALUES (:w, :j, 'Liệt kê tên sản phẩm đang hoạt động', 'Trả về product_id, product_name của sản phẩm is_active = true',
                       'SELECT product_id, product_name FROM products WHERE is_active = true ORDER BY product_id ASC LIMIT 5',
                       'ordered', 1, ARRAY[1], '{}'::jsonb, ARRAY['products'], '', '{}'::jsonb, 'approved', 'legacy_approved', 'Model A', 'v2')
               RETURNING draft_id""",
            w=world_id,
            j=job["job_id"],
        )["draft_id"]
        d2 = db.q1(
            conn,
            """INSERT INTO draft.question_drafts
               (world_id, job_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, blueprint, tables_used, schema_text, validation_report, status, status_reason, gen_model, gen_prompt_version)
               VALUES (:w, :j, 'Liệt kê khách hàng có trạng thái active', 'Trả về customer_id, full_name của khách hàng active',
                       'SELECT customer_id, full_name FROM customers WHERE status = ''active'' ORDER BY customer_id ASC LIMIT 5',
                       'ordered', 1, ARRAY[1], '{}'::jsonb, ARRAY['customers'], '', '{}'::jsonb, 'approved', 'legacy_approved', 'Model A', 'v2')
               RETURNING draft_id""",
            w=world_id,
            j=job["job_id"],
        )["draft_id"]

    grp = client.post(
        "/api/v1/admin/question-groups",
        headers=admin_h,
        json={"name": "SQL tuần 6", "draft_ids": [d1]},
    )
    assert grp.status_code == 201, grp.text
    assert grp.json()["question_count"] == 1
    gid = grp.json()["group_id"]

    added = client.post(
        f"/api/v1/admin/question-groups/{gid}/add-items",
        headers=admin_h,
        json={"draft_ids": [d2]},
    )
    assert added.status_code == 200, added.text
    assert added.json()["question_count"] == 2

    pub = client.post(
        f"/api/v1/admin/question-groups/{gid}/publish",
        headers=admin_h,
        json={"mode": "new_weekly_set", "set_title": "SQL tuần 6"},
    )
    assert pub.status_code == 200, pub.text
    lq = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert len(lq["items"]) == 2


def test_runtime_schema_self_heals_missing_question_groups_and_preserves_cors_on_errors(client, admin_h):
    """Nếu DB local chưa chạy migration 0004 (thiếu live.question_groups), ensure_runtime_schema() tự tạo bảng để không bao giờ văng Network Error."""
    from app.db import ensure_runtime_schema

    with db.begin() as conn:
        db.ex(conn, "DROP TABLE IF EXISTS live.question_group_items, live.question_groups CASCADE")

    ensure_runtime_schema()

    res = client.post(
        "/api/v1/admin/question-groups",
        headers={**admin_h, "Origin": "http://localhost:3000"},
        json={"name": "SQL tuần 6"},
    )
    assert res.status_code == 201, res.text
    assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


def test_remove_item_from_published_or_draft_weekly_set_reindexes_cleanly(client, admin_h, learner_h):
    """Admin có thể gỡ trực tiếp 1 câu hỏi khỏi Bộ đề tuần đang mở (published) hoặc nháp (draft) và thứ tự SQL1..SQLN được đánh lại liên tục."""
    q1 = make_question(1, title="Bài 1")
    q2 = make_question(1, title="Bài 2")
    q3 = make_question(1, title="Bài 3")
    with db.begin() as conn:
        ws = db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Bộ đề tuần 6', :ws, 'published', now()) RETURNING set_id",
            ws=date.today() - timedelta(days=date.today().weekday()),
        )
        sid = ws["set_id"]
        db.ex(
            conn,
            "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q1, 1), (:s, :q2, 2), (:s, :q3, 3)",
            s=sid,
            q1=q1,
            q2=q2,
            q3=q3,
        )

    rm = client.delete(f"/api/v1/admin/weekly-sets/{sid}/items/{q2}", headers=admin_h)
    assert rm.status_code == 200, rm.text
    cur = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [(it["position"], it["question_id"]) for it in cur["items"]] == [(1, q1), (2, q3)]
