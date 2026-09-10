from fastapi import FastAPI
from fastapi_canon import CanonRouter, Composition, ErrorOptions, Feature

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.browser.feature import feature as browser_feature
from browser_worker.features.browser.infrastructure import BrowserProvider
from browser_worker.features.downloads.feature import feature as downloads_feature
from browser_worker.features.health.feature import feature as health_feature
from browser_worker.features.recordings.feature import feature as recordings_feature
from browser_worker.features.release.feature import feature as release_feature
from browser_worker.features.screencast.feature import feature as screencast_feature
from browser_worker.features.state.feature import feature as state_feature
from browser_worker.features.workspace.infrastructure import WorkspaceProvider
from browser_worker.lifespan import lifespan
from browser_worker.presentation.middleware import RequestLoggingMiddleware

API_PREFIX = "/api/v1"
PROBLEM_TYPE_BASE = "https://browser-provisioner.local/problems"
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
    app.add_middleware(RequestLoggingMiddleware)
    providers = (BrowserProvider(service),) if service is not None else ()
    composition = Composition(
        Feature(name="infrastructure", providers=(WorkspaceProvider,)),
        *FEATURES,
        Feature(name="overrides", providers=providers),
        errors=ErrorOptions(type_base=PROBLEM_TYPE_BASE),
        router_factory=lambda: CanonRouter(prefix=API_PREFIX),
    )
    composition.apply(app)
    return app


app = create_app()
