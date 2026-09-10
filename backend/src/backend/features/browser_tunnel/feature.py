from fastapi_canon import Feature

from backend.features.browser_tunnel.infrastructure import BrowserTunnelProvider

feature = Feature(
    name="browser_tunnel",
    providers=(BrowserTunnelProvider,),
)
