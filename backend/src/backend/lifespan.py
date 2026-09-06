import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka import Scope
from fastapi import FastAPI

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.settings import LeaseSettings
from backend.features.sessions.application.service import SessionService
from backend.lifecycle import Lifecycle

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Seed and tear down the browser pool around the app's lifetime.

    Startup and shutdown outlive any request, so each opens its own short-lived
    scope rather than borrowing a request's session.
    """
    container = app.state.dishka_container
    lifecycle = await container.get(Lifecycle)
    async with container(scope=Scope.REQUEST) as scoped:
        browsers = await scoped.get(BrowserService)
        await browsers.start()
        sessions = await scoped.get(SessionService)
        await sessions.reap_expired()
    lifecycle.mark_ready()
    lease_settings = await container.get(LeaseSettings)
    reaper = asyncio.create_task(
        _reap_expired_leases(container, lease_settings.reaper_interval_seconds)
    )
    try:
        yield
    finally:
        lifecycle.start_draining()
        reaper.cancel()
        await asyncio.gather(reaper, return_exceptions=True)
        async with container(scope=Scope.REQUEST) as scoped:
            browsers = await scoped.get(BrowserService)
            await browsers.stop()
        await container.close()


async def _reap_expired_leases(container, interval_seconds: int) -> None:
    while True:
        try:
            async with container(scope=Scope.REQUEST) as scoped:
                sessions = await scoped.get(SessionService)
                released = await sessions.reap_expired()
                if released:
                    logger.info("Reaped expired browser leases count=%d", len(released))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Lease reaper iteration failed")
        await asyncio.sleep(interval_seconds)
