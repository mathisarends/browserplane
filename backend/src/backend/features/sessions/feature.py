from backend.features.sessions.infrastructure import SessionProvider
from backend.features.sessions.presentation.errors import API_ERRORS
from backend.features.sessions.presentation.router import session_router
from backend.shared.feature import Feature

feature = Feature(
    name="sessions",
    routers=(session_router,),
    providers=(SessionProvider,),
    api_errors=API_ERRORS,
)
