from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from backend.features.browsers.application.models import Browser, BrowserSlot


class BrowserProvisioner(ABC):
    """Owns the browser lifecycle on the browser worker."""

    @abstractmethod
    async def provision(self) -> Sequence[BrowserSlot]: ...

    @abstractmethod
    async def deprovision(self) -> None: ...

    @abstractmethod
    async def start(self, slot: BrowserSlot) -> None:
        """Bring one slot's browser process up, on its own worker."""

    @abstractmethod
    async def release(self, slot: BrowserSlot) -> None:
        """Reset one worker to its empty initial state; the slot itself stays."""


class BrowserRepository(ABC):
    """Persistence contract for the browser pool."""

    @abstractmethod
    async def save(self, *, browser: Browser) -> Browser: ...

    @abstractmethod
    async def get_by_id(self, *, browser_id: UUID) -> Browser | None: ...

    @abstractmethod
    async def list(self) -> tuple[Browser, ...]:
        """The whole pool, oldest slot first, whatever state it is in."""

    @abstractmethod
    async def find_available(self) -> Browser | None:
        """
        Claim the next free browser for the caller's transaction.

        Handing one out is a read-modify-write across the whole pool, so the
        row is locked until the caller either leases it or gives up.
        """

    @abstractmethod
    async def delete_all(self) -> None: ...
