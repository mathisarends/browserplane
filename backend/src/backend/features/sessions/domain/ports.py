from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.browsers.domain.models import Browser
from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    AuthenticationStateDocument,
    BrowserCheckpoint,
    BrowserStateDocument,
    Download,
    Session,
)


class SessionRepository(ABC):
    """Persistence contract for session aggregate roots."""

    @abstractmethod
    async def save(self, session: Session) -> Session: ...

    @abstractmethod
    async def get_by_id(self, *, session_id: UUID) -> Session | None: ...

    @abstractmethod
    async def list(self) -> tuple[Session, ...]: ...


class BrowserRuntime(ABC):
    """Access state and downloads belonging to a running browser."""

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

    @abstractmethod
    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]: ...

    @abstractmethod
    async def clear_downloads(self, browser: Browser) -> None: ...

    @abstractmethod
    async def download_file(self, browser: Browser, download_id: str) -> bytes: ...


class BrowserCheckpointRepository(ABC):
    """Persistence contract for named browser checkpoints."""

    @abstractmethod
    async def save(self, checkpoint: BrowserCheckpoint) -> BrowserCheckpoint: ...

    @abstractmethod
    async def get_by_id(self, *, checkpoint_id: UUID) -> BrowserCheckpoint | None: ...

    @abstractmethod
    async def list(self) -> tuple[BrowserCheckpoint, ...]: ...

    @abstractmethod
    async def delete(self, checkpoint_id: UUID) -> bool: ...


class AuthenticationProfileRepository(ABC):
    """Persistence contract for reusable, mutable login identities."""

    @abstractmethod
    async def save(self, profile: AuthenticationProfile) -> AuthenticationProfile: ...

    @abstractmethod
    async def get_by_id(self, *, profile_id: UUID) -> AuthenticationProfile | None: ...

    @abstractmethod
    async def list(self) -> tuple[AuthenticationProfile, ...]: ...

    @abstractmethod
    async def delete(self, profile_id: UUID) -> bool: ...
