"""Add renewable browser leases and fencing generations.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "browsers",
        sa.Column("generation", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "leases",
        sa.Column("generation", sa.BigInteger(), nullable=False, server_default="1"),
    )
    op.add_column(
        "leases",
        sa.Column("state", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "leases",
        sa.Column("last_renewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leases",
        sa.Column("reclaim_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leases", sa.Column("reclaim_started_at", sa.DateTime(timezone=True))
    )
    op.add_column("leases", sa.Column("released_at", sa.DateTime(timezone=True)))
    op.add_column("leases", sa.Column("release_reason", sa.String()))
    op.add_column(
        "leases",
        sa.Column("cleanup_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "leases", sa.Column("cleanup_retry_at", sa.DateTime(timezone=True))
    )
    op.execute("UPDATE leases SET last_renewed_at = created_at")
    op.execute("UPDATE leases SET reclaim_after = expires_at + INTERVAL '45 seconds'")
    op.execute(
        "UPDATE browsers SET generation = leases.generation "
        "FROM leases WHERE leases.browser_id = browsers.id"
    )
    op.alter_column("leases", "last_renewed_at", nullable=False)
    op.alter_column("leases", "reclaim_after", nullable=False)
    op.create_index("ix_leases_state", "leases", ["state"])
    op.create_index("ix_leases_reclaim_after", "leases", ["reclaim_after"])
    op.create_index("ix_leases_cleanup_retry_at", "leases", ["cleanup_retry_at"])
    op.create_unique_constraint(
        "uq_leases_browser_generation", "leases", ["browser_id", "generation"]
    )
    op.create_index(
        "uq_leases_current_browser",
        "leases",
        ["browser_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('active', 'reclaiming', 'failed')"),
    )
    op.alter_column("browsers", "generation", server_default=None)
    op.alter_column("leases", "generation", server_default=None)
    op.alter_column("leases", "state", server_default=None)
    op.alter_column("leases", "cleanup_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_leases_current_browser", table_name="leases")
    op.drop_constraint("uq_leases_browser_generation", "leases", type_="unique")
    op.drop_index("ix_leases_cleanup_retry_at", table_name="leases")
    op.drop_index("ix_leases_reclaim_after", table_name="leases")
    op.drop_index("ix_leases_state", table_name="leases")
    op.drop_column("leases", "cleanup_retry_at")
    op.drop_column("leases", "cleanup_attempts")
    op.drop_column("leases", "release_reason")
    op.drop_column("leases", "released_at")
    op.drop_column("leases", "reclaim_started_at")
    op.drop_column("leases", "reclaim_after")
    op.drop_column("leases", "last_renewed_at")
    op.drop_column("leases", "state")
    op.drop_column("leases", "generation")
    op.drop_column("browsers", "generation")
