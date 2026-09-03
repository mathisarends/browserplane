from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from control_plane.features.browsers.application.service import BrowserService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    browsers = await container.get(BrowserService)
    await browsers.start()
    try:
        yield
    finally:
        await browsers.stop()
        await container.close()
