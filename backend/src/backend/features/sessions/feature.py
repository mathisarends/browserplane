from fastapi_canon import Feature

from backend.features.sessions.infrastructure import SessionProvider
from backend.features.sessions.presentation.errors import ERRORS
from backend.features.sessions.presentation.router import session_router

feature = Feature(
    name="sessions",
    routers=(session_router,),
    providers=(SessionProvider,),
    errors=ERRORS,
)
