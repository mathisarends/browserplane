from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.browser.infrastructure import BrowserProvider
from browser_worker.features.browser.presentation.errors import (
    API_ERRORS as BROWSER_API_ERRORS,
)
from browser_worker.features.browser.presentation.router import browser_router
from browser_worker.features.browser.state.infrastructure import BrowserStateProvider
from browser_worker.features.browser.state.presentation.errors import (
    API_ERRORS as BROWSER_STATE_API_ERRORS,
)
from browser_worker.features.browser.state.presentation.router import (
    browser_state_router,
)
from browser_worker.features.downloads.infrastructure import DownloadProvider
from browser_worker.features.downloads.presentation.errors import (
    API_ERRORS as DOWNLOAD_API_ERRORS,
)
from browser_worker.features.downloads.presentation.router import download_router
from browser_worker.features.health.infrastructure import HealthProvider
from browser_worker.features.health.presentation.router import health_router
from browser_worker.features.recordings.infrastructure import RecordingProvider
from browser_worker.features.recordings.presentation.errors import (
    API_ERRORS as RECORDING_API_ERRORS,
)
from browser_worker.features.recordings.presentation.router import recording_router
from browser_worker.features.screencast.infrastructure import ScreencastProvider
from browser_worker.features.screencast.presentation.router import screencast_router
from browser_worker.features.workspace.infrastructure import WorkspaceProvider
from browser_worker.lifespan import lifespan
from browser_worker.presentation.api_errors import register_api_error_handlers
from browser_worker.presentation.middleware import RequestLoggingMiddleware

API_PREFIX = "/api/v1"
ROUTERS = (
    health_router,
    browser_router,
    screencast_router,
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
    app = FastAPI(title="Browser Browser Worker", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        WorkspaceProvider(),
        BrowserProvider(service),
        ScreencastProvider(),
        DownloadProvider(),
        BrowserStateProvider(),
        RecordingProvider(),
        HealthProvider(),
    )
    setup_dishka(container, app)
    return app


app = create_app()
