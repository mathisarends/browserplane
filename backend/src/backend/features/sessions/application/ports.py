from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.sessions.application.models import (
    AuthenticationStateDocument,
    AuthenticationStateSnapshot,
    BrowserStateDocument,
    BrowserStateSnapshot,
    SuspendedSession,
)


class SuspendedSessionRepository(ABC):
    """Persistence contract for sessions that currently hold no browser."""

    @abstractmethod
    async def save(self, *, suspended: SuspendedSession) -> SuspendedSession: ...

    @abstractmethod
    async def get_by_id(self, *, session_id: UUID) -> SuspendedSession | None: ...

    @abstractmethod
    async def list_all(self) -> tuple[SuspendedSession, ...]:
        """Everything parked right now, newest first."""

    @abstractmethod
    async def delete(self, *, session_id: UUID) -> None: ...


class BrowserStateGateway(ABC):
    """Reads and writes a browser's state through its worker."""

    @abstractmethod
    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument: ...

    @abstractmethod
    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None: ...

    @abstractmethod
    async def capture_browser(self, browser: Browser) -> BrowserStateDocument: ...

    @abstractmethod
    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None: ...


class BrowserStateSnapshotRepository(ABC):
    """Persistence contract for reusable, named browser states."""

    @abstractmethod
    async def save(self, *, snapshot: BrowserStateSnapshot) -> BrowserStateSnapshot: ...

    @abstractmethod
    async def list_all(self) -> tuple[BrowserStateSnapshot, ...]: ...


class AuthenticationStateSnapshotRepository(ABC):
    """Persistence contract for reusable, named authentication states."""

    @abstractmethod
    async def save(
        self, *, snapshot: AuthenticationStateSnapshot
    ) -> AuthenticationStateSnapshot: ...

    @abstractmethod
    async def list_all(self) -> tuple[AuthenticationStateSnapshot, ...]: ...
