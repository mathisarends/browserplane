from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from data_plane.features.browser.application.service import BrowserService
from data_plane.features.workspace.application.workspace import Workspace
from data_plane.lifecycle import Lifecycle


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    await container.get(BrowserService)
    await container.get(Workspace)
    lifecycle = await container.get(Lifecycle)
    try:
        yield
    finally:
        lifecycle.start_draining()
        await container.close()
