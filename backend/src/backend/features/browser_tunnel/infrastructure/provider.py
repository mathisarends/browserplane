from dishka import Provider, Scope, provide

from backend.features.browser_tunnel.infrastructure.settings import (
    BrowserTunnelSettings,
)
from backend.features.browser_tunnel.presentation.session import BrowserTunnel


class BrowserTunnelProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> BrowserTunnelSettings:
        return BrowserTunnelSettings()

    @provide(scope=Scope.APP)
    def browser_tunnel(self, settings: BrowserTunnelSettings) -> BrowserTunnel:
        return BrowserTunnel(
            width=settings.browser_width,
            height=settings.browser_height,
        )
