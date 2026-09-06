from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.workspace.application.workspace import Workspace


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    await container.get(BrowserService)
    await container.get(Workspace)
    try:
        yield
    finally:
        await container.close()
