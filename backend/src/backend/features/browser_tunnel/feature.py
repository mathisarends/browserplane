from fastapi_canon import Feature

from backend.features.browser_tunnel.infrastructure.provider import (
    BrowserTunnelProvider,
)
from backend.features.browser_tunnel.presentation.session import router

feature = Feature(
    name="browser_tunnel",
    routers=(router,),
    providers=(BrowserTunnelProvider,),
)
