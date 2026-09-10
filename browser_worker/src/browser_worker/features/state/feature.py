from fastapi_canon import Feature

from browser_worker.features.state.infrastructure import BrowserStateProvider
from browser_worker.features.state.presentation.errors import ERRORS
from browser_worker.features.state.presentation.router import browser_state_router

feature = Feature(
    name="state",
    routers=(browser_state_router,),
    providers=(BrowserStateProvider,),
    errors=ERRORS,
)
