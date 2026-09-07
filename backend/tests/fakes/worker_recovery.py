from uuid import uuid4

from backend.features.browsers.application.ports import WorkerRecovery
from backend.features.browsers.domain.models import BrowserSlot, WorkerIncarnation


class FakeWorkerRecovery(WorkerRecovery):
    """Observable worker replacement with a configurable failure."""

    def __init__(self) -> None:
        self.replaced: list[BrowserSlot] = []
        self.replace_error: Exception | None = None

    async def replace(self, slot: BrowserSlot) -> WorkerIncarnation:
        self.replaced.append(slot)
        if self.replace_error is not None:
            raise self.replace_error
        return WorkerIncarnation(uuid4())
