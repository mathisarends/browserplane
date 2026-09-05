from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from data_plane.features.browser_state.presentation.errors import (
    API_ERRORS as BROWSER_STATE_API_ERRORS,
)
from data_plane.features.browser_state.presentation.router import (
    browser_state_router,
)
from data_plane.features.browser_state.provider import BrowserStateProvider
from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.browsers.presentation.errors import (
    API_ERRORS as BROWSER_API_ERRORS,
)
from data_plane.features.browsers.presentation.router import browser_router
from data_plane.features.browsers.provider import BrowserProvider
from data_plane.features.downloads.presentation.errors import (
    API_ERRORS as DOWNLOAD_API_ERRORS,
)
from data_plane.features.downloads.presentation.router import download_router
from data_plane.features.downloads.provider import DownloadProvider
from data_plane.features.health.presentation.router import health_router
from data_plane.features.health.provider import HealthProvider
from data_plane.features.recordings.presentation.errors import (
    API_ERRORS as RECORDING_API_ERRORS,
)
from data_plane.features.recordings.presentation.router import recording_router
from data_plane.features.recordings.provider import RecordingProvider
from data_plane.lifespan import lifespan
from data_plane.presentation.api_errors import register_api_error_handlers
from data_plane.provider import SettingsProvider
from data_plane.request_logging import install_request_logging

API_PREFIX = "/api/v1"
ROUTERS = (
    health_router,
    browser_router,
    browser_state_router,
    download_router,
    recording_router,
)
API_ERRORS = (
    *BROWSER_API_ERRORS,
    *BROWSER_STATE_API_ERRORS,
    *DOWNLOAD_API_ERRORS,
    *RECORDING_API_ERRORS,
)


def create_app(service: BrowserService | None = None) -> FastAPI:
    app = FastAPI(title="Browser Data Plane", version="0.1.0", lifespan=lifespan)
    install_request_logging(app)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        SettingsProvider(),
        BrowserProvider(service),
        DownloadProvider(),
        BrowserStateProvider(),
        RecordingProvider(),
        HealthProvider(),
    )
    setup_dishka(container, app)
    return app


app = create_app()
