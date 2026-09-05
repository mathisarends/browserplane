from abc import ABC, abstractmethod
from collections.abc import Sequence

from data_plane.features.browser_state.application.models import (
    AuthenticationState,
    BrowserState,
)


class BrowserStateStore(ABC):
    """Reads and writes the restorable state of one browser."""

    @abstractmethod
    async def capture_authentication(
        self, extra_origins: Sequence[str] = ()
    ) -> AuthenticationState:
        """Read the browser's cookies and localStorage.

        ``extra_origins`` are read in addition to the origins of the open
        tabs, for logins that no tab currently shows.
        """

    @abstractmethod
    async def restore_authentication(self, state: AuthenticationState) -> None:
        """Replace the browser's cookies and localStorage with ``state``."""

    @abstractmethod
    async def capture_browser(self) -> BrowserState:
        """Read the browser's tabs and their presentation state."""

    @abstractmethod
    async def restore_browser(self, state: BrowserState) -> None:
        """Replace the browser's tabs with ``state``."""
