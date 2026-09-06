from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.features.browser_requests.infrastructure.notifications import PostgresListener
from backend.lifecycle import Lifecycle


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """API infrastructure only; demand and lease maintenance belong to scheduler."""
    container = app.state.dishka_container
    lifecycle = await container.get(Lifecycle)
    listener = await container.get(PostgresListener)
    try:
        async with listener.running():
            lifecycle.mark_ready()
            yield
    finally:
        lifecycle.start_draining()
        await container.close()
