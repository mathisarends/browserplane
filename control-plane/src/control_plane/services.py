import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from control_plane.provisioning import BrowserProvisioner
from control_plane.registry import (
    BrowserDescriptor,
    BrowserNotFoundError,
    BrowserRecord,
    BrowserStore,
)
from control_plane.settings import BrowserSlot


@dataclass(frozen=True, slots=True)
class LeaseDescriptor:
    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime


class BrowserService:
    def __init__(
        self, provisioner: BrowserProvisioner, registry: BrowserStore
    ) -> None:
        self._provisioner = provisioner
        self._registry = registry
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        now = _now()
        for slot in await self._provisioner.provision():
            self._registry.add(BrowserRecord(slot=slot, created_at=now))

    async def stop(self) -> None:
        self._registry.clear()
        await self._provisioner.deprovision()

    async def create(self) -> BrowserDescriptor:
        raise BrowserUnavailableError("No unassigned browser slots")

    def list(self) -> list[BrowserDescriptor]:
        return [self._describe(browser) for browser in self._registry.list()]

    def get(self, browser_id: UUID) -> BrowserDescriptor:
        return self._describe(self._registry.get(browser_id))

    def slot(self, browser_id: UUID) -> BrowserSlot:
        browser = self._registry.get(browser_id)
        if browser.state == "failed":
            raise BrowserNotFoundError(browser_id)
        return browser.slot

    async def destroy(self, browser_id: UUID) -> None:
        async with self._lock:
            browser = self._registry.get(browser_id)
            browser.state = "stopping"
            browser.state = "failed"

    async def reset(self, browser_id: UUID) -> BrowserDescriptor:
        async with self._lock:
            browser = self._registry.get(browser_id)
            browser.state = "starting"
            browser.state = "ready"
            return self._describe(browser)

    def _describe(self, browser: BrowserRecord) -> BrowserDescriptor:
        return BrowserDescriptor(
            id=browser.slot.id,
            state=browser.state,
            cdp_url=f"/api/v1/browsers/{browser.slot.id}/cdp",
            created_at=browser.created_at,
        )


class LeaseService:
    def __init__(self, registry: BrowserStore) -> None:
        self._registry = registry
        self._leases: dict[UUID, LeaseDescriptor] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, browser_id: UUID, owner_id: UUID, ttl: timedelta
    ) -> LeaseDescriptor:
        async with self._lock:
            self._expire()
            browser = self._registry.get(browser_id)
            if browser.state != "ready":
                raise BrowserUnavailableError(browser_id)
            now = _now()
            lease = LeaseDescriptor(uuid4(), browser_id, owner_id, now + ttl, now)
            self._leases[lease.id] = lease
            browser.state = "leased"
            return lease

    def get(self, lease_id: UUID) -> LeaseDescriptor:
        self._expire()
        try:
            return self._leases[lease_id]
        except KeyError as error:
            raise LeaseNotFoundError(lease_id) from error

    async def release(self, lease_id: UUID) -> None:
        async with self._lock:
            lease = self.get(lease_id)
            self._leases.pop(lease.id)
            browser = self._registry.get(lease.browser_id)
            if browser.state == "leased":
                browser.state = "ready"

    def _expire(self) -> None:
        now = _now()
        for lease_id, lease in list(self._leases.items()):
            if lease.expires_at <= now:
                self._leases.pop(lease_id)
                browser = self._registry.get(lease.browser_id)
                if browser.state == "leased":
                    browser.state = "ready"


def _now() -> datetime:
    return datetime.now(UTC)


class LeaseNotFoundError(LookupError):
    pass


class BrowserUnavailableError(RuntimeError):
    pass
