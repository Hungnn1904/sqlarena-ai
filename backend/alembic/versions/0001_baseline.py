"""Baseline: core/draft/live (phần AI pipeline & quản lý câu hỏi)

Revision ID: 0001
Revises:
"""
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "db" / "0001_baseline.sql"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Chỉ xóa những gì revision này tạo ra. live.roles/users là bảng dùng chung với module Auth nên giữ nguyên
    # nếu module Auth đã tạo trước; ở đây xóa cả hai chỉ khi không còn dữ liệu người dùng.
    op.execute("""
        DROP SCHEMA IF EXISTS draft CASCADE;
        DROP TABLE IF EXISTS live.audit_logs, live.admin_overrides, live.test_cases, live.questions CASCADE;
        DROP SCHEMA IF EXISTS core CASCADE;
    """)
