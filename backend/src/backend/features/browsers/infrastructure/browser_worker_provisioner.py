from collections.abc import Sequence
from typing import Any, cast

from httpx2 import AsyncClient

from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.domain.models import BrowserSlot
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from generated.browser_worker import CreateBrowserRequest, GeneratedBrowserWorkerClient


class BrowserWorkerProvisioner(BrowserProvisioner):
    """Create one browser on each configured browser worker."""

    def __init__(
        self,
        settings: BrowserPoolSettings,
        http: AsyncClient,
        worker_settings: BrowserWorkerSettings,
    ) -> None:
        self._settings = settings
        self._http = http
        self._worker_settings = worker_settings
        self._provisioned: list[BrowserSlot] = []

    async def provision(self) -> Sequence[BrowserSlot]:
        slots = self._settings.slots()
        for slot in slots:
            await self.start(slot)
            self._provisioned.append(slot)
        return slots

    async def deprovision(self) -> None:
        for slot in reversed(self._provisioned):
            await self.release(slot)
        self._provisioned.clear()

    async def start(self, slot: BrowserSlot) -> None:
        client = self._client(slot)
        await client.create_browser(CreateBrowserRequest(id=slot.id))

    async def release(self, slot: BrowserSlot) -> None:
        client = self._client(slot)
        await client.release_worker()

    def _client(self, slot: BrowserSlot) -> GeneratedBrowserWorkerClient:
        return GeneratedBrowserWorkerClient(
            cast(Any, self._http),
            slot.browser_worker_url,
            timeout=self._worker_settings.request_timeout_seconds,
        )
