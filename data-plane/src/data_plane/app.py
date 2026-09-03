from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from data_plane.lifespan import lifespan
from data_plane.manager import BrowserManager
from data_plane.provider import DataPlaneProvider
from data_plane.router import router


def create_app(manager: BrowserManager | None = None) -> FastAPI:
    app = FastAPI(title="Browser Data Plane", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    setup_dishka(make_async_container(DataPlaneProvider(manager)), app)
    return app


app = create_app()
