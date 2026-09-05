from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BrowserSummary:
    """What the backend needs to know about a browser to pick one."""

    id: UUID
    is_available: bool


@dataclass(frozen=True, slots=True)
class BrowserEndpoints:
    """Internal live-connection URLs, never handed to the frontend."""

    browser_id: UUID
    tunnel_url: str
    screencast_url: str


@dataclass(frozen=True, slots=True)
class Lease:
    """A claim on a browser, as granted by the control plane."""

    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Session:
    """One frontend workspace: a lease plus the browser it can talk to."""

    lease: Lease
    endpoints: BrowserEndpoints

    @property
    def id(self) -> UUID:
        return self.lease.id

    @property
    def browser_id(self) -> UUID:
        return self.lease.browser_id
