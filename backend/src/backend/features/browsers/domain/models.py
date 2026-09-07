from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5


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
    id: UUID
    browser_worker_url: str


@dataclass(frozen=True, slots=True)
class BrowserWorker:
    id: UUID
    url: str
    capacity: int = 1
    labels: Mapping[str, str] = field(default_factory=dict)

    def slots(self) -> tuple[BrowserSlot, ...]:
        """One slot per browser this worker can hold.

        The worker id is the namespace, so a slot keeps its id across restarts
        and stays distinct from every other worker's slot at the same index.
        """
        return tuple(
            BrowserSlot(uuid5(self.id, str(index)), self.url)
            for index in range(self.capacity)
        )


def slots_of(workers: Iterable[BrowserWorker]) -> tuple[BrowserSlot, ...]:
    return tuple(slot for worker in workers for slot in worker.slots())


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
