"""Hạ tầng test: PostgreSQL THẬT (không mock DB). Tạo DB tạm, chạy Alembic, seed Core, dùng Enterprise DB thật (chỉ đọc).
Chỉ transport HTTP tới Ollama bị thay bằng FakeOllama; engine kiểm tra/chạy SQL là mã thật.

Biến môi trường (mặc định cho môi trường dev cục bộ):
  TEST_PG_ADMIN_DSN   kết nối quyền tạo DB       (postgresql://postgres:postgres@localhost:5432/postgres)
  TEST_ENTERPRISE_*   kết nối Enterprise DB chỉ đọc (DB enterprise_db, user sqlarena_ai_ro)
"""
import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

ADMIN_DSN = os.environ.get("TEST_PG_ADMIN_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")
TEST_DB = "sqlarena_app_pytest"
os.environ["DATABASE_URL"] = ADMIN_DSN.replace("postgresql://", "postgresql+psycopg://").rsplit("/", 1)[0] + f"/{TEST_DB}"
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENTERPRISE_DB_USER", os.environ.get("TEST_ENTERPRISE_USER", "sqlarena_ai_ro"))
os.environ.setdefault("ENTERPRISE_DB_PASSWORD", os.environ.get("TEST_ENTERPRISE_PASSWORD", "ro_pass"))
os.environ.setdefault("CATALOG_DB_USER", os.environ.get("TEST_CATALOG_USER", "postgres"))
os.environ.setdefault("CATALOG_DB_PASSWORD", os.environ.get("TEST_CATALOG_PASSWORD", "postgres"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.pipeline import engine as eng  # noqa: E402
from app.pipeline import ledger  # noqa: E402
from app.security import make_token  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    with psycopg.connect(ADMIN_DSN, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        c.execute(f"CREATE DATABASE {TEST_DB}")
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, capture_output=True, text=True, env=os.environ)
    assert r.returncode == 0, r.stderr
    db.reset_engine()
    from app.seed import seed_core
    with db.begin() as conn:
        seed_core(conn)
        for role, email in (("admin", "admin@test.io"), ("learner", "learner@test.io"), ("admin", "locked@test.io")):
            db.ex(conn, "INSERT INTO live.users (role_id, email, username, password_hash, status) SELECT role_id, :e, :u, 'x', :s FROM live.roles WHERE name=:r",
                  e=email, u=email.split("@")[0], r=role, s="locked" if email.startswith("locked") else "active")
    ledger.install()
    yield
    db.reset_engine()


@pytest.fixture(autouse=True)
def clean():
    """Mỗi test bắt đầu với hàng đợi/câu hỏi trống và cấu hình mặc định."""
    with db.begin() as conn:
        conn.exec_driver_sql("TRUNCATE live.submissions, live.weekly_set_items, live.weekly_sets, draft.llm_call_ledger, draft.review_logs, draft.self_solve_runs, live.test_cases, live.questions, "
                             "draft.question_drafts, draft.generation_jobs, live.admin_overrides, live.audit_logs RESTART IDENTITY CASCADE")
        conn.exec_driver_sql("DELETE FROM core.system_settings")
        from app.services import settings_registry
        settings_registry.ensure_defaults(conn)
    eng.set_transport(None)
    yield
    eng.set_transport(None)


def _uid(email: str) -> int:
    with db.begin() as conn:
        return db.q1(conn, "SELECT user_id FROM live.users WHERE email=:e", e=email)["user_id"]


@pytest.fixture
def client():
    return TestClient(__import__("app.main", fromlist=["app"]).app)


@pytest.fixture
def admin_h():
    return {"Authorization": f"Bearer {make_token(_uid('admin@test.io'))}"}


@pytest.fixture
def learner_h():
    return {"Authorization": f"Bearer {make_token(_uid('learner@test.io'))}"}


@pytest.fixture
def admin_id():
    return _uid("admin@test.io")


@pytest.fixture
def skill_id():
    def lookup(code: str) -> int:
        with db.begin() as conn:
            return db.q1(conn, "SELECT skill_id FROM core.skills WHERE code=:c", c=code)["skill_id"]
    return lookup


def new_worker(name="w-test"):
    from app.worker import Worker
    return Worker(worker_id=name)


def enqueue_job(admin_id: int, quantity=1, difficulty=1, code="S1", topic="Human Resources") -> int:
    with db.begin() as conn:
        sk = db.q1(conn, "SELECT skill_id FROM core.skills WHERE code=:c", c=code)["skill_id"]
        w = db.q1(conn, "SELECT world_id FROM core.worlds WHERE name='enterprise_v1'")["world_id"]
        return db.q1(conn, "INSERT INTO draft.generation_jobs (world_id, triggered_by, difficulty, skill_ids, topic, requested_count) "
                           "VALUES (:w, :u, :d, :s, :t, :n) RETURNING job_id", w=w, u=admin_id, d=difficulty, s=[sk], t=topic, n=quantity)["job_id"]


def make_question(difficulty=1, code="S1", title=None, status="ready", with_test=True, flagged=False) -> int:
    """Chèn thẳng một câu hỏi live (không qua pipeline) để test bộ đề tuần."""
    with db.begin() as conn:
        w = db.q1(conn, "SELECT world_id FROM core.worlds WHERE name='enterprise_v1'")["world_id"]
        sk = db.q1(conn, "SELECT skill_id FROM core.skills WHERE code=:c", c=code)["skill_id"]
        n = db.q1(conn, "SELECT count(*) + 1 AS n FROM live.questions")["n"]
        qid = db.q1(conn, """INSERT INTO live.questions (world_id, title, question, reference_sql, compare_mode, difficulty, skill_ids, tables_used, schema_text,
                             status, is_flagged, archived_at, retired_at, retire_reason)
                             VALUES (:w, :t, 'Câu hỏi thử', 'SELECT 1', 'unordered', :d, :s, ARRAY['employees'], 'employees(...)', CAST(:st AS varchar), :f,
                                     CASE WHEN CAST(:st AS varchar)='archived' THEN now() END, CASE WHEN CAST(:st AS varchar)='retired' THEN now() END,
                                     CASE WHEN CAST(:st AS varchar)='retired' THEN 'x' END)
                             RETURNING question_id""", w=w, t=title or f"Câu {n}", d=difficulty, s=[sk], st=status, f=flagged)["question_id"]
        if with_test:
            expected = '{"columns": ["x"], "rows": [[1]], "row_count": 1, "result_hash": "h", "compare_mode": "unordered"}'
            db.ex(conn, "INSERT INTO live.test_cases (question_id, dataset_ref, dataset_version, type, expected_result) "
                        "VALUES (:q, 'enterprise/base', 1, 'standard', CAST(:e AS jsonb))", q=qid, e=expected)
        return qid


def set_week_target(client, headers, e=0, m=0, h=0):
    r = client.put("/api/v1/admin/settings/weekly.question_count", json={"value": {"1": e, "2": m, "3": h}}, headers=headers)
    assert r.status_code == 200, r.text
