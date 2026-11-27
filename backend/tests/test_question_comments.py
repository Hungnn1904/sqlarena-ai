"""Kiểm thử tích hợp PostgreSQL 17 cho Thảo luận / Bình luận 1 cấp theo từng bài SQL (live.question_comments)."""
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
            """INSERT INTO live.users (role_id, email, username, password_hash, display_name, status)
               SELECT role_id, 'solver2@test.io', 'solver2', 'x', 'Bạn Giải Đúng', 'active'
               FROM live.roles WHERE name='learner'
               ON CONFLICT DO NOTHING""",
        )
        uid = db.q1(conn, "SELECT user_id FROM live.users WHERE email='solver2@test.io'")["user_id"]
    return {"Authorization": f"Bearer {make_token(uid)}"}


def _publish_two_questions(client, admin_id: int, admin_h: dict, skill_id_fn) -> tuple[int, int]:
    eng.set_transport(FakeOllama())
    enqueue_job(admin_id, quantity=1, difficulty=1, code="S1", topic="Human Resources")
    stats = new_worker().run_once()
    did = stats["reviewed"][0][0]
    q1_id = client.get(f"/api/v1/admin/drafts/{did}", headers=admin_h).json()["promoted_question"]["question_id"]

    q2_id = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Danh sách kho hàng hiện hành",
            "question": "Liệt kê warehouse_id, warehouse_name từ bảng warehouses. Sắp xếp: warehouse_id tăng.",
            "reference_sql": "SELECT warehouse_id, warehouse_name FROM warehouses ORDER BY warehouse_id ASC",
            "difficulty": 1,
            "skill_ids": [skill_id_fn("S1")],
        },
    ).json()["question_id"]

    ws = client.post(
        "/api/v1/admin/weekly-sets",
        headers=admin_h,
        json={"week_start": str(date.today()), "title": "Tuần thảo luận SQL"},
    ).json()
    set_id = ws["set_id"]
    client.post(f"/api/v1/admin/weekly-sets/{set_id}/items", headers=admin_h, json={"question_ids": [q1_id, q2_id]})
    assert client.post(f"/api/v1/admin/weekly-sets/{set_id}/publish", headers=admin_h).status_code == 200
    return q1_id, q2_id


def test_comments_submission_gate_admin_bypass_and_reputation_badges(client, admin_id, admin_h, learner_h, skill_id):
    """Kiểm chứng điều kiện xem/viết bình luận, đặc cách Admin, và 3 nhãn uy tín tự động (Quản trị viên, Đã thử làm, Đã giải đúng)."""
    q1_id, _q2_id = _publish_two_questions(client, admin_id, admin_h, skill_id)
    solver2_h = _create_second_learner()

    # 1. Học viên chưa nộp bài: vẫn đọc được danh sách, nhưng can_comment=False và POST bị chặn 409 SUBMISSION_REQUIRED
    init_list = client.get(f"/api/v1/questions/{q1_id}/comments", headers=learner_h)
    assert init_list.status_code == 200
    assert init_list.json()["can_comment"] is False
    assert init_list.json()["total_count"] == 0

    blocked = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=learner_h,
        json={"content": "Cho mình hỏi bài này lọc hire_date thế nào?"},
    )
    assert blocked.status_code == 409 and blocked.json()["code"] == "SUBMISSION_REQUIRED"

    # 2. Admin chưa nộp bài vẫn có can_comment=True và đăng bình luận trực tiếp với nhãn Quản trị viên
    adm_view = client.get(f"/api/v1/questions/{q1_id}/comments", headers=admin_h).json()
    assert adm_view["can_comment"] is True
    adm_post = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=admin_h,
        json={"content": "Gợi ý: Các em kiểm tra điều kiện status = 'active' nhé."},
    )
    assert adm_post.status_code == 201
    assert adm_post.json()["author_badge"] == "admin"
    assert adm_post.json()["author_role"] == "admin"

    # 3. Học viên 1 nộp bài SAI (passed=False) -> mở khóa can_comment=True, bình luận mang nhãn 'attempted' (Đã thử làm)
    sub_fail = client.post(
        "/api/v1/submissions",
        headers=learner_h,
        json={"question_id": q1_id, "sql": "SELECT employee_id FROM employees LIMIT 1"},
    )
    assert sub_fail.status_code == 200 and sub_fail.json()["passed"] is False

    l1_post = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=learner_h,
        json={"content": "Mình chạy thử bị thiếu cột job_title, mọi người gợi ý giúp nhé!"},
    )
    assert l1_post.status_code == 201
    l1_c = l1_post.json()
    assert l1_c["author_solved"] is False and l1_c["author_badge"] == "attempted"

    # 4. Học viên 2 giải ĐÚNG (passed=True) -> trả lời 1 cấp dưới bình luận của Học viên 1, mang nhãn 'solved' (Đã giải đúng)
    sub_pass = client.post("/api/v1/submissions", headers=solver2_h, json={"question_id": q1_id, "sql": GOOD_SQL})
    assert sub_pass.status_code == 200 and sub_pass.json()["passed"] is True

    reply_res = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=solver2_h,
        json={
            "parent_comment_id": l1_c["comment_id"],
            "content": "Bạn bổ sung đủ 4 cột theo đúng thứ tự đề yêu cầu và thêm ORDER BY là qua nhé!",
        },
    )
    assert reply_res.status_code == 201
    rep = reply_res.json()
    assert rep["parent_comment_id"] == l1_c["comment_id"]
    assert rep["author_solved"] is True and rep["author_badge"] == "solved"

    # 5. Đọc lại cây bình luận: 2 bình luận gốc, bình luận của Học viên 1 chứa đúng 1 reply, tổng số = 3
    tree = client.get(f"/api/v1/questions/{q1_id}/comments", headers=learner_h).json()
    assert tree["can_comment"] is True and tree["total_count"] == 3
    root_l1 = next(it for it in tree["items"] if it["comment_id"] == l1_c["comment_id"])
    assert len(root_l1["replies"]) == 1 and root_l1["replies"][0]["comment_id"] == rep["comment_id"]


def test_comments_one_level_depth_bola_idor_and_delete_permissions(client, admin_id, admin_h, learner_h, skill_id):
    """Chặn bình luận lồng cấp 2, chặn parent_comment_id khác câu hỏi (IDOR), chặn câu chưa phát hành (BOLA), và kiểm tra quyền xóa."""
    q1_id, q2_id = _publish_two_questions(client, admin_id, admin_h, skill_id)
    solver2_h = _create_second_learner()

    # Câu ẩn chưa lên kệ -> 404 BOLA
    unpub_qid = client.post(
        "/api/v1/admin/questions/manual",
        headers=admin_h,
        json={
            "title": "Câu chưa lên kệ",
            "question": "Liệt kê department_id từ bảng departments.",
            "reference_sql": "SELECT department_id FROM departments",
            "difficulty": 1,
            "skill_ids": [skill_id("S1")],
        },
    ).json()["question_id"]
    assert client.get(f"/api/v1/questions/{unpub_qid}/comments", headers=learner_h).status_code == 404
    assert client.post(f"/api/v1/questions/{unpub_qid}/comments", headers=admin_h, json={"content": "Thử đăng vào câu ẩn"}).status_code == 404

    # Mở khóa bình luận trên q1 và q2 cho learner_h & solver2_h
    client.post("/api/v1/submissions", headers=learner_h, json={"question_id": q1_id, "sql": "SELECT 1"})
    client.post("/api/v1/submissions", headers=learner_h, json={"question_id": q2_id, "sql": "SELECT 1"})
    client.post("/api/v1/submissions", headers=solver2_h, json={"question_id": q1_id, "sql": GOOD_SQL})

    root_q1 = client.post(f"/api/v1/questions/{q1_id}/comments", headers=learner_h, json={"content": "Bình luận gốc ở câu 1"}).json()
    reply_q1 = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=solver2_h,
        json={"parent_comment_id": root_q1["comment_id"], "content": "Trả lời cấp 1 hợp lệ"},
    ).json()

    # Chặn trả lời cấp 2 (reply vào một reply) -> 400
    nested_2 = client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=learner_h,
        json={"parent_comment_id": reply_q1["comment_id"], "content": "Cố tình lồng cấp 2"},
    )
    assert nested_2.status_code == 400

    # Chặn IDOR gắn parent_comment_id của câu 1 sang câu 2 -> 400
    cross_q = client.post(
        f"/api/v1/questions/{q2_id}/comments",
        headers=learner_h,
        json={"parent_comment_id": root_q1["comment_id"], "content": "Gắn nhầm parent của câu khác"},
    )
    assert cross_q.status_code == 400

    # Người học khác (solver2) KHÔNG được xóa bình luận gốc của learner_h -> 403
    forbid_del = client.delete(f"/api/v1/questions/{q1_id}/comments/{root_q1['comment_id']}", headers=solver2_h)
    assert forbid_del.status_code == 403

    # Chủ sở hữu (solver2) tự xóa reply của chính mình -> 200
    own_del = client.delete(f"/api/v1/questions/{q1_id}/comments/{reply_q1['comment_id']}", headers=solver2_h)
    assert own_del.status_code == 200

    # Tạo thêm 1 reply mới rồi Admin xóa bình luận gốc -> ON DELETE CASCADE xóa sạch cả gốc lẫn reply, và question_reports vẫn bằng 0
    client.post(
        f"/api/v1/questions/{q1_id}/comments",
        headers=solver2_h,
        json={"parent_comment_id": root_q1["comment_id"], "content": "Reply sẽ tự động xóa theo bình luận gốc"},
    )
    adm_del = client.delete(f"/api/v1/questions/{q1_id}/comments/{root_q1['comment_id']}", headers=admin_h)
    assert adm_del.status_code == 200
    assert client.get(f"/api/v1/questions/{q1_id}/comments", headers=learner_h).json()["total_count"] == 0
    with db.begin() as conn:
        rep_n = db.q1(conn, "SELECT count(*) AS n FROM live.question_reports")["n"]
        rem_c = db.q1(conn, "SELECT count(*) AS n FROM live.question_comments WHERE question_id = :q", q=q1_id)["n"]
    assert rep_n == 0 and rem_c == 0
