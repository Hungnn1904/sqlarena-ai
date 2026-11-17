"""TDD test suite cho Question Groups, Calibrated Review, Bulk Approve, Manual Question & Learner UX fixes."""
from datetime import date, timedelta

from conftest import enqueue_job, make_question, new_worker
from fakes import GOOD_SQL, MODEL_A_GOOD, WRONG_SQL, FakeOllama

from app import db
from app.pipeline import engine as eng
from app.seed import seed_demo_live


def test_approved_draft_does_not_auto_leak_into_published_weekly_set(client, admin_id, admin_h, learner_h):
    """Đề mới duyệt nằm ở kho câu hỏi ready, KHÔNG tự nhảy lẻ tẻ vào bộ đề tuần đang mở."""
    q_init = make_question(1, title="Câu mở đầu tuần")
    with db.begin() as conn:
        ws = db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Tuần Đang Mở', :ws, 'published', now()) RETURNING set_id",
            ws=date.today() - timedelta(days=date.today().weekday()),
        )
        db.ex(
            conn,
            "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, 1)",
            s=ws["set_id"],
            q=q_init,
        )

    eng.set_transport(FakeOllama())
    enqueue_job(admin_id)
    stats = new_worker().run_once()
    assert stats["reviewed"] == [(1, "approved")]

    with db.begin() as conn:
        promoted = db.q1(conn, "SELECT question_id, status FROM live.questions WHERE source_draft_id = 1")
    assert promoted["status"] == "ready"
    new_qid = promoted["question_id"]

    # Học viên chỉ thấy 1 câu ban đầu, KHÔNG thấy câu mới auto-leak
    cur = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert cur["total"] == 1 and [i["question_id"] for i in cur["items"]] == [q_init]
    assert client.get(f"/api/v1/questions/{new_qid}", headers=learner_h).status_code == 404

    # Admin lọc unassigned_only=true chỉ thấy câu mới chưa phát hành
    unassigned = client.get("/api/v1/admin/questions?unassigned_only=true", headers=admin_h)
    assert unassigned.status_code == 200
    u_items = unassigned.json()["items"]
    assert [i["question_id"] for i in u_items] == [new_qid]
    assert u_items[0]["in_weekly_set"] is False
    assert u_items[0]["in_published_set"] is False
    assert u_items[0]["group_ids"] == []

    all_q = {i["question_id"]: i for i in client.get("/api/v1/admin/questions", headers=admin_h).json()["items"]}
    assert all_q[q_init]["in_weekly_set"] is True and all_q[q_init]["in_published_set"] is True


def test_question_groups_crud_draft_auto_approve_and_publish_modes(client, admin_id, admin_h, learner_h, skill_id):
    """Luồng tạo đề thủ công, bulk-approve, gom nhóm nháp, sắp xếp và đăng hàng loạt (append_active & new_weekly_set)."""
    # 1. Tạo câu hỏi thủ công trực tiếp sang kho ready
    manual_res = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Thống kê tổng số danh mục hiện có",
            "question": "Viết truy vấn đếm tổng số dòng trong bảng categories với tên cột total_categories.",
            "reference_sql": "SELECT COUNT(*)::int AS total_categories FROM categories",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
            "compare_mode": "unordered",
        },
    )
    assert manual_res.status_code == 201, manual_res.text
    m_data = manual_res.json()
    assert m_data["status"] == "ready"
    assert m_data["output_columns"] == ["total_categories"]
    assert m_data["row_count"] == 1
    q_manual = m_data["question_id"]

    # 2. Tạo 2 bản nháp needs_human (do bất đồng solver), sau đó bulk-approve draft #1, và đưa draft #2 vào tạo nhóm luôn
    eng.set_transport(FakeOllama(solver_sqls=[GOOD_SQL, GOOD_SQL, WRONG_SQL]))
    enqueue_job(admin_id, quantity=1)
    new_worker().run_once()

    second_cand = {
        **MODEL_A_GOOD,
        "title": "Tra cứu nhân sự đang làm việc tuyển mới sau đầu năm 2024",
        "question": (
            "Cho biết các nhân viên có status='active' gia nhập từ ngày 2024-01-01. "
            "Cột kết quả theo thứ tự: employee_id, full_name, job_title, hire_date. "
            "Sắp xếp: hire_date giảm dần, employee_id tăng."
        ),
        "logic_signature": {
            "output_grain": "Từng nhân sự mới",
            "analysis_goal": "Kiểm kê nhân viên gia nhập năm 2024",
            "filter_pattern": "status='active' và hire_date >= 2024-01-01",
            "aggregation_pattern": "Dòng chi tiết",
        },
    }
    eng.set_transport(FakeOllama(model_a=second_cand, solver_sqls=[GOOD_SQL, GOOD_SQL, WRONG_SQL]))
    enqueue_job(admin_id, quantity=1)
    new_worker().run_once()
    with db.begin() as conn:
        draft_ids = [r["draft_id"] for r in db.q(conn, "SELECT draft_id FROM draft.question_drafts ORDER BY draft_id")]
    assert len(draft_ids) == 2

    bulk_res = client.post(
        "/api/v1/admin/drafts/bulk-approve",
        headers=admin_h,
        json={"draft_ids": [draft_ids[0]], "note": "Duyệt nhanh câu 1"},
    )
    assert bulk_res.status_code == 200, bulk_res.text
    b_data = bulk_res.json()
    assert b_data["approved_count"] == 1
    assert b_data["approved_draft_ids"] == [draft_ids[0]]
    q_from_bulk = b_data["question_ids"][0]

    # 3. Tạo nhóm nháp kèm cả question_ids và draft_ids (tự duyệt draft_ids[1])
    grp_res = client.post(
        "/api/v1/admin/question-groups",
        headers=admin_h,
        json={
            "name": "Nhóm kiểm tra SQL cơ bản",
            "description": "Đợt kiểm tra 15 phút đầu giờ",
            "question_ids": [q_manual, q_from_bulk],
            "draft_ids": [draft_ids[1]],
        },
    )
    assert grp_res.status_code == 201, grp_res.text
    grp = grp_res.json()
    gid = grp["group_id"]
    assert grp["status"] == "draft"
    assert grp["question_count"] == 3
    q_from_group_draft = grp["items"][2]["question_id"]
    assert [it["question_id"] for it in grp["items"]] == [q_manual, q_from_bulk, q_from_group_draft]

    # Kiểm tra group_ids xuất hiện trong admin_questions
    aq = {i["question_id"]: i for i in client.get("/api/v1/admin/questions", headers=admin_h).json()["items"]}
    assert gid in aq[q_manual]["group_ids"]

    # 4. PATCH sửa tên/mô tả + PUT làm rỗng rồi chặn publish nhóm rỗng
    patch_res = client.patch(
        f"/api/v1/admin/question-groups/{gid}",
        headers=admin_h,
        json={"name": "Nhóm SQL Cơ Bản (Đã chốt)", "description": "Gồm 3 câu chọn lọc"},
    )
    assert patch_res.status_code == 200 and patch_res.json()["name"] == "Nhóm SQL Cơ Bản (Đã chốt)"

    empty_put = client.put(f"/api/v1/admin/question-groups/{gid}/items", headers=admin_h, json={"question_ids": []})
    assert empty_put.status_code == 200 and empty_put.json()["question_count"] == 0
    pub_empty = client.post(f"/api/v1/admin/question-groups/{gid}/publish", headers=admin_h, json={"mode": "append_active"})
    assert pub_empty.status_code == 409 and pub_empty.json()["code"] == "EMPTY_GROUP"

    # Đặt lại 2 câu + nối thêm câu thứ 3 qua add-items (idempotent khi truyền trùng)
    put_res = client.put(
        f"/api/v1/admin/question-groups/{gid}/items",
        headers=admin_h,
        json={"question_ids": [q_from_bulk, q_manual]},
    )
    assert put_res.status_code == 200 and [i["question_id"] for i in put_res.json()["items"]] == [q_from_bulk, q_manual]

    add_res = client.post(
        f"/api/v1/admin/question-groups/{gid}/add-items",
        headers=admin_h,
        json={"question_ids": [q_manual, q_from_group_draft]},
    )
    assert add_res.status_code == 200
    assert [i["question_id"] for i in add_res.json()["items"]] == [q_from_bulk, q_manual, q_from_group_draft]

    # 5. Publish mode=append_active khi CHƯA có bộ đề nào đang mở -> tự tạo weekly_set mới và mở luôn
    pub1 = client.post(
        f"/api/v1/admin/question-groups/{gid}/publish",
        headers=admin_h,
        json={"mode": "append_active", "set_title": "Bộ đề Tuần Thực Hành 1"},
    )
    assert pub1.status_code == 200, pub1.text
    p1 = pub1.json()
    assert p1["published_count"] == 3 and p1["group"]["status"] == "published"
    assert p1["set_title"] == "Bộ đề Tuần Thực Hành 1"

    # Không cho xoá nhóm đã published
    del_pub = client.delete(f"/api/v1/admin/question-groups/{gid}", headers=admin_h)
    assert del_pub.status_code == 409 and del_pub.json()["code"] == "INVALID_STATE"

    # Học viên thấy ngay cả 3 câu theo đúng thứ tự
    lq1 = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [i["question_id"] for i in lq1["items"]] == [q_from_bulk, q_manual, q_from_group_draft]

    # 6. Tạo nhóm 2 và publish append_active -> nối tiếp vào bộ đang mở (vị trí 4, 5)
    q4, q5 = make_question(1, title="Câu nối 4"), make_question(2, title="Câu nối 5")
    g2 = client.post("/api/v1/admin/question-groups", headers=admin_h, json={"name": "Nhóm Bổ Sung", "question_ids": [q4, q5]}).json()
    pub2 = client.post(f"/api/v1/admin/question-groups/{g2['group_id']}/publish", headers=admin_h, json={"mode": "append_active"})
    assert pub2.status_code == 200 and pub2.json()["set_id"] == p1["set_id"] and pub2.json()["published_count"] == 2
    lq2 = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [i["question_id"] for i in lq2["items"]] == [q_from_bulk, q_manual, q_from_group_draft, q4, q5]

    # 7. Tạo nhóm 3 và publish mode=new_weekly_set -> đóng bộ cũ, mở bộ mới độc lập không đụng UNIQUE(week_start)
    q6 = make_question(1, title="Câu tuần mới")
    g3 = client.post("/api/v1/admin/question-groups", headers=admin_h, json={"name": "Đợt Thi Mới", "question_ids": [q6]}).json()
    pub3 = client.post(
        f"/api/v1/admin/question-groups/{g3['group_id']}/publish",
        headers=admin_h,
        json={"mode": "new_weekly_set", "set_title": "Tuần Thi Cuối Kỳ"},
    )
    assert pub3.status_code == 200, pub3.text
    assert pub3.json()["set_id"] != p1["set_id"]
    lq3 = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [i["question_id"] for i in lq3["items"]] == [q6]

    # 8. Tạo nhóm nháp 4 và xoá nhóm nháp
    g4 = client.post("/api/v1/admin/question-groups", headers=admin_h, json={"name": "Nhóm Tạm"}).json()
    del_ok = client.delete(f"/api/v1/admin/question-groups/{g4['group_id']}", headers=admin_h)
    assert del_ok.status_code == 200 and del_ok.json() == {"deleted": True, "group_id": g4["group_id"]}
    lst = client.get("/api/v1/admin/question-groups", headers=admin_h).json()
    assert lst["total"] == 3


def test_calibrated_review_approves_benign_formality_gaps_while_blocking_real_defects(client, admin_id, admin_h):
    """Chế độ calibrated duyệt mượt các lỗi hình thức vô hại nhưng vẫn chặn cứng lỗi sai kết quả/lệch tên cột tường minh/literal bịa."""
    settings_map = {i["key"]: i["value"] for i in client.get("/api/v1/admin/settings", headers=admin_h).json()["items"]}
    assert settings_map["review.approval_mode"] == "calibrated"
    assert client.put("/api/v1/admin/settings/review.approval_mode", json={"value": "invalid"}, headers=admin_h).status_code == 400

    # Đề tiếng Việt tự nhiên (không ép tên cột tiếng Anh), blueprint có output_columns khác alias SQL,
    # 1/3 mẫu solver lỗi cú pháp nhưng 2/3 mẫu hợp lệ đồng thuận tuyệt đối, auditor trả 2 checks gọn.
    natural_cand = {
        **MODEL_A_GOOD,
        "title": "Danh sách nhân sự đang hoạt động từ đầu năm 2024",
        "question": (
            "Tìm các nhân viên đang làm việc tại công ty được tuyển dụng từ ngày 2024-01-01 trở đi. "
            "Sắp xếp kết quả theo hire_date giảm dần."
        ),
        "output_columns": ["ma_nhan_vien", "ho_va_ten"],
    }
    sql_ok_1 = "SELECT employee_id, full_name, hire_date FROM employees WHERE status = 'active' AND hire_date >= DATE '2024-01-01' ORDER BY hire_date DESC, employee_id ASC"
    sql_ok_2 = "SELECT e.employee_id, e.full_name, e.hire_date FROM employees e WHERE e.hire_date >= DATE '2024-01-01' AND e.status = 'active' ORDER BY e.hire_date DESC, e.employee_id ASC"
    compact_audit = {
        "verdict": "pass",
        "issues": [],
        "checks": [
            {"requirement": "output columns / aliases", "status": "pass", "finding": "Hợp lệ"},
            {"requirement": "ordering & tie-breakers", "status": "pass", "finding": "Khớp yêu cầu"},
        ],
    }

    # Khi strict -> bị giữ ở needs_human
    client.put("/api/v1/admin/settings/review.approval_mode", json={"value": "strict"}, headers=admin_h)
    eng.set_transport(FakeOllama(model_a=natural_cand, solver_sqls=["SELECT FROM broken_syntax", sql_ok_1, sql_ok_2], audit=compact_audit))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d_strict = db.q1(conn, "SELECT status FROM draft.question_drafts ORDER BY draft_id DESC LIMIT 1")
    assert d_strict["status"] == "needs_human"

    # Khi calibrated -> được auto-approve!
    client.put("/api/v1/admin/settings/review.approval_mode", json={"value": "calibrated"}, headers=admin_h)
    natural_cand_2 = {
        **natural_cand,
        "title": "Nhân sự đang làm việc tuyển mới từ mốc 2024-01-01",
        "question": (
            "Hãy cho biết danh sách nhân viên đang làm việc vào công ty từ mốc 2024-01-01. "
            "Sắp xếp theo hire_date giảm dần."
        ),
        "logic_signature": {
            "output_grain": "Mỗi dòng 1 nhân sự mới",
            "analysis_goal": "Tra cứu nhân sự gia nhập từ 2024",
            "filter_pattern": "hire_date >= 2024-01-01",
            "aggregation_pattern": "Chi tiết dòng",
        },
    }
    eng.set_transport(FakeOllama(model_a=natural_cand_2, solver_sqls=["SELECT FROM broken_syntax", sql_ok_1, sql_ok_2], audit=compact_audit))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d_cal = db.q1(conn, "SELECT status, status_reason FROM draft.question_drafts ORDER BY draft_id DESC LIMIT 1")
    assert d_cal["status"] == "approved", d_cal

    # Nhưng nếu câu hỏi tiếng Việt GHI TƯỜNG MINH tên cột mà SQL trả lệch -> calibrated VẪN CHẶN!
    explicit_col_cand = {
        **MODEL_A_GOOD,
        "title": "Nhân viên mới kèm cột tường minh",
        "question": (
            "Liệt kê nhân viên có status='active' và hire_date >= 2024-01-01. "
            "Cột kết quả theo thứ tự: ma_nv, ten_nv. "
            "Sắp xếp: hire_date giảm dần, employee_id tăng."
        ),
        "output_columns": ["ma_nv", "ten_nv"],
        "logic_signature": {
            "output_grain": "Nhân viên cụ thể",
            "analysis_goal": "Đối chiếu tên cột bắt buộc",
            "filter_pattern": "status active 2024",
            "aggregation_pattern": "Không gom nhóm",
        },
    }
    eng.set_transport(FakeOllama(model_a=explicit_col_cand, solver_sqls=[GOOD_SQL, GOOD_SQL, GOOD_SQL], audit=compact_audit))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d_explicit = db.q1(conn, "SELECT status, status_reason FROM draft.question_drafts ORDER BY draft_id DESC LIMIT 1")
    assert d_explicit["status"] == "needs_human" and "output_columns_mismatch" in d_explicit["status_reason"]

    # Và nếu SQL bịa literal lạ không có trong đề -> calibrated VẪN CHẶN!
    invented_sql = "SELECT employee_id, full_name, hire_date FROM employees WHERE job_title <> 'PhantomRoleXYZ' AND hire_date >= DATE '2024-01-01' ORDER BY hire_date DESC, employee_id ASC"
    invented_cand = {
        **natural_cand,
        "title": "Kiểm tra chặn literal bịa đặt",
        "question": "Tìm danh sách nhân sự gia nhập từ ngày 2024-01-01 trở về sau. Sắp xếp theo hire_date giảm dần.",
        "logic_signature": {
            "output_grain": "Một dòng nhân sự",
            "analysis_goal": "Phát hiện literal tự chế",
            "filter_pattern": "hire_date từ đầu 2024",
            "aggregation_pattern": "Trực tiếp",
        },
    }
    eng.set_transport(FakeOllama(model_a=invented_cand, solver_sqls=[invented_sql, invented_sql, invented_sql], audit=compact_audit))
    enqueue_job(admin_id)
    new_worker().run_once()
    with db.begin() as conn:
        d_inv = db.q1(conn, "SELECT status, status_reason FROM draft.question_drafts ORDER BY draft_id DESC LIMIT 1")
    assert d_inv["status"] == "needs_human" and "unstated_string_literal" in d_inv["status_reason"]


def test_admin_approve_rejected_and_custom_sql(client, admin_id, admin_h):
    """Admin có thể cứu một draft bị rejected/needs_human bằng cách truyền custom_sql hợp lệ."""
    eng.set_transport(FakeOllama(solver_sqls=[GOOD_SQL, GOOD_SQL, WRONG_SQL]))
    enqueue_job(admin_id)
    new_worker().run_once()
    rej = client.post("/api/v1/admin/drafts/1/reject", headers=admin_h, json={"reason": "Tạm từ chối để viết lại đáp án"})
    assert rej.status_code == 200 and rej.json()["status"] == "rejected"

    app_res = client.post(
        "/api/v1/admin/drafts/1/approve",
        headers=admin_h,
        json={"custom_sql": GOOD_SQL, "note": "Admin cấp đáp án chuẩn"},
    )
    assert app_res.status_code == 200, app_res.text
    assert app_res.json()["status"] == "approved"
    assert app_res.json()["promoted_question"]["status"] == "ready"


def test_learner_output_columns_sql_comments_and_monthly_rollover(client, admin_h, learner_h, skill_id):
    """Kiểm tra output_columns không lộ expected, cho phép comment SQL trong sandbox, và BXH tháng đầu tháng mới."""
    m_res = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Đếm danh mục có comment",
            "question": "Đếm tổng số danh mục trong bảng categories thành cột cnt.",
            "reference_sql": "SELECT COUNT(*)::int AS cnt FROM categories",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    )
    qid = m_res.json()["question_id"]

    # Đặt bộ đề tuần có week_start ở tháng trước nhưng vẫn đang published sang tháng hiện tại
    today = date.today()
    prev_month_day = today.replace(day=1) - timedelta(days=5)
    prev_monday = prev_month_day - timedelta(days=prev_month_day.weekday())
    with db.begin() as conn:
        ws = db.q1(
            conn,
            "INSERT INTO live.weekly_sets (title, week_start, status, published_at) "
            "VALUES ('Bộ đề giao thoa cuối tháng', :ws, 'published', now()) RETURNING set_id",
            ws=prev_monday,
        )
        db.ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, 1)", s=ws["set_id"], q=qid)

    q_det = client.get(f"/api/v1/questions/{qid}", headers=learner_h)
    assert q_det.status_code == 200
    assert q_det.json()["output_columns"] == ["cnt"]
    assert "expected" not in q_det.text and "reference_sql" not in q_det.text

    commented_sql = """
    /* Bài làm của sinh viên PTIT */
    SELECT COUNT(*)::int AS cnt -- đếm tổng danh mục
    FROM categories;
    """
    run_res = client.post("/api/v1/sql/run", headers=learner_h, json={"question_id": qid, "sql": commented_sql})
    assert run_res.status_code == 200, run_res.text
    assert run_res.json()["passed_policy"] is True

    sub_res = client.post("/api/v1/submissions", headers=learner_h, json={"question_id": qid, "sql": commented_sql})
    assert sub_res.status_code == 200 and sub_res.json()["submission_status"] == "passed"

    lb_m = client.get("/api/v1/leaderboard/monthly", headers=learner_h)
    assert lb_m.status_code == 200
    assert len(lb_m.json()["items"]) == 1
    assert lb_m.json()["items"][0]["total_score"] == 100


def test_seed_demo_live_creates_sample_draft_question_group():
    """seed_demo_live tạo sẵn 1 nhóm đề mẫu trạng thái draft gồm 4 câu ready chưa gán vào weekly_set_items."""
    with db.begin() as conn:
        seed_demo_live(conn)
        grp = db.q1(
            conn,
            "SELECT * FROM live.question_groups WHERE name = 'Nhóm đề Thực hành JOIN & Doanh thu (Chờ đăng)'",
        )
        assert grp is not None and grp["status"] == "draft"
        items = db.q(
            conn,
            """SELECT gi.position, q.question_id, q.status,
                      EXISTS (SELECT 1 FROM live.weekly_set_items wsi WHERE wsi.question_id = q.question_id) AS in_ws
               FROM live.question_group_items gi
               JOIN live.questions q USING (question_id)
               WHERE gi.group_id = :g ORDER BY gi.position""",
            g=grp["group_id"],
        )
    assert len(items) == 4
    assert all(it["status"] == "ready" and not it["in_ws"] for it in items)
    with db.begin() as conn:
        db.ex(conn, "DELETE FROM live.submissions")
        db.ex(conn, "DELETE FROM live.users WHERE email LIKE '%@sqlarena.local'")


def test_normalize_candidate_fills_fk_and_table_roles_only_for_valid_skeleton():
    """Tự động bù table_roles + join_relations + cột FK cho Model A nhưng giữ nguyên nếu candidate rỗng/hỏng."""
    from app.pipeline.catalog import load_engine_data
    from app.pipeline.generation import normalize_candidate_for_validation

    with db.begin() as conn:
        data = load_engine_data(conn, "enterprise_v1")
    ws = {**data["world"]["schema_description"], "fk_relations": data["world"]["fk_relations"]}

    # Candidate thiếu các trường gốc bắt buộc -> giữ nguyên không tự bịa
    broken = {"title": "x"}
    assert normalize_candidate_for_validation(broken, ws) == {"title": "x"}

    # Candidate hợp lệ nhưng quên table_roles, join_relations và cột customer_id trong required_columns
    cand = {
        "title": "Thống kê tổng chi tiêu khách hàng",
        "question": "Tìm tổng giá trị đơn hàng của từng khách hàng.",
        "tables_used": ["customers", "orders"],
        "required_columns": {"customers": ["full_name"], "orders": ["order_id", "total_amount"]},
    }
    norm = normalize_candidate_for_validation(cand, ws)
    assert set(norm["table_roles"].keys()) == {"customers", "orders"}
    assert len(norm["join_relations"]) == 1
    assert "customer_id" in norm["required_columns"]["customers"]
    assert "customer_id" in norm["required_columns"]["orders"]


def test_apithat_gateway_status_and_secret_blind_key_vault(client, admin_h, learner_h, monkeypatch):
    """Secret-Blind Vault cho apithat.dev: xác thực key, lưu runtime, không bao giờ lộ plaintext key qua API hay audit log."""
    assert client.get("/api/v1/admin/gateway-status", headers=learner_h).status_code == 403

    st0 = client.get("/api/v1/admin/gateway-status", headers=admin_h)
    assert st0.status_code == 200
    assert "base_url" in st0.json() and "rotation_pool" in st0.json()
    assert "gpt-5.6-sol" in st0.json()["rotation_pool"]

    fake_secret = "sk-apithat-unit-test-secret-key-123456789999"
    monkeypatch.setattr(
        eng,
        "probe_apithat_key",
        lambda api_key, base_url="https://apithat.dev/v1": ["gpt-5.6-sol", "gpt-6.1-terra", "gpt-6-sol"],
    )
    res = client.post(
        "/api/v1/admin/gateway-key",
        headers=admin_h,
        json={"api_key": fake_secret, "base_url": "https://apithat.dev/v1", "preferred_model": "gpt-5.6-sol", "persist_env": False},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["configured"] is True and body["valid"] is True
    assert body["masked_key"] == "sk-a...9999"
    assert fake_secret not in res.text
    assert "gpt-5.6-sol" in body["available_models"]

    st1 = client.get("/api/v1/admin/gateway-status", headers=admin_h)
    assert st1.status_code == 200
    assert st1.json()["valid"] is True
    assert fake_secret not in st1.text

    with db.begin() as conn:
        logs = db.q(conn, "SELECT detail::text AS txt FROM live.audit_logs WHERE action = 'gateway.key_updated'")
    assert len(logs) == 1 and fake_secret not in logs[0]["txt"]
    eng.clear_runtime_gateway_override()


