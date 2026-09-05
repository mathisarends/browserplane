"""Create the browsers table

Revision ID: 0001
Revises:
Create Date: 2026-09-05 08:14:50.327137

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "browsers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_plane_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tunnel_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("screencast_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("browsers")
