from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Browser:
    """The single Chromium instance owned by this worker."""

    id: UUID
    cdp_url: str
