import asyncio

from dishka import Provider, Scope, provide
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.features.health.application.service import HealthService

PERSISTENCE_TIMEOUT_SECONDS = 2.0


class HealthProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def health_service(self, engine: AsyncEngine) -> HealthService:
        async def check_persistence() -> None:
            # Own connection, so a probe never waits behind request traffic, and
            # a timeout, so a hung database fails the probe instead of the poll.
            async with asyncio.timeout(PERSISTENCE_TIMEOUT_SECONDS):
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))

        return HealthService(check_persistence)
