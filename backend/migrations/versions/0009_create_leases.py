"""Create the leases table.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("browser_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leases_browser_id", "leases", ["browser_id"])
    op.create_index("ix_leases_owner_id", "leases", ["owner_id"])
    op.create_index("ix_leases_expires_at", "leases", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_leases_expires_at", "leases")
    op.drop_index("ix_leases_owner_id", "leases")
    op.drop_index("ix_leases_browser_id", "leases")
    op.drop_table("leases")
