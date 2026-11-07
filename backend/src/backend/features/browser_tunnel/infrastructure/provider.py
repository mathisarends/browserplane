from dishka import Provider, Scope, provide

from backend.features.browser_tunnel.infrastructure.cdp_browser import CdpBrowser
from backend.features.browser_tunnel.infrastructure.settings import (
    BrowserSettings,
    BrowserTunnelSettings,
)
from backend.features.browser_tunnel.presentation.session import BrowserTunnel


class BrowserTunnelProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> BrowserTunnelSettings:
        return BrowserTunnelSettings()

    @provide(scope=Scope.APP)
    def browser_tunnel(self, settings: BrowserTunnelSettings) -> BrowserTunnel:
        return BrowserTunnel(
            browser_factory=lambda cdp_url: CdpBrowser(
                BrowserSettings(
                    cdp_url=cdp_url,
                    width=settings.browser_width,
                    height=settings.browser_height,
                    _env_file=None,
                )
            ),
        )
