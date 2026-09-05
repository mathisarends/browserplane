from dataclasses import dataclass
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.leases.application.models import Lease


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
