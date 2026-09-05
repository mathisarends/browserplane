from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.provider import BrowserProvider
from backend.features.health.presentation.router import health_router
from backend.features.leases.provider import LeaseProvider
from backend.features.sessions.application.ports import (
    BrowserStateGateway,
    SuspendedSessionRepository,
)
from backend.features.sessions.presentation.errors import (
    API_ERRORS as SESSION_API_ERRORS,
)
from backend.features.sessions.presentation.router import session_router
from backend.features.sessions.provider import SessionProvider
from backend.infrastructure.provider import DatabaseProvider
from backend.lifespan import lifespan
from backend.presentation.api_errors import register_api_error_handlers
from backend.provider import SettingsProvider

API_PREFIX = "/api/v1"
API_ERRORS = SESSION_API_ERRORS
ROUTERS = (health_router, session_router)


def create_app(
    provisioner: BrowserProvisioner | None = None,
    repository: BrowserRepository | None = None,
    suspensions: SuspendedSessionRepository | None = None,
    browser_state: BrowserStateGateway | None = None,
) -> FastAPI:
    app = FastAPI(title="Browser Backend", version="0.1.0", lifespan=lifespan)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        SettingsProvider(),
        DatabaseProvider(),
        BrowserProvider(provisioner, repository),
        LeaseProvider(),
        SessionProvider(suspensions, browser_state),
    )
    setup_dishka(container, app)
    return app


app = create_app()
