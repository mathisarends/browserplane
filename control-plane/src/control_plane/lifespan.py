from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from control_plane.services import BrowserService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    service = await container.get(BrowserService)
    await service.start()
    try:
        yield
    finally:
        await service.stop()
        await container.close()
