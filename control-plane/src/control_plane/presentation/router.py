from fastapi import APIRouter

from control_plane.features.browsers.presentation.routes import browser_router
from control_plane.features.health.presentation.routes import health_router
from control_plane.features.leases.presentation.routes import lease_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(browser_router)
api_router.include_router(lease_router)
