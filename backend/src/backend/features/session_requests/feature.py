from backend.features.session_requests.infrastructure.provider import (
    SessionRequestProvider,
)
from backend.features.session_requests.presentation.errors import API_ERRORS
from backend.features.session_requests.presentation.router import (
    acquisition_router,
    session_request_router,
)
from backend.shared.feature import Feature

feature = Feature(
    name="session_requests",
    providers=(SessionRequestProvider,),
    routers=(acquisition_router, session_request_router),
    api_errors=API_ERRORS,
)
