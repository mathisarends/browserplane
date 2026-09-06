import asyncio
from collections import defaultdict
from contextlib import contextmanager
from uuid import UUID


class Wakeups:
    """Local hints only; registration always precedes the authoritative read."""

    def __init__(self):
        self._waiters: dict[UUID, set[asyncio.Future]] = defaultdict(set)
        self.dispatch = asyncio.Event()

    @contextmanager
    def register(self, request_id: UUID):
        future = asyncio.get_running_loop().create_future()
        self._waiters[request_id].add(future)
        try:
            yield future
        finally:
            self._waiters[request_id].discard(future)
            if not self._waiters[request_id]:
                del self._waiters[request_id]
            future.cancel()

    def wake(self):
        self.dispatch.set()
        for futures in self._waiters.values():
            for future in futures:
                if not future.done():
                    future.set_result(None)
