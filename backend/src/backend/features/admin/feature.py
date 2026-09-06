from backend.features.admin.infrastructure import AdminProvider
from backend.features.admin.presentation.router import admin_router
from backend.shared.feature import Feature

feature = Feature(
    name="admin",
    routers=(admin_router,),
    providers=(AdminProvider,),
)
