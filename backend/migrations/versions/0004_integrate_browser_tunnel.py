"""Remove endpoints that are derived or no longer run as separate services."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_integrate_browser_tunnel"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("browsers", "tunnel_url")
    op.drop_column("browsers", "screencast_url")


def downgrade() -> None:
    op.add_column(
        "browsers",
        sa.Column("screencast_url", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "browsers",
        sa.Column("tunnel_url", sa.String(), nullable=False, server_default=""),
    )
