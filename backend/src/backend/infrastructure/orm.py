"""
SQLModel table definitions for the backend's schema.

One file is the single registration point Alembic imports to see the metadata;
split it per feature only once it grows hard to navigate.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

from backend.features.browsers.application.models import BrowserState


class DatabaseModel(SQLModel):
    """Columns every table carries."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class BrowserModel(DatabaseModel, table=True):
    """A provisioned browser slot and the state the pool last saw it in."""

    __tablename__ = "browsers"

    data_plane_url: str
    tunnel_url: str
    screencast_url: str
    # Stored as plain text: the set of states still moves, and a native enum
    # type would need a migration for every new member.
    state: BrowserState = Field(sa_column=Column(String, nullable=False))
