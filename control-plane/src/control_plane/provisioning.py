from collections.abc import Sequence
from typing import Protocol

from control_plane.settings import BrowserSlot, ControlPlaneSettings


class BrowserProvisioner(Protocol):
    async def provision(self) -> Sequence[BrowserSlot]: ...

    async def deprovision(self) -> None: ...


class ComposeBrowserProvisioner:
    """Expose the two browser tunnels eagerly created by Compose."""

    def __init__(self, settings: ControlPlaneSettings) -> None:
        self._settings = settings

    async def provision(self) -> Sequence[BrowserSlot]:
        return self._settings.slots()

    async def deprovision(self) -> None:
        # Compose owns the container lifecycle in this first implementation.
        return None
