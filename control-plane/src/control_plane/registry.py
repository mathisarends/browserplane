from dataclasses import dataclass

from control_plane.provisioning import BrowserProvisioner
from control_plane.settings import BrowserSlot


@dataclass(frozen=True, slots=True)
class BrowserDescriptor:
    id: str
    status: str
    websocket_url: str


class BrowserRegistry:
    def __init__(self, provisioner: BrowserProvisioner) -> None:
        self._provisioner = provisioner
        self._slots: dict[str, BrowserSlot] = {}

    async def start(self) -> None:
        slots = await self._provisioner.provision()
        self._slots = {slot.id: slot for slot in slots}

    async def stop(self) -> None:
        self._slots.clear()
        await self._provisioner.deprovision()

    def list(self) -> list[BrowserDescriptor]:
        return [
            BrowserDescriptor(
                id=slot.id,
                status="ready",
                websocket_url=f"/api/browsers/{slot.id}/ws",
            )
            for slot in self._slots.values()
        ]

    def get(self, browser_id: str) -> BrowserSlot:
        try:
            return self._slots[browser_id]
        except KeyError as error:
            raise BrowserNotFoundError(browser_id) from error


class BrowserNotFoundError(LookupError):
    pass
