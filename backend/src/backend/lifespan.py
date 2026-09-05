from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka import Scope
from fastapi import FastAPI

from backend.features.browsers.application.service import BrowserService
from backend.lifecycle import Lifecycle


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
    lifecycle.mark_ready()
    try:
        yield
    finally:
        lifecycle.start_draining()
        async with container(scope=Scope.REQUEST) as scoped:
            browsers = await scoped.get(BrowserService)
            await browsers.stop()
        await container.close()
