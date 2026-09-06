from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class BrowserState(StrEnum):
    STARTING = "starting"
    READY = "ready"
    LEASED = "leased"
    RECYCLING = "recycling"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BrowserSlot:
    """A fixed browser id on one internal browser worker."""

    id: UUID
    browser_worker_url: str


@dataclass(slots=True)
class Browser:
    slot: BrowserSlot
    created_at: datetime
    state: BrowserState = field(default=BrowserState.READY)
    generation: int = 0

    @property
    def id(self) -> UUID:
        return self.slot.id

    @property
    def is_available(self) -> bool:
        return self.state in (BrowserState.READY, BrowserState.STOPPED)
