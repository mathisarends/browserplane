from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.features.session_requests.infrastructure.notifications import (
    PostgresListener,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """API infrastructure only; demand and lease maintenance belong to scheduler."""
    container = app.state.dishka_container
    listener = await container.get(PostgresListener)
    async with listener.running():
        yield
