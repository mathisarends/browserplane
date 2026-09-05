"""Split reusable browser and authentication state.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authentication_state_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_browser", sa.String(), nullable=False),
        sa.Column("authentication_state", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_authentication_state_snapshots_owner_id"),
        "authentication_state_snapshots",
        ["owner_id"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO authentication_state_snapshots
            (id, created_at, owner_id, name, source_browser, authentication_state)
        SELECT id, created_at, owner_id, name, source_browser, authentication_state
        FROM browser_state_snapshots
        """
    )
    op.drop_column("browser_state_snapshots", "authentication_state")


def downgrade() -> None:
    op.add_column(
        "browser_state_snapshots",
        sa.Column("authentication_state", postgresql.JSONB(), nullable=True),
    )
    op.execute(
        """
        UPDATE browser_state_snapshots AS browser
        SET authentication_state = authentication.authentication_state
        FROM authentication_state_snapshots AS authentication
        WHERE authentication.id = browser.id
        """
    )
    op.execute(
        """
        UPDATE browser_state_snapshots
        SET authentication_state = '{"cookies": [], "origins": []}'::jsonb
        WHERE authentication_state IS NULL
        """
    )
    op.alter_column("browser_state_snapshots", "authentication_state", nullable=False)
    op.drop_index(
        op.f("ix_authentication_state_snapshots_owner_id"),
        table_name="authentication_state_snapshots",
    )
    op.drop_table("authentication_state_snapshots")
