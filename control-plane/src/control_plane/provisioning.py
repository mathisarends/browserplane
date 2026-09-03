from collections.abc import Sequence
from typing import Protocol

import httpx2

from control_plane.settings import BrowserSlot, ControlPlaneSettings


class BrowserProvisioner(Protocol):
    async def provision(self) -> Sequence[BrowserSlot]: ...

    async def deprovision(self) -> None: ...


class DataPlaneBrowserProvisioner:
    """Create one browser on each configured data-plane worker."""

    def __init__(self, settings: ControlPlaneSettings) -> None:
        self._settings = settings
        self._provisioned: list[BrowserSlot] = []

    async def provision(self) -> Sequence[BrowserSlot]:
        slots = self._settings.slots()
        async with httpx2.AsyncClient() as client:
            for slot in slots:
                response = await client.post(
                    f"{slot.data_plane_url}/api/v1/browsers",
                    json={"id": slot.id},
                )
                response.raise_for_status()
                self._provisioned.append(slot)
        return slots

    async def deprovision(self) -> None:
        async with httpx2.AsyncClient() as client:
            for slot in reversed(self._provisioned):
                response = await client.delete(
                    f"{slot.data_plane_url}/api/v1/browsers/{slot.id}"
                )
                response.raise_for_status()
        self._provisioned.clear()
