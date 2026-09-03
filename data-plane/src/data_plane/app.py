from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.browsers.presentation.errors import API_ERRORS
from data_plane.features.browsers.presentation.router import browser_router
from data_plane.features.browsers.provider import BrowserProvider
from data_plane.features.health.presentation.router import health_router
from data_plane.features.health.provider import HealthProvider
from data_plane.lifespan import lifespan
from data_plane.presentation.api_errors import register_api_error_handlers
from data_plane.provider import SettingsProvider

API_PREFIX = "/api/v1"
ROUTERS = (health_router, browser_router)


def create_app(service: BrowserService | None = None) -> FastAPI:
    app = FastAPI(title="Browser Data Plane", version="0.1.0", lifespan=lifespan)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        SettingsProvider(),
        BrowserProvider(service),
        HealthProvider(),
    )
    setup_dishka(container, app)
    return app


app = create_app()
