from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager


class UnitOfWork[ServiceT](ABC):
    """One short transaction handing out one service.

    Entering builds the service on a fresh transaction; leaving commits it, or
    rolls it back when the block failed, and hands the connection back. Only
    detached values may cross the boundary.

    Callers that must not occupy a database connection while they wait keep
    every read and write inside such a block instead of holding a service that
    was built for the whole HTTP request::

        async with self._sessions() as sessions:
            aggregate = await sessions.get(session_id)
        await self._control.acquire(request)  # no connection held here
    """

    @abstractmethod
    def __call__(self) -> AbstractAsyncContextManager[ServiceT]: ...
