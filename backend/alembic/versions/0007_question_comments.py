"""Add live.question_comments for per-question SQL discussion.

Revision ID: 0007
Revises: 0006
"""
from pathlib import Path

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "db" / "0007_question_comments.sql"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS live.question_comments CASCADE;")
