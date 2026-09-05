"""Create reusable browser state snapshots.

Revision ID: 0005
Revises: 0004_integrate_browser_tunnel
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004_integrate_browser_tunnel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browser_state_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_browser", sa.String(), nullable=False),
        sa.Column("authentication_state", postgresql.JSONB(), nullable=False),
        sa.Column("browser_state", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_browser_state_snapshots_owner_id"),
        "browser_state_snapshots",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_browser_state_snapshots_owner_id"),
        table_name="browser_state_snapshots",
    )
    op.drop_table("browser_state_snapshots")
