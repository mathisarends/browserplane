from collections.abc import Sequence

from httpx2 import AsyncClient

from backend.features.browsers.application.models import BrowserSlot
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from generated.browser_worker import CreateBrowserRequest, GeneratedBrowserWorkerClient


class BrowserWorkerProvisioner(BrowserProvisioner):
    """Create one browser on each configured browser worker."""

    def __init__(self, settings: BrowserPoolSettings) -> None:
        self._settings = settings
        self._provisioned: list[BrowserSlot] = []

    async def provision(self) -> Sequence[BrowserSlot]:
        slots = self._settings.slots()
        for slot in slots:
            await self.start(slot)
            self._provisioned.append(slot)
        return slots

    async def deprovision(self) -> None:
        for slot in reversed(self._provisioned):
            await self.stop(slot)
        self._provisioned.clear()

    async def start(self, slot: BrowserSlot) -> None:
        async with self._client(slot) as client:
            await client.create_browser(CreateBrowserRequest(id=slot.id))

    async def stop(self, slot: BrowserSlot) -> None:
        async with self._client(slot) as client:
            await client.destroy_browser()

    def _client(self, slot: BrowserSlot) -> GeneratedBrowserWorkerClient:
        # The generated client closes the transport it was handed, so one client
        # per call keeps a single worker's failure from leaking a shared pool.
        return GeneratedBrowserWorkerClient(AsyncClient(), slot.browser_worker_url)
