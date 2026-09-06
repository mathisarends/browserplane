from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import AsyncContainer, Scope

from backend.shared.unit_of_work import UnitOfWork


class ScopedUnitOfWork[ServiceT](UnitOfWork[ServiceT]):
    """A unit of work backed by a nested dependency scope.

    The scope owns the ``AsyncSession`` its service was built on, so leaving the
    block runs that session's commit or rollback and returns its connection to
    the pool. Nothing is reused across blocks: every entry resolves a new
    service on a new session.
    """

    def __init__(self, container: AsyncContainer, service: type[ServiceT]) -> None:
        self._container = container
        self._service = service

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[ServiceT]:
        async with self._container(scope=Scope.REQUEST) as scoped:
            yield await scoped.get(self._service)
