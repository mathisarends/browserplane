from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Browser:
    id: UUID
    cdp_url: str
