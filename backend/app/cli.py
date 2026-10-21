"""CLI vận hành:  python -m app.cli <lệnh>
  migrate        chạy Alembic upgrade head
  seed           nạp world/skills/đề nguồn + cấu hình mặc định (chạy lặp an toàn)
  create-admin   tạo tài khoản admin dev (chỉ để chạy thử khi chưa có module Auth)
  token          in access token cho user (dev)
  worker         chạy Generation/Review Worker
  worker --once  chạy đúng một nhịp rồi thoát
  check          kiểm tra cấu hình engine + Enterprise DB + Ollama (không tốn call sinh)
"""
import argparse
import logging
import subprocess
import sys

from .config import BACKEND_DIR


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate"); sub.add_parser("seed"); sub.add_parser("check")
    ca = sub.add_parser("create-admin"); ca.add_argument("--email", required=True); ca.add_argument("--username", required=True)
    tk = sub.add_parser("token"); tk.add_argument("--user-id", type=int, required=True)
    wk = sub.add_parser("worker"); wk.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if a.cmd == "migrate":
        return subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR)
    if a.cmd == "seed":
        from .db import begin
        from .seed import seed_core
        with begin() as conn:
            print(seed_core(conn))
        return 0
    if a.cmd == "create-admin":
        from .db import begin, q1
        with begin() as conn:
            row = q1(conn, "INSERT INTO live.users (role_id, email, username, password_hash, display_name) "
                           "SELECT role_id, :e, :u, 'dev-only-no-login', :u FROM live.roles WHERE name='admin' "
                           "ON CONFLICT DO NOTHING RETURNING user_id", e=a.email, u=a.username)
            row = row or q1(conn, "SELECT user_id FROM live.users WHERE lower(email)=lower(:e)", e=a.email)
        print("user_id =", row["user_id"])
        return 0
    if a.cmd == "token":
        from .security import make_token
        print(make_token(a.user_id, 30))
        return 0
    if a.cmd == "check":
        from .db import begin
        from .pipeline import engine as eng
        from .pipeline.catalog import load_engine_data, verify_catalog
        cfg = eng.load_engine_config()
        with begin() as conn:
            data = load_engine_data(conn, cfg["WORLD_ID"])
        verify_catalog(cfg, data)
        print("Core + schema Enterprise: OK")
        print("Datasets:", [(d.ref, d.version[:12]) for d in eng.rv.build_datasets(cfg)])
        print("Ollama:", eng.arena.check_ollama(cfg)["available"])
        return 0
    if a.cmd == "worker":
        from .worker import Worker
        w = Worker()
        print(w.run_once()) if a.once else w.run_forever()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
