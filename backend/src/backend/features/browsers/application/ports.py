from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from backend.features.browsers.domain.models import Browser, BrowserSlot, BrowserWorker


class BrowserWorkerDirectory(ABC):
    """Where the pool learns which workers exist."""

    @abstractmethod
    async def snapshot(self) -> Sequence[BrowserWorker]:
        """The workers known right now; a complete set, not a delta."""


class BrowserProvisioner(ABC):
    """Owns the browser lifecycle on the browser worker."""

    @abstractmethod
    async def provision(self) -> Sequence[BrowserSlot]: ...

    @abstractmethod
    async def deprovision(self) -> None: ...

    @abstractmethod
    async def start(self, slot: BrowserSlot, generation: int = 0) -> None:
        """Bring one slot's browser process up, on its own worker."""

    @abstractmethod
    async def release(self, slot: BrowserSlot, generation: int) -> None:
        """Reset one worker to its empty initial state; the slot itself stays."""


class BrowserRepository(ABC):
    """Persistence contract for the browser pool."""

    @abstractmethod
    async def save(self, browser: Browser) -> Browser:
        """
        Write a slot, overwriting whatever an earlier boot left behind.

        Provisioning hands out the same slot ids on every start, so seeding the
        pool is an upsert: the fresh row also resets the state, which is what we
        want, because the leases that referenced it are gone.
        """

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
