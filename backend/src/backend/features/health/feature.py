from fastapi_canon import Feature

from backend.features.health.infrastructure.provider import HealthProvider
from backend.features.health.presentation.router import health_router

feature = Feature(
    name="health",
    routers=(health_router,),
    providers=(HealthProvider,),
)
