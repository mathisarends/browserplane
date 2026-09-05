from collections.abc import Sequence

from httpx2 import AsyncClient

from control_plane.features.browsers.application.models import BrowserSlot
from control_plane.features.browsers.application.ports import BrowserProvisioner
from control_plane.settings import ControlPlaneSettings
from generated.data_plane import CreateBrowserRequest, GeneratedDataPlaneClient


class DataPlaneBrowserProvisioner(BrowserProvisioner):
    """Create one browser on each configured data-plane worker."""

    def __init__(self, settings: ControlPlaneSettings) -> None:
        self._settings = settings
        self._provisioned: list[BrowserSlot] = []

    async def provision(self) -> Sequence[BrowserSlot]:
        slots = self._settings.slots()
        async with AsyncClient() as http:
            for slot in slots:
                client = GeneratedDataPlaneClient(http, slot.data_plane_url)
                await client.create_browser(CreateBrowserRequest(id=slot.id))
                self._provisioned.append(slot)
        return slots

    async def deprovision(self) -> None:
        async with AsyncClient() as http:
            for slot in reversed(self._provisioned):
                client = GeneratedDataPlaneClient(http, slot.data_plane_url)
                await client.destroy_browser()
        self._provisioned.clear()
