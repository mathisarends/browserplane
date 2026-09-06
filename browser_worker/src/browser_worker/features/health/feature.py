from browser_worker.features.health.infrastructure import HealthProvider
from browser_worker.features.health.presentation.router import health_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name='health',
    routers=(health_router,),
    providers=(HealthProvider,),
)
