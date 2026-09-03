from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class BrowserState(StrEnum):
    STARTING = "starting"
    READY = "ready"
    LEASED = "leased"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BrowserSlot:
    """Worker address plus the client-facing tunnel endpoint for a browser."""

    id: UUID
    data_plane_url: str
    tunnel_url: str


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
