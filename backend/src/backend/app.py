from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from backend.features.health.presentation.router import health_router
from backend.features.sessions.presentation.errors import (
    API_ERRORS as SESSION_API_ERRORS,
)
from backend.features.sessions.presentation.router import session_router
from backend.features.sessions.provider import SessionProvider
from backend.presentation.api_errors import register_api_error_handlers
from backend.presentation.upstream_errors import API_ERRORS as UPSTREAM_API_ERRORS
from backend.provider import SettingsProvider

API_PREFIX = "/api/v1"
API_ERRORS = (*SESSION_API_ERRORS, *UPSTREAM_API_ERRORS)
ROUTERS = (health_router, session_router)


def create_app() -> FastAPI:
    app = FastAPI(title="Browser Backend", version="0.1.0")
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(SettingsProvider(), SessionProvider())
    setup_dishka(container, app)
    return app


app = create_app()
