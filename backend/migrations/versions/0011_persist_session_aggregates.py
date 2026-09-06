"""Persist session aggregates, browser checkpoints, and authentication profiles.

Revision ID: 0011
Revises: 0010
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _rename_saved_state_tables()
    op.drop_column("browser_checkpoints", "name")
    op.drop_column("browser_checkpoints", "source_browser")
    op.add_column(
        "browser_checkpoints",
        sa.Column("authentication_profile_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_browser_checkpoints_authentication_profile_id"),
        "browser_checkpoints",
        ["authentication_profile_id"],
    )
    op.create_foreign_key(
        "fk_browser_checkpoints_authentication_profile_id",
        "browser_checkpoints",
        "authentication_profiles",
        ["authentication_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("browser_checkpoint_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["browser_checkpoint_id"],
            ["browser_checkpoints.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_owner_id"), "sessions", ["owner_id"])
    op.create_index(op.f("ix_sessions_status"), "sessions", ["status"])
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"])
    op.create_index(
        op.f("ix_sessions_browser_checkpoint_id"),
        "sessions",
        ["browser_checkpoint_id"],
    )
    op.execute(
        """
        INSERT INTO sessions (id, created_at, owner_id, status, expires_at)
        SELECT id, created_at, owner_id, 'active', expires_at FROM leases
        """
    )

    connection = op.get_bind()
    suspended_sessions = list(
        connection.execute(
            sa.text(
                "SELECT id, owner_id, created_at, expires_at, "
                "authentication_state, browser_state FROM suspended_sessions"
            )
        ).mappings()
    )
    for suspended in suspended_sessions:
        profile_id = uuid4()
        checkpoint_id = uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO authentication_profiles "
                "(id, owner_id, name, authentication_state, created_at) "
                "VALUES (:id, :owner_id, :name, :state, :created_at)"
            ),
            {
                "id": profile_id,
                "owner_id": suspended["owner_id"],
                "name": f"Session {suspended['id']}",
                "state": suspended["authentication_state"],
                "created_at": suspended["created_at"],
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO browser_checkpoints "
                "(id, owner_id, browser_state, authentication_profile_id, created_at) "
                "VALUES (:id, :owner_id, CAST(:state AS JSONB), "
                ":profile_id, :created_at)"
            ),
            {
                "id": checkpoint_id,
                "owner_id": suspended["owner_id"],
                "state": json.dumps(suspended["browser_state"]),
                "profile_id": profile_id,
                "created_at": suspended["created_at"],
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO sessions "
                "(id, owner_id, status, expires_at, browser_checkpoint_id, created_at) "
                "VALUES (:id, :owner_id, 'suspended', :expires_at, "
                ":checkpoint_id, :created_at)"
            ),
            {
                "id": suspended["id"],
                "owner_id": suspended["owner_id"],
                "expires_at": suspended["expires_at"],
                "checkpoint_id": checkpoint_id,
                "created_at": suspended["created_at"],
            },
        )
    op.drop_table("suspended_sessions")


def downgrade() -> None:
    op.create_table(
        "suspended_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authentication_state", sa.LargeBinary(), nullable=False),
        sa.Column("browser_state", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_suspended_sessions_expires_at"),
        "suspended_sessions",
        ["expires_at"],
    )
    op.execute(
        """
        INSERT INTO suspended_sessions
            (id, created_at, owner_id, expires_at, authentication_state, browser_state)
        SELECT session.id, session.created_at, session.owner_id, session.expires_at,
               profile.authentication_state, checkpoint.browser_state
        FROM sessions AS session
        JOIN browser_checkpoints AS checkpoint
          ON checkpoint.id = session.browser_checkpoint_id
        JOIN authentication_profiles AS profile
          ON profile.id = checkpoint.authentication_profile_id
        WHERE session.status = 'suspended'
        """
    )
    op.drop_table("sessions")

    op.drop_constraint(
        "fk_browser_checkpoints_authentication_profile_id",
        "browser_checkpoints",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_browser_checkpoints_authentication_profile_id"),
        table_name="browser_checkpoints",
    )
    op.drop_column("browser_checkpoints", "authentication_profile_id")
    op.add_column(
        "browser_checkpoints",
        sa.Column("name", sa.String(), nullable=False, server_default="Checkpoint"),
    )
    op.add_column(
        "browser_checkpoints",
        sa.Column(
            "source_browser",
            sa.String(),
            nullable=False,
            server_default="Unknown",
        ),
    )
    op.alter_column("browser_checkpoints", "name", server_default=None)
    op.alter_column("browser_checkpoints", "source_browser", server_default=None)
    _restore_saved_state_table_names()


def _rename_saved_state_tables() -> None:
    op.rename_table("authentication_state_snapshots", "authentication_profiles")
    op.drop_index(
        "ix_authentication_state_snapshots_owner_id",
        table_name="authentication_profiles",
    )
    op.create_index(
        op.f("ix_authentication_profiles_owner_id"),
        "authentication_profiles",
        ["owner_id"],
    )
    op.rename_table("browser_state_snapshots", "browser_checkpoints")
    op.drop_index(
        "ix_browser_state_snapshots_owner_id", table_name="browser_checkpoints"
    )
    op.create_index(
        op.f("ix_browser_checkpoints_owner_id"),
        "browser_checkpoints",
        ["owner_id"],
    )


def _restore_saved_state_table_names() -> None:
    op.drop_index(
        op.f("ix_browser_checkpoints_owner_id"), table_name="browser_checkpoints"
    )
    op.rename_table("browser_checkpoints", "browser_state_snapshots")
    op.create_index(
        "ix_browser_state_snapshots_owner_id",
        "browser_state_snapshots",
        ["owner_id"],
    )
    op.drop_index(
        op.f("ix_authentication_profiles_owner_id"),
        table_name="authentication_profiles",
    )
    op.rename_table("authentication_profiles", "authentication_state_snapshots")
    op.create_index(
        "ix_authentication_state_snapshots_owner_id",
        "authentication_state_snapshots",
        ["owner_id"],
    )
