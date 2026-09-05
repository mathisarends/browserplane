from collections.abc import Sequence

from backend.features.browsers.application.models import BrowserSlot
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.infrastructure.browser_worker import BrowserWorkerClient
from generated.browser_worker import CreateBrowserRequest, GeneratedBrowserWorkerClient


class BrowserWorkerProvisioner(BrowserProvisioner):
    """Create one browser on each configured browser worker."""

    def __init__(
        self,
        settings: BrowserPoolSettings,
        client: BrowserWorkerClient,
    ) -> None:
        self._settings = settings
        self._client = client
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
        await self._client.request(
            slot.browser_worker_url,
            lambda client: client.create_browser(CreateBrowserRequest(id=slot.id)),
        )

    async def stop(self, slot: BrowserSlot) -> None:
        await self._client.request(
            slot.browser_worker_url,
            GeneratedBrowserWorkerClient.destroy_browser,
        )
