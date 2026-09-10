from fastapi_canon import Feature

from browser_worker.features.browser.infrastructure import BrowserProvider
from browser_worker.features.browser.presentation.errors import ERRORS
from browser_worker.features.browser.presentation.router import browser_router

feature = Feature(
    name="browser",
    routers=(browser_router,),
    providers=(BrowserProvider,),
    errors=ERRORS,
)
