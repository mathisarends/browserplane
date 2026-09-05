from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID


class BrowserState(StrEnum):
    STARTING = "starting"
    READY = "ready"
    LEASED = "leased"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BrowserSlot:
    """A fixed browser id on one internal data-plane worker."""

    id: UUID
    data_plane_url: str

    @property
    def cdp_url(self) -> str:
        return self._websocket_url("cdp")

    @property
    def screencast_url(self) -> str:
        return self._websocket_url("screencast")

    @property
    def fmp4_screencast_url(self) -> str:
        return f"{self.screencast_url}/fmp4"

    def _websocket_url(self, stream: str) -> str:
        parsed = urlsplit(self.data_plane_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        base_path = parsed.path.rstrip("/")
        return urlunsplit(
            (
                scheme,
                parsed.netloc,
                f"{base_path}/api/v1/browser/{self.id}/{stream}",
                "",
                "",
            )
        )


@dataclass(slots=True)
class Browser:
    slot: BrowserSlot
    created_at: datetime
    state: BrowserState = field(default=BrowserState.READY)

    @property
    def id(self) -> UUID:
        return self.slot.id

    @property
    def is_available(self) -> bool:
        return self.state is BrowserState.READY
