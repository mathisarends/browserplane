"""
SQLModel table definitions for the backend's schema.

One file is the single registration point Alembic imports to see the metadata;
split it per feature only once it grows hard to navigate.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from backend.features.browsers.application.models import BrowserState


class DatabaseModel(SQLModel):
    """Columns every table carries."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # sa_type, not sa_column: a Column instance belongs to one table, and this
    # base class is shared by all of them.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


class BrowserModel(DatabaseModel, table=True):
    """A provisioned browser slot and the state the pool last saw it in."""

    __tablename__ = "browsers"

    data_plane_url: str
    # Stored as plain text: the set of states still moves, and a native enum
    # type would need a migration for every new member.
    state: BrowserState = Field(sa_column=Column(String, nullable=False))


class SuspendedSessionModel(DatabaseModel, table=True):
    """A session that gave its browser back, and what it needs to come back."""

    __tablename__ = "suspended_sessions"

    owner_id: UUID
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    # Kept as separate opaque data-plane documents: authentication can be
    # reused without also restoring a suspended browser's tabs (and vice versa).
    authentication_state: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False)
    )
    browser_state: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))


class BrowserStateSnapshotModel(DatabaseModel, table=True):
    """A reusable browser state captured explicitly by a user."""

    __tablename__ = "browser_state_snapshots"

    owner_id: UUID = Field(index=True)
    name: str
    source_browser: str
    authentication_state: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False)
    )
    browser_state: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
