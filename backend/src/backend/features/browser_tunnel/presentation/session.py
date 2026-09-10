import logging
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect
from pyrpckit.fastapi import serve
from starlette.websockets import WebSocketState

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.infrastructure.cdp_browser import CdpBrowser
from backend.features.browser_tunnel.infrastructure.settings import BrowserSettings
from backend.features.browser_tunnel.presentation.rpc import (
    BROWSER_CHANNEL,
)

logger = logging.getLogger(__name__)


class BrowserTunnel:
    """Run the backend-owned RPC adapter against one internal CDP stream."""

    def __init__(self, *, width: int, height: int) -> None:
        self._width = width
        self._height = height

    async def serve(self, websocket: WebSocket, cdp_url: str) -> None:
        browser = CdpBrowser(
            BrowserSettings(
                cdp_url=cdp_url,
                width=self._width,
                height=self._height,
                _env_file=None,
            )
        )
        try:
            await browser.start()
            with suppress(WebSocketDisconnect):
                await serve(
                    BROWSER_CHANNEL,
                    websocket,
                    context={Browser: browser},
                )
        except Exception as error:
            # The internal CDP address must never leak into logs or close reasons.
            logger.warning(
                "Browser RPC session became unavailable (%s)", type(error).__name__
            )
            if websocket.application_state is WebSocketState.CONNECTING:
                await websocket.accept()
            if websocket.application_state is WebSocketState.CONNECTED:
                with suppress(RuntimeError):
                    await websocket.close(code=1011, reason="Browser unavailable")
        finally:
            await browser.stop()
