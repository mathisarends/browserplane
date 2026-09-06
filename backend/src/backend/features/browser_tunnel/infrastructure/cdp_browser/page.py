from collections.abc import Awaitable, Callable

from cdpify import CDPSession

from backend.features.browser_tunnel.application import BrowserTab
from backend.features.browser_tunnel.infrastructure.cdp_browser.clipboard import (
    CdpClipboard,
)
from backend.features.browser_tunnel.infrastructure.cdp_browser.input import CdpInput
from backend.features.browser_tunnel.infrastructure.cdp_browser.navigation import (
    CdpNavigation,
)
from backend.features.browser_tunnel.infrastructure.cdp_browser.page_metadata import (
    CdpPageMetadata,
)
from backend.features.browser_tunnel.infrastructure.cursor_event_bridge import (
    CursorEventBridge,
)
from backend.features.browser_tunnel.infrastructure.events.stream import PublishEvent
from backend.features.browser_tunnel.infrastructure.page_event_bridge import (
    PageEventBridge,
)
from backend.features.browser_tunnel.infrastructure.settings import BrowserSettings


class CdpPage:
    def __init__(
        self,
        session: CDPSession,
        target_id: str,
        tabs: Callable[[], Awaitable[list[BrowserTab]]],
        publish: PublishEvent,
        failed: Callable[[], None],
    ) -> None:
        self.session = session
        self.target_id = target_id
        self.clipboard = CdpClipboard(session)
        self.input = CdpInput(session, self.clipboard)
        self.navigation = CdpNavigation(session)
        self.events = PageEventBridge(
            session, target_id, CdpPageMetadata(session), tabs, publish, failed
        )
        self.cursor = CursorEventBridge(publish)

    async def start(self, settings: BrowserSettings) -> None:
        await self.session.page.enable()
        await self.session.network.enable()
        await self.session.emulation.set_device_metrics_override(
            width=settings.width,
            height=settings.height,
            device_scale_factor=1,
            mobile=False,
        )
        await self.events.start()
        await self.cursor.start(self.session, self.target_id)

    async def stop(self) -> None:
        try:
            await self.events.stop()
        finally:
            await self.cursor.stop()
