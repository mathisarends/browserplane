from collections.abc import Sequence

from dishka import Provider
from fastapi import APIRouter, FastAPI
from fastapi_canon import Composition, ErrorOptions, Feature

from backend.features.admin.feature import feature as admin_feature
from backend.features.browser_tunnel.feature import feature as browser_tunnel_feature
from backend.features.browsers.feature import feature as browsers_feature
from backend.features.health.feature import feature as health_feature
from backend.features.leases.feature import feature as leases_feature
from backend.features.recordings.feature import feature as recordings_feature
from backend.features.session_requests.feature import (
    feature as session_requests_feature,
)
from backend.features.sessions.feature import feature as sessions_feature
from backend.infrastructure.browser_worker import BrowserWorkerProvider
from backend.infrastructure.database import DatabaseProvider
from backend.infrastructure.storage.provider import StorageProvider
from backend.lifespan import lifespan
from backend.presentation.middleware import install_request_logging

API_PREFIX = "/api/v1"
PROBLEM_TYPE_BASE = "https://browser-provisioner.local/problems"
FEATURES = (
    health_feature,
    browser_tunnel_feature,
    browsers_feature,
    leases_feature,
    sessions_feature,
    session_requests_feature,
    recordings_feature,
    admin_feature,
)


def create_app(provider_overrides: Sequence[Provider] = ()) -> FastAPI:
    app = FastAPI(title="Browser Backend", version="0.1.0", lifespan=lifespan)
    install_request_logging(app)
    composition = Composition(
        _core_feature(),
        *FEATURES,
        _overrides_feature(provider_overrides),
        errors=ErrorOptions(type_base=PROBLEM_TYPE_BASE),
        router_factory=lambda: APIRouter(prefix=API_PREFIX),
    )
    composition.apply(app)
    return app


def _core_feature() -> Feature:
    return Feature(
        name="infrastructure",
        providers=(StorageProvider, DatabaseProvider, BrowserWorkerProvider),
    )


def _overrides_feature(provider_overrides: Sequence[Provider]) -> Feature:
    return Feature(name="overrides", providers=provider_overrides)


app = create_app()
