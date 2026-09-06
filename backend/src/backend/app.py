from collections.abc import Sequence

from dishka import Provider
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI

from backend.container import create_container
from backend.features.admin.feature import feature as admin_feature
from backend.features.browser_tunnel.feature import feature as browser_tunnel_feature
from backend.features.browsers.feature import feature as browsers_feature
from backend.features.health.feature import feature as health_feature
from backend.features.leases.feature import feature as leases_feature
from backend.features.recordings.feature import feature as recordings_feature
from backend.features.sessions.feature import feature as sessions_feature
from backend.lifespan import lifespan
from backend.presentation.api_errors import register_api_error_handlers
from backend.presentation.middleware import install_request_logging
from backend.shared.feature import Feature

API_PREFIX = "/api/v1"
FEATURES = (
    health_feature,
    browser_tunnel_feature,
    browsers_feature,
    leases_feature,
    sessions_feature,
    recordings_feature,
    admin_feature,
)


def create_app(provider_overrides: Sequence[Provider] = ()) -> FastAPI:
    app = FastAPI(title="Browser Backend", version="0.1.0", lifespan=lifespan)
    _configure_app(app, FEATURES)
    container = create_container(FEATURES, provider_overrides)
    setup_dishka(container, app)
    _register_routes(app, FEATURES)
    return app


def _configure_app(app: FastAPI, features: tuple[Feature, ...]) -> None:
    install_request_logging(app)
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
