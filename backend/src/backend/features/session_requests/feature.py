from fastapi_canon import Feature

from backend.features.session_requests.infrastructure.provider import (
    SessionRequestProvider,
)
from backend.features.session_requests.presentation.errors import ERRORS
from backend.features.session_requests.presentation.router import (
    acquisition_router,
    session_request_router,
)

feature = Feature(
    name="session_requests",
    providers=(SessionRequestProvider,),
    routers=(acquisition_router, session_request_router),
    errors=ERRORS,
)
