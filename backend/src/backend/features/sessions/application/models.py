from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.leases.application.models import Lease

type BrowserStateDocument = dict[str, Any]
"""A captured browser state, exactly as the data plane hands it over.

The backend does not model the payload: its shape is owned by the data
plane's ``BrowserStateSchema`` and travels back there unchanged. Re-modelling
it here would mean a migration every time the data plane learns to capture
one more thing.
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
    def tunnel_url(self) -> str:
        return self.browser.slot.tunnel_url

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
    state: BrowserStateDocument
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now
