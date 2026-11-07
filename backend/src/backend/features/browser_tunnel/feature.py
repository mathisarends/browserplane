from fastapi_canon import Feature

from backend.features.browser_tunnel.infrastructure.provider import (
    BrowserTunnelProvider,
)

feature = Feature(
    name="browser_tunnel",
    providers=(BrowserTunnelProvider,),
)
