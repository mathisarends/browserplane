"""Reset authentication profiles for complete origin storage snapshots."""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing profiles lack IndexedDB and cannot be upgraded after capture.
    op.execute(
        "UPDATE session_requests SET authentication_profile_id = NULL "
        "WHERE authentication_profile_id IS NOT NULL"
    )
    op.execute("DELETE FROM authentication_profiles")


def downgrade() -> None:
    # Deleted credentials cannot be reconstructed.
    pass
