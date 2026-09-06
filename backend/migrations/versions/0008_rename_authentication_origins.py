"""Name authentication local storage explicitly.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _rename_key("origins", "localStorage")


def downgrade() -> None:
    _rename_key("localStorage", "origins")


def _rename_key(old: str, new: str) -> None:
    for table in ("suspended_sessions", "authentication_state_snapshots"):
        op.execute(
            f"""
            UPDATE {table}
            SET authentication_state =
                (authentication_state - '{old}')
                || jsonb_build_object(
                    '{new}',
                    COALESCE(authentication_state -> '{old}', '[]'::jsonb)
                )
            WHERE authentication_state ? '{old}'
            """
        )
