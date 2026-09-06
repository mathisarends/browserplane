from browser_worker.features.state.infrastructure import BrowserStateProvider
from browser_worker.features.state.presentation.errors import API_ERRORS
from browser_worker.features.state.presentation.router import browser_state_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name="state",
    routers=(browser_state_router,),
    providers=(BrowserStateProvider,),
    api_errors=API_ERRORS,
)
