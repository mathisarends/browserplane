from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from data_plane.features.browser.application.service import BrowserService
from data_plane.workspace import Workspace


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    await container.get(BrowserService)
    await container.get(Workspace)
    try:
        yield
    finally:
        await container.close()
