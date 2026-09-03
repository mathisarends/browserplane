from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Browser:
    """A Chromium instance owned by this worker."""

    id: UUID
    cdp_url: str


@dataclass(frozen=True, slots=True)
class Capacity:
    total: int
    available: int
