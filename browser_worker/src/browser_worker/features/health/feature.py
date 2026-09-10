from fastapi_canon import Feature

from browser_worker.features.health.infrastructure import HealthProvider
from browser_worker.features.health.presentation.router import health_router

feature = Feature(
    name="health",
    routers=(health_router,),
    providers=(HealthProvider,),
)
