from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend.browser_tunnel.presentation import browser_rpc_router
from backend.features.admin.infrastructure import AdminProvider
from backend.features.admin.presentation.router import admin_router
from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.infrastructure import BrowserProvider
from backend.features.browsers.presentation.errors import (
    API_ERRORS as BROWSER_API_ERRORS,
)
from backend.features.health.presentation.router import health_router
from backend.features.leases.infrastructure import LeaseProvider
from backend.features.recordings.infrastructure import RecordingProvider
from backend.features.recordings.presentation.errors import (
    API_ERRORS as RECORDING_API_ERRORS,
)
from backend.features.recordings.presentation.router import recording_router
from backend.features.sessions.application.ports import (
    AuthenticationStateSnapshotRepository,
    BrowserStateGateway,
    BrowserStateSnapshotRepository,
    SuspendedSessionRepository,
)
from backend.features.sessions.infrastructure import SessionProvider
from backend.features.sessions.presentation.errors import (
    API_ERRORS as SESSION_API_ERRORS,
)
from backend.features.sessions.presentation.router import session_router
from backend.infrastructure.bucket.provider import BucketProvider
from backend.infrastructure.database import DatabaseProvider
from backend.lifespan import lifespan
from backend.presentation.api_errors import register_api_error_handlers
from backend.presentation.middleware import install_request_logging

API_PREFIX = "/api/v1"
API_ERRORS = SESSION_API_ERRORS + BROWSER_API_ERRORS + RECORDING_API_ERRORS
ROUTERS = (
    health_router,
    session_router,
    recording_router,
    admin_router,
    browser_rpc_router,
)


def create_app(
    provisioner: BrowserProvisioner | None = None,
    repository: BrowserRepository | None = None,
    suspensions: SuspendedSessionRepository | None = None,
    browser_state: BrowserStateGateway | None = None,
    snapshots: BrowserStateSnapshotRepository | None = None,
    authentication_snapshots: AuthenticationStateSnapshotRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="Browser Backend", version="0.1.0", lifespan=lifespan)
    install_request_logging(app)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        BucketProvider(),
        DatabaseProvider(),
        BrowserProvider(provisioner, repository),
        RecordingProvider(),
        LeaseProvider(),
        SessionProvider(
            suspensions, browser_state, snapshots, authentication_snapshots
        ),
        AdminProvider(),
    )
    setup_dishka(container, app)
    return app


app = create_app()
