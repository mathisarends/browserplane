from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from backend.features.browsers.application.exceptions import BrowserNotFoundException
from backend.features.browsers.domain.models import Browser
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.domain.models import Lease
from backend.features.sessions.application.ports import BrowserRuntime
from backend.features.sessions.domain.models import (
    AuthenticationStateDocument,
    BrowserStateDocument,
    Download,
)


class FakeSessionBrowsers:
    """A browser lookup service with an explicit remaining pool size."""

    def __init__(self, *browsers: Browser, remaining_capacity: int = 0) -> None:
        self._browsers = {browser.id: browser for browser in browsers}
        self._remaining_capacity = remaining_capacity

    async def get(self, browser_id: UUID) -> Browser:
        try:
            return self._browsers[browser_id]
        except KeyError as error:
            raise BrowserNotFoundException() from error

    async def remaining_capacity(self) -> int:
        return self._remaining_capacity


class FakeSessionLeases:
    """Lease service fake that records lifecycle operations by session id."""

    def __init__(self, *leases: Lease) -> None:
        self._leases = {lease.id: lease for lease in leases}
        self.released: list[tuple[UUID, str]] = []
        self.reaped: tuple[UUID, ...] = ()

    async def inspect(self, lease_id: UUID) -> Lease:
        return self._lease(lease_id)

    async def get(self, lease_id: UUID) -> Lease:
        lease = self._lease(lease_id)
        if lease.is_expired(datetime.now(UTC)):
            raise LeaseNotFoundException()
        return lease

    async def renew(self, lease_id: UUID) -> Lease:
        lease = self._lease(lease_id)
        renewed = replace(
            lease,
            last_renewed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        self._leases[lease_id] = renewed
        return renewed

    async def release(self, lease_id: UUID, *, reason: str) -> None:
        self._lease(lease_id)
        self.released.append((lease_id, reason))

    async def reap_due(self) -> tuple[UUID, ...]:
        return self.reaped

    def _lease(self, lease_id: UUID) -> Lease:
        try:
            return self._leases[lease_id]
        except KeyError as error:
            raise LeaseNotFoundException() from error


class FakeBrowserRuntime(BrowserRuntime):
    """Worker-state fake that stores input and exposes deterministic captures."""

    def __init__(
        self,
        *,
        authentication: AuthenticationStateDocument | None = None,
        browser_state: BrowserStateDocument | None = None,
        downloads: tuple[Download, ...] = (),
        files: dict[str, bytes] | None = None,
    ) -> None:
        self.authentication = authentication or {"cookies": []}
        self.browser_state = browser_state or {"tabs": []}
        self.downloads = downloads
        self.files = files or {}
        self.mounted_authentication: list[AuthenticationStateDocument] = []
        self.mounted_browser: list[BrowserStateDocument] = []

    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument:
        return self.authentication

    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None:
        self.mounted_authentication.append(state)

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        return self.browser_state

    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None:
        self.mounted_browser.append(state)

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        return self.downloads

    async def clear_downloads(self, browser: Browser) -> None:
        self.downloads = ()

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        return self.files[download_id]
