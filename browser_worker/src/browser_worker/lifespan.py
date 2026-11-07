from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from browser_worker.features.browser.application import BrowserService
from browser_worker.features.workspace.application import Workspace


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    await container.get(BrowserService)
    await container.get(Workspace)
    yield
