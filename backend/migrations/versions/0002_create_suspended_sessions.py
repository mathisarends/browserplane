"""Create the suspended_sessions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suspended_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Sweeping the suspensions nobody came back for is a scan over this column.
    op.create_index(
        "ix_suspended_sessions_expires_at",
        "suspended_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_suspended_sessions_expires_at", "suspended_sessions")
    op.drop_table("suspended_sessions")
