from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BucketObject:
    key: str
    path: Path
    content_type: str | None = None
