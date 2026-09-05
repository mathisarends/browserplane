"""Split authentication from suspended browser state.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "suspended_sessions",
        sa.Column("authentication_state", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "suspended_sessions",
        sa.Column("browser_state", postgresql.JSONB(), nullable=True),
    )
    op.execute(
        """
        UPDATE suspended_sessions
        SET authentication_state = COALESCE(
                state -> 'authentication',
                '{"cookies": [], "origins": []}'::jsonb
            ),
            browser_state = state - 'authentication'
        """
    )
    op.alter_column("suspended_sessions", "authentication_state", nullable=False)
    op.alter_column("suspended_sessions", "browser_state", nullable=False)
    op.drop_column("suspended_sessions", "state")


def downgrade() -> None:
    op.add_column(
        "suspended_sessions",
        sa.Column("state", postgresql.JSONB(), nullable=True),
    )
    op.execute(
        """
        UPDATE suspended_sessions
        SET state = browser_state || jsonb_build_object(
            'authentication', authentication_state
        )
        """
    )
    op.alter_column("suspended_sessions", "state", nullable=False)
    op.drop_column("suspended_sessions", "browser_state")
    op.drop_column("suspended_sessions", "authentication_state")
