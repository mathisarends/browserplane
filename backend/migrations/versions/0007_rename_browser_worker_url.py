"""Rename the browser worker address column.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "browsers",
        "data_plane_url",
        new_column_name="browser_worker_url",
    )


def downgrade() -> None:
    op.alter_column(
        "browsers",
        "browser_worker_url",
        new_column_name="data_plane_url",
    )
