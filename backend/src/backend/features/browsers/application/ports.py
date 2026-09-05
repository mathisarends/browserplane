from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from backend.features.browsers.application.models import Browser, BrowserSlot


class BrowserProvisioner(ABC):
    """Owns the browser lifecycle on the data plane."""

    @abstractmethod
    async def provision(self) -> Sequence[BrowserSlot]: ...

    @abstractmethod
    async def deprovision(self) -> None: ...


class BrowserRegistry(ABC):
    """Storage port for provisioned browsers."""

    @abstractmethod
    def add(self, browser: Browser) -> None: ...

    @abstractmethod
    def list(self) -> list[Browser]: ...

    @abstractmethod
    def get(self, browser_id: UUID) -> Browser | None: ...

    @abstractmethod
    def clear(self) -> None: ...
