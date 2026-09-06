from collections.abc import AsyncGenerator, AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.infrastructure.database.settings import DatabaseSettings


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> DatabaseSettings:
        return DatabaseSettings()

    @provide(scope=Scope.APP)
    async def engine(self, settings: DatabaseSettings) -> AsyncIterator[AsyncEngine]:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, BaseException | None]:
        # Closing the scope sends the failing exception into this generator
        # rather than throwing it, so the commit decision has to read it from
        # the yield. A plain `try/except` around the yield would never see it
        # and would commit the half-finished work of a failed request.
        async with factory() as session:
            error = yield session
            if error is None:
                await session.commit()
            else:
                await session.rollback()
