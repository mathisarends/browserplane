import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.features.session_requests.application.ports import Notification, Notifier
from backend.features.session_requests.application.wakeups import Wakeups
from backend.infrastructure.database.settings import DatabaseSettings

logger = logging.getLogger(__name__)
CHANNEL = "browser_capacity_changed"


def connection_options(settings: DatabaseSettings) -> dict:
    url = make_url(settings.database_url)
    return dict(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.database,
        **dict(url.query),
    )


async def notify_transaction(session: AsyncSession) -> None:
    # PostgreSQL delivers this only if the surrounding transaction commits.
    await session.execute(text("SELECT pg_notify(:channel, '')"), {"channel": CHANNEL})


class PostgresNotifier(Notifier):
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self._factory = factory

    async def notify(self, notification: Notification) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": notification.channel, "payload": notification.payload},
            )


class PostgresListener:
    def __init__(self, settings: DatabaseSettings, wakeups: Wakeups):
        self._settings = settings
        self._wakeups = wakeups

    @asynccontextmanager
    async def running(self):
        task = asyncio.create_task(self.run(), name="session-request-listener")
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def run(self):
        while True:
            connection = None
            try:
                connection = await asyncpg.connect(
                    **connection_options(self._settings), timeout=5
                )
                await connection.add_listener(CHANNEL, lambda *_: self._wakeups.wake())
                self._wakeups.wake()
                while True:
                    await asyncio.sleep(5)
                    await connection.execute("SELECT 1", timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "Session request listener disconnected; reconnecting", exc_info=True
                )
                self._wakeups.wake()
                await asyncio.sleep(2)
            finally:
                if connection is not None:
                    with suppress(Exception):
                        await connection.close(timeout=2)
