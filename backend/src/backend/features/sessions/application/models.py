from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.leases.application.models import Lease

type AuthenticationStateDocument = dict[str, Any]
type BrowserStateDocument = dict[str, Any]
"""Captured state documents, exactly as the data plane hands them over.

The backend does not model the payloads: their shapes are owned by the data
plane's authentication and browser-state schemas and travel back there
unchanged. Re-modelling them here would mean a migration every time the data
plane learns to capture one more thing.
"""


class SessionStatus(StrEnum):
    """Whether a session currently holds a browser."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(frozen=True, slots=True)
class Session:
    """One frontend workspace: a lease plus the browser it may talk to."""

    lease: Lease
    browser: Browser

    @property
    def id(self) -> UUID:
        return self.lease.id

    @property
    def browser_id(self) -> UUID:
        return self.browser.id

    @property
    def cdp_url(self) -> str:
        return self.browser.slot.cdp_url

    @property
    def screencast_url(self) -> str:
        return self.browser.slot.screencast_url


@dataclass(frozen=True, slots=True)
class SuspendedSession:
    """A session that gave its browser back but can be picked up again.

    Waiting for a human takes hours, and holding a Chromium process open for
    that long wastes a pool slot. Suspending stores what the browser held and
    frees it; resuming mounts that state onto whichever browser is free then.
    The id is the session's, so the links handed out before still work.
    """

    id: UUID
    owner_id: UUID
    authentication_state: AuthenticationStateDocument
    browser_state: BrowserStateDocument
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now


@dataclass(frozen=True, slots=True)
class BrowserStateSnapshot:
    """A named, reusable browser state persisted independently of a session."""

    id: UUID
    owner_id: UUID
    name: str
    source_browser: str
    authentication_state: AuthenticationStateDocument
    browser_state: BrowserStateDocument
    created_at: datetime
