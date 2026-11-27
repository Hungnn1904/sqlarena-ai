"""Add live.question_votes and live.question_reports for learner feedback.

Revision ID: 0006
Revises: 0005
"""
from pathlib import Path

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "db" / "0006_question_feedback.sql"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS live.question_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS live.question_votes CASCADE;")
