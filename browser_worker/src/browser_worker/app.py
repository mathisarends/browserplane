from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI

from browser_worker.container import create_container
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.browser.feature import feature as browser_feature
from browser_worker.features.browser.infrastructure import BrowserProvider
from browser_worker.features.downloads.feature import feature as downloads_feature
from browser_worker.features.health.feature import feature as health_feature
from browser_worker.features.recordings.feature import feature as recordings_feature
from browser_worker.features.release.feature import feature as release_feature
from browser_worker.features.screencast.feature import feature as screencast_feature
from browser_worker.features.state.feature import feature as state_feature
from browser_worker.lifespan import lifespan
from browser_worker.presentation.api_errors import register_api_error_handlers
from browser_worker.presentation.middleware import RequestLoggingMiddleware
from browser_worker.shared.feature import Feature

API_PREFIX = "/api/v1"
FEATURES = (
    health_feature,
    browser_feature,
    screencast_feature,
    state_feature,
    downloads_feature,
    recordings_feature,
    release_feature,
)


def create_app(service: BrowserService | None = None) -> FastAPI:
    app = FastAPI(title="Browser Worker", version="0.1.0", lifespan=lifespan)
    _configure_app(app, FEATURES)
    container = create_container(
        FEATURES,
        (BrowserProvider(service),) if service is not None else (),
    )
    setup_dishka(container, app)
    _register_routes(app, FEATURES)
    return app


def _configure_app(app: FastAPI, features: tuple[Feature, ...]) -> None:
    app.add_middleware(RequestLoggingMiddleware)
    register_api_error_handlers(
        app,
        tuple(error for feature in features for error in feature.api_errors),
    )


def _register_routes(app: FastAPI, features: tuple[Feature, ...]) -> None:
    api_router = APIRouter(prefix=API_PREFIX)
    for feature in features:
        for router in feature.routers:
            api_router.include_router(router)
    app.include_router(api_router)


app = create_app()
