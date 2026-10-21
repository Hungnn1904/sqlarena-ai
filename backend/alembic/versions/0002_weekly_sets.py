"""Bộ đề tuần: live.weekly_sets, live.weekly_set_items

Revision ID: 0002
Revises: 0001
"""
from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "db" / "0002_weekly_sets.sql"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS live.weekly_set_items; DROP TABLE IF EXISTS live.weekly_sets;")
