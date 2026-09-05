from abc import ABC, abstractmethod
from collections.abc import Sequence

from data_plane.features.browser_state.application.models import BrowserState


class BrowserStateStore(ABC):
    """Reads and writes the restorable state of one browser."""

    @abstractmethod
    async def capture(self, extra_origins: Sequence[str] = ()) -> BrowserState:
        """Read the browser's tabs and authentication state.

        ``extra_origins`` are read in addition to the origins of the open
        tabs, for logins that no tab currently shows.
        """

    @abstractmethod
    async def restore(self, state: BrowserState) -> None:
        """Replace the browser's state with ``state``."""
