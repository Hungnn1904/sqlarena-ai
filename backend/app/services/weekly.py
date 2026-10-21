"""Bộ đề tuần: draft → published → closed (Design v7, mục 4 business rules).

Phạm vi ở đây: tạo bộ (tự chọn câu READY chưa dùng, tính thiếu hụt, xếp job sinh bổ sung), thay items, publish, close (archive câu hỏi),
và các view cho người học. Chấm điểm/weekly_results/pass_rate thuộc module xếp hạng: đăng ký qua CLOSE_HOOKS (chạy cùng transaction đóng tuần).
"""
from datetime import date, datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import Connection

from ..config import get_settings
from ..db import ex, q, q1
from ..domain import DIFF_NAME
from ..errors import ApiError, bad_request, conflict, not_found
from . import audit, jobs
from . import settings_registry as sr

# Module xếp hạng đăng ký hàm (conn, set_id) -> dict | None; chạy TRONG transaction đóng tuần (lỗi ⇒ rollback toàn bộ).
CLOSE_HOOKS: list[Callable[[Connection, int], dict | None]] = []
MAX_JOB_DRAFTS = 30

# "Test case hợp lệ, đúng dataset/version": có ít nhất một test case và KHÔNG test case nào lệch dataset_version hiện hành của world.
VALID_TESTS = """EXISTS (SELECT 1 FROM live.test_cases t WHERE t.question_id = qq.question_id)
                 AND NOT EXISTS (SELECT 1 FROM live.test_cases t JOIN core.worlds w ON w.world_id = qq.world_id
                                 WHERE t.question_id = qq.question_id AND t.dataset_version <> w.dataset_version)"""


def _test_problems(conn: Connection, ids: list[int]) -> dict[str, list[int]]:
    """Phân loại lỗi test case: missing (chưa có), stale (lệch dataset_version)."""
    rows = q(conn, """SELECT qq.question_id,
                      NOT EXISTS (SELECT 1 FROM live.test_cases t WHERE t.question_id = qq.question_id) AS missing,
                      EXISTS (SELECT 1 FROM live.test_cases t JOIN core.worlds w ON w.world_id = qq.world_id
                              WHERE t.question_id = qq.question_id AND t.dataset_version <> w.dataset_version) AS stale
                      FROM live.questions qq WHERE qq.question_id = ANY(:ids)""", ids=ids)
    out = {"missing_test_cases": [r["question_id"] for r in rows if r["missing"]], "stale_dataset_version": [r["question_id"] for r in rows if r["stale"]]}
    return {k: v for k, v in out.items() if v}


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def ends_at(week_start: date) -> datetime:
    """Mốc kết thúc tuần = 00:00 ngày (week_start + 7) theo múi giờ ứng dụng."""
    return datetime.combine(week_start + timedelta(days=7), time.min, tzinfo=_tz())


def _target(conn: Connection) -> dict[int, int]:
    return {int(k): v for k, v in sr.get(conn, "weekly.question_count").items()}


def _lock_set(conn: Connection, set_id: int) -> dict:
    s = q1(conn, "SELECT * FROM live.weekly_sets WHERE set_id=:i FOR UPDATE", i=set_id)
    if not s:
        raise not_found("Không tìm thấy bộ đề")
    return s


# ------------------------------------------------------------------------------------------- admin view
def _items(conn: Connection, set_id: int) -> list[dict]:
    return q(conn, """SELECT i.position, i.is_voided, q.question_id, q.title, q.difficulty, q.skill_ids, q.status, q.is_flagged
                      FROM live.weekly_set_items i JOIN live.questions q USING (question_id) WHERE i.set_id=:s ORDER BY i.position""", s=set_id)


def _view(conn: Connection, s: dict, extra_warnings: list[str] | None = None, job_ids: list[int] | None = None) -> dict:
    items = _items(conn, s["set_id"])
    target = _target(conn)
    have = {d: sum(1 for it in items if it["difficulty"] == d) for d in (1, 2, 3)}
    deficits = {str(d): target[d] - have[d] for d in (1, 2, 3) if target.get(d, 0) > have[d]} if s["status"] == "draft" else {}
    warnings = list(extra_warnings or [])
    total, want = len(items), sum(target.values())
    if s["status"] == "draft" and total != want:
        warnings.append(f"Số đề ({total}) khác cấu hình tuần ({want}); kiểm tra lại trước khi publish")
    bad = [it["question_id"] for it in items if it["status"] != "ready" or it["is_flagged"]]
    if bad and s["status"] == "draft":
        warnings.append(f"Câu không còn đủ điều kiện (không ready/bị gắn cờ): {bad}")
    names = {r["skill_id"]: r["name"] for r in q(conn, "SELECT skill_id, name FROM core.skills")}
    return {"set_id": s["set_id"], "title": s["title"], "week_start": s["week_start"], "status": s["status"], "ends_at": ends_at(s["week_start"]),
            "published_at": s["published_at"], "closed_at": s["closed_at"],
            "items": [{"position": it["position"], "is_voided": it["is_voided"],
                       "question": {"question_id": it["question_id"], "title": it["title"], "difficulty": it["difficulty"], "status": it["status"],
                                    "is_flagged": it["is_flagged"], "skills": [names.get(i) for i in it["skill_ids"]]}} for it in items],
            "warnings": warnings, "deficits_by_difficulty": deficits, "supplemental_generation_job_ids": job_ids or []}


def get(conn: Connection, set_id: int) -> dict:
    s = q1(conn, "SELECT * FROM live.weekly_sets WHERE set_id=:i", i=set_id)
    if not s:
        raise not_found("Không tìm thấy bộ đề")
    return _view(conn, s)


def list_sets(conn: Connection, status: str | None, page: int, size: int) -> dict:
    where, p = ("WHERE s.status=:st", {"st": status}) if status else ("", {})
    total = q1(conn, f"SELECT count(*) AS n FROM live.weekly_sets s {where}", **p)["n"]
    rows = q(conn, f"""SELECT s.set_id, s.title, s.week_start, s.status, s.created_at, s.published_at, s.closed_at,
                       (SELECT count(*) FROM live.weekly_set_items i WHERE i.set_id=s.set_id) AS question_count
                       FROM live.weekly_sets s {where} ORDER BY s.week_start DESC LIMIT :l OFFSET :o""", l=size, o=(page - 1) * size, **p)
    return {"items": rows, "total": total, "page": page, "page_size": size}


# ------------------------------------------------------------------------------------------- create
def _pick(conn: Connection, difficulty: int, n: int) -> list[int]:
    """Chọn n câu READY chưa từng gán bộ, không bị gắn cờ; xoay vòng theo kỹ năng chính để bộ đề không dồn một kỹ năng."""
    rows = q(conn, """SELECT question_id, skill_ids FROM live.questions qq WHERE qq.status='ready' AND NOT qq.is_flagged AND qq.difficulty=:d AND """ + VALID_TESTS + """ AND NOT EXISTS (SELECT 1 FROM live.weekly_set_items i WHERE i.question_id = qq.question_id) ORDER BY qq.question_id""", d=difficulty)
    buckets: dict[int, list[int]] = {}
    for r in rows:
        buckets.setdefault(r["skill_ids"][0], []).append(r["question_id"])
    picked: list[int] = []
    while len(picked) < n and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(picked) < n:
                picked.append(buckets[key].pop(0))
    return picked


def _enqueue_supplemental(conn: Connection, admin: dict, deficits: dict[int, int]) -> tuple[list[int], list[str]]:
    ids, warnings = [], []
    active = q(conn, "SELECT skill_id FROM core.skills WHERE is_active ORDER BY skill_id")
    for diff, missing in sorted(deficits.items()):
        remaining = missing
        while remaining > 0:
            qty = min(remaining, MAX_JOB_DRAFTS)
            try:
                job, _ = jobs.create(conn, admin, {"difficulty": diff, "skill_ids": [s["skill_id"] for s in active], "quantity": qty, "topic": None}, None)
            except ApiError as exc:
                if exc.status == 429:
                    warnings.append(f"Không xếp được job sinh bổ sung cho độ khó {DIFF_NAME[diff]} (thiếu {remaining}): vượt trần ngân sách LLM. Bộ đề giữ DRAFT.")
                else:
                    warnings.append(f"Không xếp được job sinh bổ sung cho độ khó {DIFF_NAME[diff]}: {exc.message}")
                break
            ids.append(job["job_id"])
            remaining -= qty
    return ids, warnings


def create(conn: Connection, admin: dict, week_start: date, title: str | None) -> dict:
    if q1(conn, "SELECT 1 AS x FROM live.weekly_sets WHERE week_start=:w", w=week_start):
        raise conflict("WEEK_ALREADY_HAS_SET", "Tuần này đã có bộ đề", {"week_start": str(week_start)})
    target = _target(conn)
    chosen: dict[int, list[int]] = {d: _pick(conn, d, target.get(d, 0)) for d in (1, 2, 3)}
    deficits = {d: target.get(d, 0) - len(chosen[d]) for d in (1, 2, 3) if target.get(d, 0) > len(chosen[d])}
    s = q1(conn, "INSERT INTO live.weekly_sets (title, week_start) VALUES (:t, :w) RETURNING *",
           t=title or f"Bộ đề tuần {week_start:%d/%m/%Y}", w=week_start)
    pos = 0
    for d in (1, 2, 3):                                 # Easy → Medium → Hard
        for qid in chosen[d]:
            pos += 1
            ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, :p)", s=s["set_id"], q=qid, p=pos)
    job_ids, warnings = _enqueue_supplemental(conn, admin, deficits) if deficits else ([], [])
    if deficits:
        warnings.insert(0, "Thiếu đề READY theo độ khó: " + ", ".join(f"{DIFF_NAME[d]} −{n}" for d, n in sorted(deficits.items())) +
                        ". Job sinh bổ sung không tự thêm câu vào bộ; cập nhật items khi job xong và đã duyệt.")
    audit.log(conn, admin["user_id"], "weekly_set.create", "weekly_set", s["set_id"],
              {"week_start": str(week_start), "picked": {str(d): len(v) for d, v in chosen.items()}, "deficits": {str(d): n for d, n in deficits.items()}, "jobs": job_ids})
    return _view(conn, s, warnings, job_ids)


# ------------------------------------------------------------------------------------------- items / publish / close
def replace_items(conn: Connection, admin: dict, set_id: int, question_ids: list[int]) -> dict:
    s = _lock_set(conn, set_id)
    if s["status"] != "draft":
        raise conflict("INVALID_STATE", f"Chỉ sửa được items khi bộ đề còn DRAFT (hiện: {s['status']})", {"status": s["status"]})
    if len(set(question_ids)) != len(question_ids):
        raise bad_request("question_ids bị trùng")
    rows = {r["question_id"]: r for r in q(conn, """SELECT qq.question_id, qq.status, qq.is_flagged,
                (SELECT i.set_id FROM live.weekly_set_items i WHERE i.question_id = qq.question_id) AS in_set
                FROM live.questions qq WHERE qq.question_id = ANY(:ids)""", ids=question_ids)}
    problems: dict[str, list[int]] = {}
    for qid in question_ids:
        r = rows.get(qid)
        if r is None:
            problems.setdefault("not_found", []).append(qid)
        elif r["status"] != "ready":
            problems.setdefault("not_ready", []).append(qid)
        elif r["is_flagged"]:
            problems.setdefault("flagged", []).append(qid)
        elif r["in_set"] not in (None, set_id):
            problems.setdefault("already_in_another_set", []).append(qid)
    eligible_ids = [i for i in question_ids if i in rows and i not in {x for v in problems.values() for x in v}]
    for key, ids_ in _test_problems(conn, eligible_ids).items():
        problems.setdefault("invalid_test_cases", []).extend(ids_)
    if problems:
        raise conflict("QUESTION_NOT_ELIGIBLE", "Có câu không đủ điều kiện đưa vào bộ đề", problems)
    ex(conn, "DELETE FROM live.weekly_set_items WHERE set_id=:s", s=set_id)
    for pos, qid in enumerate(question_ids, 1):
        ex(conn, "INSERT INTO live.weekly_set_items (set_id, question_id, position) VALUES (:s, :q, :p)", s=set_id, q=qid, p=pos)
    audit.log(conn, admin["user_id"], "weekly_set.items", "weekly_set", set_id, {"count": len(question_ids)})
    return _view(conn, s)


def publish(conn: Connection, admin: dict, set_id: int) -> dict:
    s = _lock_set(conn, set_id)
    if s["status"] != "draft":
        raise conflict("INVALID_STATE", f"Chỉ publish được bộ đề DRAFT (hiện: {s['status']})", {"status": s["status"]})
    if q1(conn, "SELECT 1 AS x FROM live.weekly_sets WHERE status='published'"):
        raise conflict("ANOTHER_SET_PUBLISHED", "Đang có bộ đề khác được PUBLISH; đóng tuần đó trước")
    items = _items(conn, set_id)
    if not items:
        raise conflict("EMPTY_SET", "Không publish bộ đề rỗng")
    bad = {"not_ready_or_flagged": [it["question_id"] for it in items if it["status"] != "ready" or it["is_flagged"]],
           **_test_problems(conn, [it["question_id"] for it in items])}
    if any(bad.values()):
        raise conflict("SET_NOT_PUBLISHABLE", "Có câu chưa đủ điều kiện phát hành (cổng duyệt cuối)", {k: v for k, v in bad.items() if v})
    ex(conn, "UPDATE live.weekly_sets SET status='published', published_at=now() WHERE set_id=:i", i=set_id)
    audit.log(conn, admin["user_id"], "weekly_set.publish", "weekly_set", set_id, {"questions": len(items)})
    return get(conn, set_id)


def close(conn: Connection, admin: dict, set_id: int) -> dict:
    """Một transaction: khóa set → archive câu READY của bộ (không đụng retired) → chạy hook xếp hạng → closed."""
    s = _lock_set(conn, set_id)
    if s["status"] != "published":
        raise conflict("INVALID_STATE", f"Chỉ đóng được bộ đề PUBLISHED (hiện: {s['status']})", {"status": s["status"]})
    if sr.get(conn, "weekly.close_requires_cutoff") and datetime.now(_tz()) < ends_at(s["week_start"]):
        raise conflict("BEFORE_CUTOFF", "Chưa tới mốc kết thúc tuần", {"ends_at": ends_at(s["week_start"]).isoformat()})
    results = [h(conn, set_id) for h in CLOSE_HOOKS]
    archived = ex(conn, """UPDATE live.questions SET status='archived', archived_at=now()
                           WHERE status='ready' AND question_id IN (SELECT question_id FROM live.weekly_set_items WHERE set_id=:s)""", s=set_id)
    ex(conn, "UPDATE live.weekly_sets SET status='closed', closed_at=now() WHERE set_id=:i", i=set_id)
    audit.log(conn, admin["user_id"], "weekly_set.close", "weekly_set", set_id, {"archived": archived, "hooks": [r for r in results if r]})
    warnings = [] if CLOSE_HOOKS else ["weekly_results/pass_rate CHƯA được tính: module xếp hạng chưa đăng ký CLOSE_HOOKS"]
    return _view(conn, q1(conn, "SELECT * FROM live.weekly_sets WHERE set_id=:i", i=set_id), warnings)


# ------------------------------------------------------------------------------------------- tác động của retire
def on_question_retired(conn: Connection, question_id: int) -> str | None:
    it = q1(conn, "SELECT i.set_id, s.status FROM live.weekly_set_items i JOIN live.weekly_sets s USING (set_id) WHERE i.question_id=:q", q=question_id)
    if not it:
        return None
    if it["status"] == "published":
        ex(conn, "UPDATE live.weekly_set_items SET is_voided=true WHERE question_id=:q", q=question_id)
        return "voided_in_published_set"
    if it["status"] == "draft":
        ex(conn, "DELETE FROM live.weekly_set_items WHERE question_id=:q", q=question_id)
        ex(conn, "UPDATE live.weekly_set_items SET position = position + 1000 WHERE set_id=:s", s=it["set_id"])
        ex(conn, """UPDATE live.weekly_set_items i SET position = n.rn FROM (SELECT question_id, row_number() OVER (ORDER BY position) AS rn
                    FROM live.weekly_set_items WHERE set_id=:s) n WHERE i.set_id=:s AND i.question_id = n.question_id""", s=it["set_id"])
        return "removed_from_draft_set"
    return None


# ------------------------------------------------------------------------------------------- người học
def current_set(conn: Connection) -> dict:
    s = q1(conn, "SELECT * FROM live.weekly_sets WHERE status='published'")
    if not s:
        raise not_found("Chưa có bộ đề nào đang mở")
    return s


def learner_view(conn: Connection) -> dict:
    s = current_set(conn)
    n = q1(conn, "SELECT count(*) AS n FROM live.weekly_set_items WHERE set_id=:s", s=s["set_id"])["n"]
    return {"set_id": s["set_id"], "title": s["title"], "week_start": s["week_start"], "ends_at": ends_at(s["week_start"]),
            "question_count": n, "solved_count": 0}      # solved_count cần bài nộp (module chấm điểm) — chưa có nguồn dữ liệu


def learner_questions(conn: Connection, difficulty, skill_id, solved, search, page: int, size: int) -> dict:
    s = current_set(conn)
    conds, p = ["i.set_id=:s"], {"s": s["set_id"]}
    if difficulty:
        conds.append("qq.difficulty=:d"); p["d"] = difficulty
    if skill_id:
        conds.append("qq.skill_ids @> ARRAY[:k]::int[]"); p["k"] = skill_id
    if search:
        conds.append("qq.title ILIKE :t"); p["t"] = f"%{search}%"
    if solved is True:                       # chưa có dữ liệu bài nộp: không câu nào được coi là đã giải
        conds.append("false")
    where = " AND ".join(conds)
    total = q1(conn, f"SELECT count(*) AS n FROM live.weekly_set_items i JOIN live.questions qq USING (question_id) WHERE {where}", **p)["n"]
    rows = q(conn, f"""SELECT i.position, i.is_voided, qq.question_id, qq.title, qq.difficulty, qq.skill_ids
                       FROM live.weekly_set_items i JOIN live.questions qq USING (question_id) WHERE {where}
                       ORDER BY i.position LIMIT :l OFFSET :o""", l=size, o=(page - 1) * size, **p)
    names = {r["skill_id"]: r["name"] for r in q(conn, "SELECT skill_id, name FROM core.skills")}
    return {"items": [{"question_id": r["question_id"], "position": r["position"], "title": r["title"], "difficulty": r["difficulty"],
                       "skills": [names[i] for i in r["skill_ids"] if i in names], "solved": False, "is_voided": r["is_voided"]} for r in rows],
            "total": total, "page": page, "page_size": size}


def learner_question(conn: Connection, question_id: int) -> dict:
    s = current_set(conn)
    r = q1(conn, """SELECT qq.question_id, qq.title, qq.question, qq.difficulty, qq.skill_ids, qq.tables_used, qq.schema_text, i.is_voided
                    FROM live.weekly_set_items i JOIN live.questions qq USING (question_id) WHERE i.set_id=:s AND i.question_id=:q""", s=s["set_id"], q=question_id)
    if not r:
        raise not_found("Không tìm thấy câu hỏi")          # không thuộc bộ đề đang mở ⇒ 404 (không lộ tồn tại)
    names = {x["skill_id"]: x["name"] for x in q(conn, "SELECT skill_id, name FROM core.skills")}
    return {"question_id": r["question_id"], "title": r["title"], "question": r["question"], "difficulty": r["difficulty"],
            "skills": [names[i] for i in r["skill_ids"] if i in names], "tables_used": r["tables_used"], "schema_text": r["schema_text"],
            "solved": False, "is_voided": r["is_voided"], "attempt_count": 0}


def learner_history(conn: Connection, page: int, size: int) -> dict:
    """Lịch sử tóm tắt các tuần đã đóng: KHÔNG có nội dung đề (không mở lại đề sau khi đóng)."""
    total = q1(conn, "SELECT count(*) AS n FROM live.weekly_sets WHERE status='closed'")["n"]
    rows = q(conn, """SELECT s.set_id, s.title, s.week_start, s.closed_at,
                      (SELECT count(*) FROM live.weekly_set_items i WHERE i.set_id = s.set_id) AS question_count,
                      (SELECT count(*) FROM live.weekly_set_items i WHERE i.set_id = s.set_id AND i.is_voided) AS voided_count
                      FROM live.weekly_sets s WHERE s.status='closed' ORDER BY s.week_start DESC LIMIT :l OFFSET :o""", l=size, o=(page - 1) * size)
    return {"items": rows, "total": total, "page": page, "page_size": size}
