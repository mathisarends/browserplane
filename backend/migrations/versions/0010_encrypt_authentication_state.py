"""Encrypt persisted authentication state and remove its unused source label.

Revision ID: 0010
Revises: 0009
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.settings import SessionSettings

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTHENTICATION_STATE_TABLES = (
    "suspended_sessions",
    "authentication_state_snapshots",
)


def upgrade() -> None:
    cipher = _cipher()
    for table in AUTHENTICATION_STATE_TABLES:
        _encrypt_authentication_state(table, cipher)
    op.drop_column("authentication_state_snapshots", "source_browser")


def downgrade() -> None:
    cipher = _cipher()
    for table in AUTHENTICATION_STATE_TABLES:
        _decrypt_authentication_state(table, cipher)
    op.add_column(
        "authentication_state_snapshots",
        sa.Column(
            "source_browser",
            sa.String(),
            nullable=False,
            server_default="Unknown",
        ),
    )
    op.alter_column(
        "authentication_state_snapshots",
        "source_browser",
        server_default=None,
    )


def _cipher() -> AuthenticationStateCipher:
    key = SessionSettings().authentication_state_encryption_key.get_secret_value()
    return AuthenticationStateCipher(key)


def _encrypt_authentication_state(
    table: str, cipher: AuthenticationStateCipher
) -> None:
    encrypted_column = "authentication_state_encrypted"
    op.add_column(table, sa.Column(encrypted_column, sa.LargeBinary(), nullable=True))
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text(f"SELECT id, authentication_state FROM {table}")
        ).mappings()
    )
    for row in rows:
        connection.execute(
            sa.text(
                f"UPDATE {table} SET {encrypted_column} = :ciphertext WHERE id = :id"
            ),
            {
                "ciphertext": cipher.encrypt(row["authentication_state"]),
                "id": row["id"],
            },
        )
    op.alter_column(table, encrypted_column, nullable=False)
    op.drop_column(table, "authentication_state")
    op.alter_column(
        table,
        encrypted_column,
        new_column_name="authentication_state",
    )


def _decrypt_authentication_state(
    table: str, cipher: AuthenticationStateCipher
) -> None:
    decrypted_column = "authentication_state_decrypted"
    op.add_column(table, sa.Column(decrypted_column, JSONB(), nullable=True))
    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text(f"SELECT id, authentication_state FROM {table}")
        ).mappings()
    )
    for row in rows:
        state = cipher.decrypt(bytes(row["authentication_state"]))
        connection.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET {decrypted_column} = CAST(:state AS JSONB) WHERE id = :id"
            ),
            {
                "state": json.dumps(state, ensure_ascii=False),
                "id": row["id"],
            },
        )
    op.alter_column(table, decrypted_column, nullable=False)
    op.drop_column(table, "authentication_state")
    op.alter_column(
        table,
        decrypted_column,
        new_column_name="authentication_state",
    )
