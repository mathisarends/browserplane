from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Column, DateTime, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from backend.features.browsers.domain.models import BrowserState


class DatabaseModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # sa_type, not sa_column: a Column instance belongs to one table, and this
    # base class is shared by all of them.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


class BrowserModel(DatabaseModel, table=True):
    __tablename__ = "browsers"

    browser_worker_url: str
    # Stored as plain text: the set of states still moves, and a native enum
    # type would need a migration for every new member.
    state: BrowserState = Field(sa_column=Column(String, nullable=False))
    generation: int = Field(default=0, sa_type=BigInteger, nullable=False)


class SessionRequestModel(DatabaseModel, table=True):
    __tablename__ = "session_requests"

    owner_id: UUID = Field(index=True)
    test_run_id: UUID | None = None
    status: str = Field(sa_column=Column(String, nullable=False))
    expires_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    # An assignment mints lease and session aggregate under one id; this is it.
    session_id: UUID | None = None
    browser_id: UUID | None = None
    authentication_profile_id: UUID | None = None
    browser_checkpoint_id: UUID | None = None
    retry_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    resume_session_id: UUID | None = None


class LeaseModel(DatabaseModel, table=True):
    __tablename__ = "leases"

    browser_id: UUID = Field(index=True)
    owner_id: UUID = Field(index=True)
    generation: int = Field(sa_type=BigInteger, nullable=False)
    state: str = Field(sa_column=Column(String, nullable=False, index=True))
    last_renewed_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    expires_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    reclaim_after: datetime = Field(
        sa_type=DateTime(timezone=True), nullable=False, index=True
    )
    reclaim_started_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    released_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    release_reason: str | None = None
    cleanup_attempts: int = Field(default=0, nullable=False)
    cleanup_retry_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), index=True
    )


class AuthenticationProfileModel(DatabaseModel, table=True):
    __tablename__ = "authentication_profiles"

    owner_id: UUID = Field(index=True)
    name: str
    authentication_state: bytes = Field(sa_column=Column(LargeBinary, nullable=False))


class BrowserCheckpointModel(DatabaseModel, table=True):
    __tablename__ = "browser_checkpoints"

    owner_id: UUID = Field(index=True)
    browser_state: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    authentication_profile_id: UUID | None = Field(
        default=None,
        foreign_key="authentication_profiles.id",
        ondelete="SET NULL",
        index=True,
    )


class SessionModel(DatabaseModel, table=True):
    __tablename__ = "sessions"

    owner_id: UUID = Field(index=True)
    status: str = Field(sa_column=Column(String, nullable=False))
    expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,
    )
    browser_checkpoint_id: UUID | None = Field(
        default=None,
        foreign_key="browser_checkpoints.id",
        ondelete="SET NULL",
        index=True,
    )
