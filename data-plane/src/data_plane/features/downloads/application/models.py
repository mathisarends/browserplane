from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Download:
    id: str
    filename: str
    url: str
    size: int
    path: Path
