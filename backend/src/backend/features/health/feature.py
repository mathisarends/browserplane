from backend.features.health.infrastructure import HealthProvider
from backend.features.health.presentation.router import health_router
from backend.shared.feature import Feature

feature = Feature(
    name="health",
    routers=(health_router,),
    providers=(HealthProvider,),
)
