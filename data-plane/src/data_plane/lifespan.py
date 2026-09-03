from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from data_plane.application.service import BrowserService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    await container.get(BrowserService)
    try:
        yield
    finally:
        await container.close()
