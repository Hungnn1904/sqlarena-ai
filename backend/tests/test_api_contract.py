"""Hợp đồng API: xác thực/phân quyền, validate, idempotency, trần ngân sách."""
from app import db
from app.security import make_token


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_auth_matrix(client, admin_h, learner_h):
    assert client.get("/api/v1/admin/drafts").status_code == 401
    assert client.get("/api/v1/admin/drafts", headers={"Authorization": "Bearer rubbish"}).status_code == 401
    assert client.get("/api/v1/admin/drafts", headers=learner_h).status_code == 403
    assert client.get("/api/v1/admin/drafts", headers=admin_h).status_code == 200
    assert client.get("/api/v1/weekly/current").status_code == 401
    assert client.get("/api/v1/admin/weekly-sets", headers=learner_h).status_code == 403
    assert client.get("/api/v1/weekly/current", headers=learner_h).status_code == 404       # chưa có bộ đề published


def test_locked_account_and_expired_token(client):
    with db.begin() as conn:
        uid = db.q1(conn, "SELECT user_id FROM live.users WHERE email='locked@test.io'")["user_id"]
    r = client.get("/api/v1/admin/drafts", headers={"Authorization": f"Bearer {make_token(uid)}"})
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"
    import jwt, datetime
    from app.config import get_settings
    old = jwt.encode({"sub": "1", "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)}, get_settings().jwt_secret, algorithm="HS256")
    assert client.get("/api/v1/weekly/current", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_error_shape_is_openapi_error(client, admin_h):
    r = client.post("/api/v1/admin/generation-jobs", json={"difficulty": 9, "skill_ids": [], "quantity": 0}, headers=admin_h)
    body = r.json()
    assert r.status_code == 400 and set(body) == {"code", "message", "details"} and body["code"] == "VALIDATION_ERROR"


def test_create_job_and_idempotency(client, admin_h, skill_id):
    payload = {"difficulty": 1, "skill_ids": [skill_id("S1")], "quantity": 2, "topic": "Human Resources"}
    h = {**admin_h, "Idempotency-Key": "abc-1"}
    a = client.post("/api/v1/admin/generation-jobs", json=payload, headers=h)
    assert a.status_code == 202 and a.json()["status"] == "queued" and a.json()["requested_count"] == 2
    b = client.post("/api/v1/admin/generation-jobs", json=payload, headers=h)
    assert b.status_code == 200 and b.json()["job_id"] == a.json()["job_id"]            # phát lại: không tạo job thứ hai
    c = client.post("/api/v1/admin/generation-jobs", json={**payload, "quantity": 3}, headers=h)
    assert c.status_code == 409 and c.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    with db.begin() as conn:
        assert db.q1(conn, "SELECT count(*) n FROM draft.generation_jobs")["n"] == 1


def test_job_rejects_unknown_skill_and_infeasible_combo(client, admin_h, skill_id):
    r = client.post("/api/v1/admin/generation-jobs", json={"difficulty": 1, "skill_ids": [9999], "quantity": 1}, headers=admin_h)
    assert r.status_code == 400
    # Rules không định nghĩa S6 ở mức easy → từ chối ngay khi tạo job
    r = client.post("/api/v1/admin/generation-jobs", json={"difficulty": 1, "skill_ids": [skill_id("S6")], "quantity": 1}, headers=admin_h)
    assert r.status_code == 400 and "Rules" in r.json()["message"]


def test_budget_cap_blocks_job_creation(client, admin_h, skill_id):
    assert client.put("/api/v1/admin/settings/generation.daily_budget_calls", json={"value": 3}, headers=admin_h).status_code == 200
    r = client.post("/api/v1/admin/generation-jobs", json={"difficulty": 1, "skill_ids": [skill_id("S1")], "quantity": 1}, headers=admin_h)
    assert r.status_code == 429 and r.json()["code"] == "LLM_BUDGET_EXCEEDED" and r.headers["Retry-After"]
    assert r.json()["details"]["daily_cap"] == 3


def test_settings_validation(client, admin_h):
    put = lambda k, v: client.put(f"/api/v1/admin/settings/{k}", json={"value": v}, headers=admin_h)
    assert put("solve.samples_k", 99).status_code == 400            # vượt trần
    assert put("solve.samples_k", "3").status_code == 400           # sai kiểu
    assert put("solve.consensus", "majority").status_code == 400    # không được sửa qua API
    assert put("unknown.key", 1).status_code == 404
    assert put("solve.samples_k", 5).json()["value"] == 5
    with db.begin() as conn:
        assert db.q1(conn, "SELECT count(*) n FROM live.audit_logs WHERE action='setting.update'")["n"] == 1


def test_job_without_skill_ids_uses_all_feasible_skills(client, admin_h, skill_id):
    r = client.post("/api/v1/admin/generation-jobs", json={"difficulty": 1, "quantity": 1, "topic": "Human Resources"}, headers=admin_h)
    assert r.status_code == 202
    with db.begin() as conn:
        ids = db.q1(conn, "SELECT skill_ids FROM draft.generation_jobs")["skill_ids"]
    assert skill_id("S1") in ids and skill_id("S6") not in ids        # Rules không có S6 ở mức easy
