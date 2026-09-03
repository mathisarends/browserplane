from fastapi import APIRouter

from control_plane.routes.browsers import router as browsers_router
from control_plane.routes.health import router as health_router
from control_plane.routes.leases import router as leases_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(browsers_router)
router.include_router(leases_router)
