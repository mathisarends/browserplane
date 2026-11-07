from fastapi_canon import Feature

from backend.features.admin.infrastructure.provider import AdminProvider
from backend.features.admin.presentation.router import admin_router

feature = Feature(
    name="admin",
    routers=(admin_router,),
    providers=(AdminProvider,),
)
