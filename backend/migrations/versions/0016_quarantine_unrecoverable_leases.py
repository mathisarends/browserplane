"""Keep a quarantined lease holding on to its browser.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A quarantined lease is not terminal: its browser is still occupied by a
# runtime nobody could clean up, so the slot must stay claimed by this lease.
LIVE_STATES = "state IN ('active', 'reclaiming', 'failed', 'quarantined')"
PREVIOUS_LIVE_STATES = "state IN ('active', 'reclaiming', 'failed')"


def upgrade() -> None:
    op.drop_index("uq_leases_current_browser", table_name="leases")
    op.create_index(
        "uq_leases_current_browser",
        "leases",
        ["browser_id"],
        unique=True,
        postgresql_where=sa.text(LIVE_STATES),
    )


def downgrade() -> None:
    op.execute("UPDATE leases SET state = 'failed' WHERE state = 'quarantined'")
    op.drop_index("uq_leases_current_browser", table_name="leases")
    op.create_index(
        "uq_leases_current_browser",
        "leases",
        ["browser_id"],
        unique=True,
        postgresql_where=sa.text(PREVIOUS_LIVE_STATES),
    )
