"""Bộ đề tuần: tạo/thiếu hụt/job bổ sung, thay items, publish, close, view người học, tác động của retire."""
import datetime

import pytest
from conftest import make_question, set_week_target

from app import db
from app.services import weekly

WEEK = "2026-10-19"


def H(h):
    return h


def _create(client, h, week=WEEK, **kw):
    return client.post("/api/v1/admin/weekly-sets", json={"week_start": week, **kw}, headers=h)


def test_create_picks_ready_unused_and_orders_by_difficulty(client, admin_h):
    set_week_target(client, admin_h, 2, 1, 0)
    e = [make_question(1, title=f"E{i}") for i in range(3)]
    m = make_question(2, "S4")
    make_question(1, status="retired"); make_question(1, flagged=True); make_question(1, status="archived")      # không đủ điều kiện
    r = _create(client, admin_h, title="Tuần 1")
    assert r.status_code == 201
    s = r.json()
    assert s["status"] == "draft" and s["title"] == "Tuần 1" and s["deficits_by_difficulty"] == {} and s["supplemental_generation_job_ids"] == []
    got = [(i["position"], i["question"]["question_id"], i["question"]["difficulty"]) for i in s["items"]]
    assert got == [(1, e[0], 1), (2, e[1], 1), (3, m, 2)]                    # Easy trước Medium; position liên tục
    assert _create(client, admin_h).status_code == 409                       # tuần đã có bộ
    # Câu đã gán bộ thì bộ sau không lấy lại (UNIQUE(question_id))
    r2 = _create(client, admin_h, week="2026-10-26")
    assert {i["question"]["question_id"] for i in r2.json()["items"]}.isdisjoint({e[0], e[1], m})


def test_shortage_records_deficits_and_enqueues_supplemental_jobs(client, admin_h):
    set_week_target(client, admin_h, 2, 1, 1)
    make_question(1)                                                          # thiếu: Easy 1, Medium 1, Hard 1
    s = _create(client, admin_h).json()
    assert s["deficits_by_difficulty"] == {"1": 1, "2": 1, "3": 1} and len(s["supplemental_generation_job_ids"]) == 3
    assert any("Thiếu đề READY" in w for w in s["warnings"])
    with db.begin() as conn:
        jobs = db.q(conn, "SELECT difficulty, requested_count, status FROM draft.generation_jobs ORDER BY difficulty")
    assert [(j["difficulty"], j["requested_count"], j["status"]) for j in jobs] == [(1, 1, "queued"), (2, 1, "queued"), (3, 1, "queued")]


def test_large_deficit_is_split_into_jobs_of_at_most_30(client, admin_h):
    set_week_target(client, admin_h, 0, 0, 70)
    client.put("/api/v1/admin/settings/generation.daily_budget_calls", json={"value": 100000}, headers=admin_h)
    s = _create(client, admin_h).json()
    with db.begin() as conn:
        sizes = sorted(r["requested_count"] for r in db.q(conn, "SELECT requested_count FROM draft.generation_jobs"))
    assert sizes == [10, 30, 30] and len(s["supplemental_generation_job_ids"]) == 3


def test_budget_exhausted_keeps_set_draft_with_warning(client, admin_h):
    set_week_target(client, admin_h, 5, 0, 0)
    client.put("/api/v1/admin/settings/generation.daily_budget_calls", json={"value": 3}, headers=admin_h)
    r = _create(client, admin_h)
    s = r.json()
    assert r.status_code == 201 and s["status"] == "draft" and s["supplemental_generation_job_ids"] == [] and s["deficits_by_difficulty"] == {"1": 5}
    assert any("ngân sách" in w for w in s["warnings"])


def test_replace_items_rules(client, admin_h):
    set_week_target(client, admin_h, 1, 0, 0)
    a, b, c = make_question(1), make_question(1), make_question(1)
    bad_ready, flagged, other = make_question(1, status="archived"), make_question(1, flagged=True), make_question(1)
    sid = _create(client, admin_h).json()["set_id"]
    other_set = _create(client, admin_h, week="2026-10-26").json()["set_id"]
    ok = client.put(f"/api/v1/admin/weekly-sets/{other_set}/items", json={"question_ids": [other]}, headers=admin_h)
    assert ok.status_code == 200
    r = client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [c, b, a, bad_ready, flagged, other, 9999]}, headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "QUESTION_NOT_ELIGIBLE"
    d = r.json()["details"]
    assert d["not_ready"] == [bad_ready] and d["flagged"] == [flagged] and d["already_in_another_set"] == [other] and d["not_found"] == [9999]
    r = client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [c, b, a]}, headers=admin_h)
    assert [i["question"]["question_id"] for i in r.json()["items"]] == [c, b, a]               # thứ tự mảng = position
    assert client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [a, a]}, headers=admin_h).status_code == 400


def test_publish_gates(client, admin_h):
    set_week_target(client, admin_h, 1, 0, 0)
    sid = _create(client, admin_h).json()["set_id"]                          # không có đề READY ⇒ bộ rỗng
    r = client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "EMPTY_SET"
    no_tc = make_question(1, with_test=False)
    r = client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [no_tc]}, headers=admin_h)
    assert r.status_code == 409 and r.json()["details"]["invalid_test_cases"] == [no_tc]        # chặn ngay lúc chọn
    good = make_question(1)
    client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [good]}, headers=admin_h)
    r = client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
    assert r.status_code == 200 and r.json()["status"] == "published" and r.json()["published_at"]
    assert client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h).status_code == 409        # đã published
    assert client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [good]}, headers=admin_h).status_code == 409   # hết DRAFT
    second = _create(client, admin_h, week="2026-10-26").json()["set_id"]
    client.put(f"/api/v1/admin/weekly-sets/{second}/items", json={"question_ids": [make_question(1)]}, headers=admin_h)
    r = client.post(f"/api/v1/admin/weekly-sets/{second}/publish", headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "ANOTHER_SET_PUBLISHED"


def test_dataset_version_must_match_world(client, admin_h):
    """Test case sinh trên dataset_version cũ không được chọn/publish (tài liệu chốt: 'đúng dataset/version')."""
    set_week_target(client, admin_h, 2, 0, 0)
    a, b = make_question(1), make_question(1)
    sid = _create(client, admin_h).json()["set_id"]
    assert {i["question"]["question_id"] for i in client.get(f"/api/v1/admin/weekly-sets/{sid}", headers=admin_h).json()["items"]} == {a, b}
    try:
        with db.begin() as conn:
            db.ex(conn, "UPDATE core.worlds SET dataset_version = dataset_version + 1")            # dataset đổi phiên bản sau khi sinh test case
        r = client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
        assert r.status_code == 409 and r.json()["code"] == "SET_NOT_PUBLISHABLE" and set(r.json()["details"]["stale_dataset_version"]) == {a, b}
        r = client.put(f"/api/v1/admin/weekly-sets/{sid}/items", json={"question_ids": [a]}, headers=admin_h)
        assert r.status_code == 409 and r.json()["details"]["invalid_test_cases"] == [a]
        set_week_target(client, admin_h, 2, 0, 0)
        s2 = _create(client, admin_h, week="2026-11-02").json()
        assert s2["items"] == [] and s2["deficits_by_difficulty"] == {"1": 2}                      # không tự chọn đề lệch version
    finally:
        with db.begin() as conn:
            db.ex(conn, "UPDATE core.worlds SET dataset_version = dataset_version - 1")


def test_db_enforces_single_published_set():
    with db.begin() as conn:
        db.ex(conn, "INSERT INTO live.weekly_sets (title, week_start, status, published_at) VALUES ('a', '2026-01-05', 'published', now())")
    with pytest.raises(Exception, match="weekly_sets_one_published_idx"):
        with db.begin() as conn:
            db.ex(conn, "INSERT INTO live.weekly_sets (title, week_start, status, published_at) VALUES ('b', '2026-01-12', 'published', now())")


def _published(client, h, easy=2, hard=1):
    set_week_target(client, h, easy, 0, hard)
    qs = [make_question(1, title=f"E{i}") for i in range(easy)] + [make_question(3, "S5", title="H0") for _ in range(hard)]
    sid = _create(client, h).json()["set_id"]
    assert client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=h).status_code == 200
    return sid, qs


def test_learner_only_sees_published_weekly_set(client, admin_h, learner_h):
    set_week_target(client, admin_h, 1, 0, 0)
    q1_ = make_question(1)
    assert client.get("/api/v1/weekly/current", headers=learner_h).status_code == 404                # chưa publish
    sid = _create(client, admin_h).json()["set_id"]
    assert client.get("/api/v1/weekly/current", headers=learner_h).status_code == 404                # DRAFT cũng không lộ
    assert client.get(f"/api/v1/questions/{q1_}", headers=learner_h).status_code == 404
    client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
    cur = client.get("/api/v1/weekly/current", headers=learner_h).json()
    assert cur["set_id"] == sid and cur["question_count"] == 1 and cur["week_start"] == WEEK and cur["ends_at"].startswith("2026-10-26T00:00:00")
    outside = make_question(1)                                                                       # READY nhưng ngoài bộ
    assert client.get(f"/api/v1/questions/{outside}", headers=learner_h).status_code == 404
    d = client.get(f"/api/v1/questions/{q1_}", headers=learner_h)
    assert d.status_code == 200 and d.json()["is_voided"] is False and d.json()["solved"] is False
    assert "reference_sql" not in d.text and "SELECT 1" not in d.text and "expected" not in d.text
    assert client.get("/api/v1/weekly/current").status_code == 401
    assert client.get("/api/v1/questions", headers=learner_h).status_code in (404, 405)               # pool phẳng đã bỏ


def test_learner_list_filters_and_order(client, admin_h, learner_h):
    sid, qs = _published(client, admin_h, easy=2, hard=1)
    r = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()
    assert [i["question_id"] for i in r["items"]] == qs and [i["position"] for i in r["items"]] == [1, 2, 3] and r["total"] == 3
    assert [i["question_id"] for i in client.get("/api/v1/weekly/current/questions?difficulty=3", headers=learner_h).json()["items"]] == [qs[2]]
    with db.begin() as conn:
        s5 = db.q1(conn, "SELECT skill_id FROM core.skills WHERE code='S5'")["skill_id"]
    assert client.get(f"/api/v1/weekly/current/questions?skill_id={s5}", headers=learner_h).json()["total"] == 1
    assert client.get("/api/v1/weekly/current/questions?solved=true", headers=learner_h).json()["total"] == 0
    assert client.get("/api/v1/weekly/current/questions?page_size=2&page=2", headers=learner_h).json()["items"][0]["question_id"] == qs[2]


def test_retire_voids_in_published_set_and_blocks_restore(client, admin_h, learner_h):
    sid, qs = _published(client, admin_h, easy=2, hard=0)
    r = client.post(f"/api/v1/admin/questions/{qs[0]}/retire", json={"reason": "đề lỗi giữa tuần"}, headers=admin_h).json()
    assert r["status"] == "retired" and r["weekly_effect"] == "voided_in_published_set"
    items = client.get("/api/v1/weekly/current/questions", headers=learner_h).json()["items"]
    assert [(i["question_id"], i["is_voided"]) for i in items] == [(qs[0], True), (qs[1], False)]     # vẫn hiển thị, đánh dấu void
    again = client.post(f"/api/v1/admin/questions/{qs[0]}/restore", json={}, headers=admin_h)
    assert again.status_code == 409 and again.json()["code"] == "QUESTION_ALREADY_USED"


def test_retire_in_draft_set_removes_and_reindexes_and_restore_allowed(client, admin_h):
    set_week_target(client, admin_h, 3, 0, 0)
    qs = [make_question(1) for _ in range(3)]
    sid = _create(client, admin_h).json()["set_id"]
    r = client.post(f"/api/v1/admin/questions/{qs[1]}/retire", json={"reason": "trùng ý"}, headers=admin_h).json()
    assert r["weekly_effect"] == "removed_from_draft_set"
    view = client.get(f"/api/v1/admin/weekly-sets/{sid}", headers=admin_h).json()
    assert [(i["position"], i["question"]["question_id"]) for i in view["items"]] == [(1, qs[0]), (2, qs[2])]
    assert view["deficits_by_difficulty"] == {"1": 1}
    assert client.post(f"/api/v1/admin/questions/{qs[1]}/restore", json={}, headers=admin_h).json()["status"] == "ready"   # chưa từng bị gán nữa


def test_close_archives_ready_only_and_respects_cutoff(client, admin_h, learner_h):
    today = datetime.date.today().isoformat()
    set_week_target(client, admin_h, 2, 0, 0)
    a, b = make_question(1), make_question(1)
    sid = _create(client, admin_h, week=today).json()["set_id"]
    client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
    client.post(f"/api/v1/admin/questions/{b}/retire", json={"reason": "lỗi đề"}, headers=admin_h)
    client.put("/api/v1/admin/settings/weekly.close_requires_cutoff", json={"value": True}, headers=admin_h)
    r = client.post(f"/api/v1/admin/weekly-sets/{sid}/close", headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "BEFORE_CUTOFF"                      # bật cutoff: chưa tới mốc kết thúc tuần
    client.put("/api/v1/admin/settings/weekly.close_requires_cutoff", json={"value": False}, headers=admin_h)
    r = client.post(f"/api/v1/admin/weekly-sets/{sid}/close", headers=admin_h)
    assert r.status_code == 200 and r.json()["status"] == "closed" and any("CLOSE_HOOKS" in w for w in r.json()["warnings"])
    with db.begin() as conn:
        st = {x["question_id"]: x["status"] for x in db.q(conn, "SELECT question_id, status FROM live.questions")}
    assert st[a] == "archived" and st[b] == "retired"                                        # retired không bị ghi đè
    assert client.get(f"/api/v1/questions/{a}", headers=learner_h).status_code == 404         # đề archived không truy cập được
    assert client.get("/api/v1/weekly/current", headers=learner_h).status_code == 404
    assert client.post(f"/api/v1/admin/weekly-sets/{sid}/close", headers=admin_h).status_code == 409


def test_close_is_atomic_when_ranking_hook_fails(client, admin_h):
    client.put("/api/v1/admin/settings/weekly.close_requires_cutoff", json={"value": False}, headers=admin_h)
    sid, qs = _published(client, admin_h, easy=2, hard=0)

    def boom(conn, set_id):
        db.ex(conn, "UPDATE live.weekly_sets SET title='đã sửa trong hook' WHERE set_id=:i", i=set_id)
        raise RuntimeError("lỗi tính weekly_results")
    weekly.CLOSE_HOOKS.append(boom)
    try:
        with pytest.raises(RuntimeError):
            client.post(f"/api/v1/admin/weekly-sets/{sid}/close", headers=admin_h)
    finally:
        weekly.CLOSE_HOOKS.clear()
    with db.begin() as conn:
        s = db.q1(conn, "SELECT status, title FROM live.weekly_sets WHERE set_id=:i", i=sid)
        assert s["status"] == "published" and s["title"] != "đã sửa trong hook"               # rollback toàn bộ
        assert {r["status"] for r in db.q(conn, "SELECT status FROM live.questions")} == {"ready"}


def test_weekly_setting_validation(client, admin_h):
    put = lambda v: client.put("/api/v1/admin/settings/weekly.question_count", json={"value": v}, headers=admin_h)
    assert put({"1": 0, "2": 0, "3": 0}).status_code == 400          # tổng 0
    assert put({"1": 80, "2": 30}).status_code == 400                 # vượt 100
    assert put({"4": 5}).status_code == 400 and put({"1": -1}).status_code == 400 and put({"1": "5"}).status_code == 400
    assert put({"1": 20, "2": 20, "3": 10}).json()["value"] == {"1": 20, "2": 20, "3": 10}


def test_defaults_follow_final_spec_5_10_5(client, admin_h):
    items = {i["key"]: i["value"] for i in client.get("/api/v1/admin/settings", headers=admin_h).json()["items"]}
    assert items["weekly.question_count"] == {"1": 5, "2": 10, "3": 5} and items["weekly.close_requires_cutoff"] is False
    for _ in range(3):
        make_question(1)
    s = _create(client, admin_h).json()                                      # mục tiêu 20 câu: thiếu 2 Easy, 10 Medium, 5 Hard
    assert len(s["items"]) == 3 and s["deficits_by_difficulty"] == {"1": 2, "2": 10, "3": 5}


def test_learner_filter_by_title_and_history_summary(client, admin_h, learner_h):
    set_week_target(client, admin_h, 2, 0, 0)
    a = make_question(1, title="Nhân viên mới vào năm 2024"); make_question(1, title="Sản phẩm giá cao")
    sid = _create(client, admin_h).json()["set_id"]
    client.post(f"/api/v1/admin/weekly-sets/{sid}/publish", headers=admin_h)
    r = client.get("/api/v1/weekly/current/questions?q=nhân viên", headers=learner_h).json()
    assert [i["question_id"] for i in r["items"]] == [a]
    assert client.get("/api/v1/weekly/history", headers=learner_h).json()["total"] == 0          # chưa có tuần nào đã đóng
    client.post(f"/api/v1/admin/weekly-sets/{sid}/close", headers=admin_h)
    h = client.get("/api/v1/weekly/history", headers=learner_h).json()
    assert h["total"] == 1 and h["items"][0]["question_count"] == 2 and h["items"][0]["week_start"] == "2026-10-19"
    assert set(h["items"][0]) == {"set_id", "title", "week_start", "closed_at", "question_count", "voided_count"}   # chỉ tóm tắt, không có nội dung đề
    assert client.get(f"/api/v1/questions/{a}", headers=learner_h).status_code == 404
