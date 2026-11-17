"""Allow return_needs_human action in live.admin_overrides.

Revision ID: 0005
Revises: 0004
"""
from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "db" / "0005_admin_override_return_needs_human.sql"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DELETE FROM live.admin_overrides WHERE action = 'return_needs_human';")
    op.execute("ALTER TABLE live.admin_overrides DROP CONSTRAINT IF EXISTS admin_overrides_action_check;")
    op.execute(
        "ALTER TABLE live.admin_overrides ADD CONSTRAINT admin_overrides_action_check "
        "CHECK (action IN ('approve', 'reject', 'retire', 'restore'));"
    )
