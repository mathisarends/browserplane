from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from backend.features.browsers.domain.models import Browser
from backend.features.leases.domain.models import Lease

type AuthenticationStateDocument = dict[str, Any]
type BrowserStateDocument = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Download:
    id: str
    filename: str
    url: str
    size: int


class SessionStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class Session:
    """Persistent aggregate root for the browser-session lifecycle."""

    id: UUID
    owner_id: UUID
    status: SessionStatus
    created_at: datetime
    expires_at: datetime | None
    browser_checkpoint_id: UUID | None = None

    def suspend(self, checkpoint_id: UUID, expires_at: datetime) -> Session:
        if self.status is not SessionStatus.ACTIVE:
            raise ValueError("Only an active session can be suspended")
        return replace(
            self,
            status=SessionStatus.SUSPENDED,
            expires_at=expires_at,
            browser_checkpoint_id=checkpoint_id,
        )

    def resume(self, expires_at: datetime) -> Session:
        if self.status is not SessionStatus.SUSPENDED:
            raise ValueError("Only a suspended session can be resumed")
        return replace(
            self,
            status=SessionStatus.ACTIVE,
            expires_at=expires_at,
            browser_checkpoint_id=None,
        )

    def renew(self, expires_at: datetime) -> Session:
        if self.status is not SessionStatus.ACTIVE:
            raise ValueError("Only an active session can be renewed")
        return replace(self, expires_at=expires_at)

    def close(self) -> Session:
        if self.status is SessionStatus.CLOSED:
            return self
        return replace(self, status=SessionStatus.CLOSED, expires_at=None)

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= now


@dataclass(frozen=True, slots=True)
class ActiveSession:
    """An active aggregate together with its current lease and browser."""

    session: Session
    lease: Lease
    browser: Browser

    @property
    def id(self) -> UUID:
        return self.session.id

    @property
    def owner_id(self) -> UUID:
        return self.session.owner_id

    @property
    def browser_id(self) -> UUID:
        return self.browser.id


@dataclass(frozen=True, slots=True)
class BrowserCheckpoint:
    """Persisted browser state that can be mounted again later."""

    id: UUID
    owner_id: UUID
    browser_state: BrowserStateDocument
    authentication_profile_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticationProfile:
    """Named, mutable login identity; its state remains backend-internal."""

    id: UUID
    owner_id: UUID
    name: str
    authentication_state: AuthenticationStateDocument
    created_at: datetime
