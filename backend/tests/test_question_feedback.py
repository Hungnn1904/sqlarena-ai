"""Kiểm thử tích hợp PostgreSQL 17 cho Bình chọn câu hỏi (👍/👎), Báo lỗi / Góp ý (🚩) & 3 hướng xử lý Human-in-the-loop của Admin."""
from datetime import date

from conftest import enqueue_job, new_worker
from fakes import FakeOllama, GOOD_SQL

from app import db
from app.pipeline import engine as eng
from app.security import make_token


def _create_second_learner() -> dict:
    with db.begin() as conn:
        db.ex(
            conn,
            """INSERT INTO live.users (role_id, email, username, password_hash, status)
               SELECT role_id, 'learner2@test.io', 'learner2', 'x', 'active'
               FROM live.roles WHERE name='learner'
               ON CONFLICT DO NOTHING""",
        )
        uid = db.q1(conn, "SELECT user_id FROM live.users WHERE email='learner2@test.io'")["user_id"]
    return {"Authorization": f"Bearer {make_token(uid)}"}


def _publish_ai_question(client, admin_id: int, admin_h: dict) -> tuple[int, int]:
    eng.set_transport(FakeOllama())
    enqueue_job(admin_id, quantity=1, difficulty=1, code="S1", topic="Human Resources")
    stats = new_worker().run_once()
    draft_id = stats["reviewed"][0][0]
    det = client.get(f"/api/v1/admin/drafts/{draft_id}", headers=admin_h).json()
    qid = det["promoted_question"]["question_id"]

    ws = client.post(
        "/api/v1/admin/weekly-sets",
        headers=admin_h,
        json={"week_start": str(date.today()), "title": "Tuần kiểm thử phản hồi"},
    ).json()
    set_id = ws["set_id"]
    client.post(f"/api/v1/admin/weekly-sets/{set_id}/items", headers=admin_h, json={"question_ids": [qid]})
    pub = client.post(f"/api/v1/admin/weekly-sets/{set_id}/publish", headers=admin_h)
    assert pub.status_code == 200
    return draft_id, qid


def test_vote_requires_at_least_one_submission_and_allows_switching_vote(client, admin_id, admin_h, learner_h):
    """Bình chọn 👍/👎 yêu cầu tối thiểu 1 lần nộp bài (kể cả nộp sai), mỗi tài khoản 1 phiếu duy nhất và đổi được chiều vote."""
    _draft_id, qid = _publish_ai_question(client, admin_id, admin_h)

    # Chưa nộp bài lần nào -> can_vote=False và POST /vote bị từ chối 409 SUBMISSION_REQUIRED
    q_before = client.get(f"/api/v1/questions/{qid}", headers=learner_h).json()
    assert q_before["feedback"]["can_vote"] is False
    assert q_before["feedback"]["my_vote"] is None

    denied = client.post(f"/api/v1/questions/{qid}/vote", headers=learner_h, json={"vote": 1})
    assert denied.status_code == 409
    assert denied.json()["code"] == "SUBMISSION_REQUIRED"

    # Nộp bài thử 1 lần nhưng kết quả SAI (passed=False) -> vẫn đủ điều kiện bình chọn!
    sub = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": qid, "sql": "SELECT employee_id FROM employees LIMIT 1"},
    )
    assert sub.status_code == 200 and sub.json()["passed"] is False

    # Bình chọn 👍 (vote = 1)
    v1 = client.post(f"/api/v1/questions/{qid}/vote", headers=learner_h, json={"vote": 1})
    assert v1.status_code == 200
    b1 = v1.json()
    assert b1["my_vote"] == 1 and b1["upvotes"] == 1 and b1["downvotes"] == 0 and b1["can_vote"] is True

    # Đổi sang 👎 (vote = -1) trên cùng tài khoản -> cập nhật hàng duy nhất, không cộng dồn 2 phiếu
    v2 = client.post(f"/api/v1/questions/{qid}/vote", headers=learner_h, json={"vote": -1})
    assert v2.status_code == 200
    b2 = v2.json()
    assert b2["my_vote"] == -1 and b2["upvotes"] == 0 and b2["downvotes"] == 1

    # Bỏ chọn (vote = 0) -> xóa phiếu
    v0 = client.post(f"/api/v1/questions/{qid}/vote", headers=learner_h, json={"vote": 0})
    assert v0.status_code == 200
    assert v0.json()["my_vote"] is None and v0.json()["upvotes"] == 0 and v0.json()["downvotes"] == 0


def test_learner_reports_enforce_one_open_per_user_and_never_auto_lock_question(client, admin_id, admin_h, learner_h, skill_id):
    """Cho phép gửi báo lỗi ngay khi đọc đề, chặn báo lỗi trùng đang mở (open), chặn BOLA đề ẩn, và KHÔNG BAO GIỜ tự khóa câu hỏi."""
    _draft_id, qid = _publish_ai_question(client, admin_id, admin_h)
    learner2_h = _create_second_learner()

    # Câu chưa phát hành lên kệ -> 404 khi cố vote hoặc gửi report (chống BOLA)
    unpub_qid = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Câu ẩn trong kho",
            "question": "Liệt kê employee_id từ bảng employees.",
            "reference_sql": "SELECT employee_id FROM employees",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    ).json()["question_id"]
    assert client.post(f"/api/v1/questions/{unpub_qid}/reports", headers=learner_h, json={"reason_type": "other", "comment": "Thử dò ID ẩn"}).status_code == 404
    assert client.post(f"/api/v1/questions/{unpub_qid}/vote", headers=learner_h, json={"vote": 1}).status_code == 404

    # Gửi báo lỗi ngay khi đọc đề (0 lần nộp bài) -> thành công 201
    r1 = client.post(
        f"/api/v1/questions/{qid}/reports",
        headers=learner_h,
        json={"reason_type": "ambiguous_prompt", "comment": "Đề chưa nêu rõ nhân viên thử việc có tính không."},
    )
    assert r1.status_code == 201
    rep1 = r1.json()
    assert rep1["status"] == "open" and rep1["reason_type"] == "ambiguous_prompt"

    # Cùng người học gửi tiếp báo lỗi thứ 2 khi báo lỗi cũ còn open -> chặn 409 OPEN_REPORT_EXISTS
    dup = client.post(
        f"/api/v1/questions/{qid}/reports",
        headers=learner_h,
        json={"reason_type": "typo_or_column_name", "comment": "Spam báo lỗi lần 2"},
    )
    assert dup.status_code == 409 and dup.json()["code"] == "OPEN_REPORT_EXISTS"

    # Người học thứ 2 cũng báo lỗi -> tổng cộng 2 báo lỗi open, nhưng câu hỏi VẪN mở bình thường trên kệ (Human-in-the-loop)
    r2 = client.post(
        f"/api/v1/questions/{qid}/reports",
        headers=learner2_h,
        json={"reason_type": "wrong_answer_or_testcase", "comment": "Nghi thiếu điều kiện lọc status."},
    )
    assert r2.status_code == 201

    shelf = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()["items"]
    assert any(it["question_id"] == qid and not it["is_voided"] for it in shelf)
    with db.begin() as conn:
        qrow = db.q1(conn, "SELECT status, is_flagged FROM live.questions WHERE question_id=:q", q=qid)
    assert qrow["status"] == "ready" and qrow["is_flagged"] is False


def test_admin_feedback_filter_and_three_resolution_flows(client, admin_id, admin_h, learner_h, skill_id):
    """Kiểm tra lọc 'Có báo lỗi' tại Ngân hàng đề, GET /admin/questions/feedback và cả 3 hướng xử lý: Dismiss, Sửa SQL/Return-Needs-Human, Retire."""
    draft_id, qid_ai = _publish_ai_question(client, admin_id, admin_h)
    learner2_h = _create_second_learner()

    # Tạo thêm 1 câu thứ 2 trên cùng kệ để thử cả 3 luồng độc lập
    qid_manual = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Danh sách phòng ban hoạt động",
            "question": "Liệt kê department_id, department_name từ bảng departments. Sắp xếp: department_id tăng.",
            "reference_sql": "SELECT department_id, department_name FROM departments WHERE department_id = 1 ORDER BY department_id ASC",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    ).json()["question_id"]
    ws_cur = client.get("/api/v1/admin/weekly-sets?status=published", headers=admin_h).json()["items"][0]
    # Thêm câu manual thông qua question-groups append_active
    grp = client.post(
        "/api/v1/admin/question-groups",
        headers=admin_h,
        json={"name": "Nhóm bổ sung", "question_ids": [qid_manual]},
    ).json()
    client.post(f"/api/v1/admin/question-groups/{grp['group_id']}/publish", headers=admin_h, json={"mode": "append_active"})

    # 1. Người học gửi báo lỗi trên qid_manual -> Admin lọc has_reports=true và xem /admin/questions/feedback
    rep_dismiss = client.post(
        f"/api/v1/questions/{qid_manual}/reports",
        headers=learner_h,
        json={"reason_type": "wrong_difficulty", "comment": "Bài dễ nhưng em bấm nhầm báo lỗi."},
    ).json()
    fb_list = client.get("/api/v1/admin/questions/feedback?status=open", headers=admin_h)
    assert fb_list.status_code == 200
    assert any(it["report_id"] == rep_dismiss["report_id"] for it in fb_list.json()["items"])

    bank_reported = client.get("/api/v1/admin/questions?has_reports=true", headers=admin_h).json()["items"]
    assert [it["question_id"] for it in bank_reported] == [qid_manual]
    assert bank_reported[0]["open_reports_count"] == 1

    # Hướng 3: Bỏ qua (Dismiss) -> câu hỏi giữ nguyên ready, bộ lọc has_reports=true trở về rỗng, học viên được quyền gửi lại báo lỗi mới
    res_dismiss = client.post(
        f"/api/v1/admin/reports/{rep_dismiss['report_id']}/resolve",
        headers=admin_h,
        json={"action": "dismiss", "admin_note": "Độ khó mức 1 đã đúng chuẩn S1."},
    )
    assert res_dismiss.status_code == 200 and res_dismiss.json()["report"]["status"] == "dismissed"
    assert client.get("/api/v1/admin/questions?has_reports=true", headers=admin_h).json()["items"] == []

    # Hướng 1A: Người học báo nghi sai đáp án (bị gắn thừa WHERE department_id = 1) -> Admin sửa SQL & sinh lại test case ngay -> đóng resolved
    rep_fix_sql = client.post(
        f"/api/v1/questions/{qid_manual}/reports",
        headers=learner_h,
        json={"reason_type": "wrong_answer_or_testcase", "comment": "Đáp án đang lọc nhầm chỉ 1 phòng ban thay vì toàn bộ."},
    ).json()
    fixed_sql = "SELECT department_id, department_name FROM departments ORDER BY department_id ASC"
    res_rework_sql = client.post(
        f"/api/v1/admin/reports/{rep_fix_sql['report_id']}/resolve",
        headers=admin_h,
        json={
            "action": "rework",
            "updated_sql": fixed_sql,
            "admin_note": "Đã gỡ điều kiện thừa và sinh lại test case chuẩn.",
        },
    )
    assert res_rework_sql.status_code == 200
    assert res_rework_sql.json()["report"]["status"] == "resolved"
    # Học viên nộp đúng câu fixed_sql lập tức chấm Đạt 100%!
    grade_ok = client.post("/api/v1/submissions", headers=learner_h, json={"question_id": qid_manual, "sql": fixed_sql}).json()
    assert grade_ok["passed"] is True

    # Hướng 1B: Thu hồi về Cần duyệt (return_needs_human) trên câu AI qid_ai -> gỡ khỏi kệ, draft về needs_human, đóng report resolved
    rep_return = client.post(
        f"/api/v1/questions/{qid_ai}/reports",
        headers=learner2_h,
        json={"reason_type": "ambiguous_prompt", "comment": "Cần chỉnh lại câu chữ đề bài rõ hơn."},
    ).json()
    res_return = client.post(
        f"/api/v1/admin/reports/{rep_return['report_id']}/resolve",
        headers=admin_h,
        json={"action": "return_needs_human", "admin_note": "Đưa về hàng đợi Duyệt đề để biên tập lại."},
    )
    assert res_return.status_code == 200
    assert res_return.json()["report"]["status"] == "resolved"
    assert client.get(f"/api/v1/admin/drafts/{draft_id}", headers=admin_h).json()["status"] == "needs_human"
    assert client.get(f"/api/v1/questions/{qid_ai}", headers=learner2_h).status_code == 404 and ws_cur["set_id"] >= 1

    # Hướng 2: Loại bỏ (Retire) trên qid_manual -> chuyển câu hỏi sang retired & đóng report resolved
    rep_retire = client.post(
        f"/api/v1/questions/{qid_manual}/reports",
        headers=learner2_h,
        json={"reason_type": "other", "comment": "Đề quá cơ bản, đề xuất loại bỏ."},
    ).json()
    res_retire = client.post(
        f"/api/v1/admin/reports/{rep_retire['report_id']}/resolve",
        headers=admin_h,
        json={"action": "retire", "admin_note": "Đã loại bỏ khỏi ngân hàng đề."},
    )
    assert res_retire.status_code == 200
    assert res_retire.json()["report"]["status"] == "resolved"
    assert client.get(f"/api/v1/admin/questions/{qid_manual}", headers=admin_h).json()["status"] == "retired"


def test_manual_question_return_needs_human_roundtrip_reapprove(client, admin_id, admin_h, learner_h, skill_id):
    """Câu thủ công/đề nguồn (source_draft_id=NULL) khi thu hồi về Duyệt đề phải gỡ sạch weekly_set_items và phê duyệt khứ hồi thành công."""
    _publish_ai_question(client, admin_id, admin_h)
    q_seed = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Tra cứu kho vận đang hoạt động",
            "question": "Liệt kê warehouse_id, warehouse_name từ bảng warehouses. Sắp xếp: warehouse_id tăng.",
            "reference_sql": "SELECT warehouse_id, warehouse_name FROM warehouses ORDER BY warehouse_id ASC",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    ).json()["question_id"]
    grp = client.post(
        "/api/v1/admin/question-groups",
        headers=admin_h,
        json={"name": "Nhóm kho vận", "question_ids": [q_seed]},
    ).json()
    client.post(f"/api/v1/admin/question-groups/{grp['group_id']}/publish", headers=admin_h, json={"mode": "append_active"})

    rep = client.post(
        f"/api/v1/questions/{q_seed}/reports",
        headers=learner_h,
        json={"reason_type": "typo_or_column_name", "comment": "Cần rà soát lại tiêu đề trước khi mở lại."},
    ).json()
    res = client.post(
        f"/api/v1/admin/reports/{rep['report_id']}/resolve",
        headers=admin_h,
        json={"action": "return_needs_human", "admin_note": "Chuyển câu thủ công sang Duyệt đề."},
    )
    assert res.status_code == 200
    new_did = res.json()["question"]["source_draft_id"]
    assert new_did is not None
    assert client.get(f"/api/v1/questions/{q_seed}", headers=learner_h).status_code == 404

    # Phê duyệt lại tại Duyệt đề không bị 409 MANDATORY_GATE_FAILED và vào kho Chưa có trên kệ (unassigned_only=true)
    reapp = client.post(
        f"/api/v1/admin/drafts/{new_did}/approve",
        headers=admin_h,
        json={"custom_sql": "SELECT warehouse_id, warehouse_name FROM warehouses ORDER BY warehouse_id ASC", "note": "Duyệt lại thành công"},
    )
    assert reapp.status_code == 200 and reapp.json()["status"] == "approved"
    unassigned_ids = [it["question_id"] for it in client.get("/api/v1/admin/questions?unassigned_only=true", headers=admin_h).json()["items"]]
    assert q_seed in unassigned_ids and admin_id >= 1
