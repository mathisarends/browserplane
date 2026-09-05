from collections.abc import AsyncIterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BucketObject:
    """An object whose body can be relayed without loading it all into memory."""

    key: str
    content: AsyncIterable[bytes]
    content_type: str | None = None
