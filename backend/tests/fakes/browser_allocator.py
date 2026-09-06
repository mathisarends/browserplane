from uuid import UUID

from backend.features.leases.application.ports import BrowserAllocator


class FakeBrowserAllocator(BrowserAllocator):
    """Allocator fake that exposes the claims and cleanup it receives."""

    def __init__(self, generation: int = 0) -> None:
        self.generation = generation
        self.reserved: list[UUID] = []
        self.recycled: list[UUID] = []
        self.recycle_error: Exception | None = None

    async def reserve(self, browser_id: UUID) -> int:
        self.reserved.append(browser_id)
        return self.generation

    async def recycle(self, browser_id: UUID) -> None:
        self.recycled.append(browser_id)
        if self.recycle_error is not None:
            raise self.recycle_error
