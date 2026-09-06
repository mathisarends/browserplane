from backend.features.browser_tunnel.infrastructure import BrowserTunnelProvider
from backend.shared.feature import Feature

feature = Feature(
    name="browser_tunnel",
    providers=(BrowserTunnelProvider,),
)
