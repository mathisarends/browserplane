from collections.abc import Sequence

from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.domain.models import BrowserSlot


class FakeBrowserProvisioner(BrowserProvisioner):
    """Observable worker lifecycle with configurable failures."""

    def __init__(self, slots: Sequence[BrowserSlot] = ()) -> None:
        self.slots = tuple(slots)
        self.started: list[tuple[BrowserSlot, int]] = []
        self.released: list[tuple[BrowserSlot, int]] = []
        self.release_error: Exception | None = None

    async def provision(self) -> Sequence[BrowserSlot]:
        return self.slots

    async def deprovision(self) -> None:
        return None

    async def start(self, slot: BrowserSlot, generation: int = 0) -> None:
        self.started.append((slot, generation))

    async def release(self, slot: BrowserSlot, generation: int) -> None:
        self.released.append((slot, generation))
        if self.release_error is not None:
            raise self.release_error
