from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from control_plane.features.browsers.application.ports import BrowserProvisioner
from control_plane.features.browsers.presentation.errors import (
    API_ERRORS as BROWSER_API_ERRORS,
)
from control_plane.features.browsers.presentation.router import browser_router
from control_plane.features.browsers.provider import BrowserProvider
from control_plane.features.health.presentation.router import health_router
from control_plane.features.leases.presentation.errors import (
    API_ERRORS as LEASE_API_ERRORS,
)
from control_plane.features.leases.presentation.router import lease_router
from control_plane.features.leases.provider import LeaseProvider
from control_plane.lifespan import lifespan
from control_plane.presentation.api_errors import register_api_error_handlers
from control_plane.provider import SettingsProvider

API_PREFIX = "/api/v1"
API_ERRORS = (*BROWSER_API_ERRORS, *LEASE_API_ERRORS)
ROUTERS = (health_router, browser_router, lease_router)


def create_app(provisioner: BrowserProvisioner | None = None) -> FastAPI:
    app = FastAPI(title="Browser Control Plane", version="0.1.0", lifespan=lifespan)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_api_error_handlers(app, API_ERRORS)
    container = make_async_container(
        SettingsProvider(),
        BrowserProvider(provisioner),
        LeaseProvider(),
    )
    setup_dishka(container, app)
    return app


app = create_app()
