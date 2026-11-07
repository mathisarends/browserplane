import logging
from collections.abc import Callable
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect
from fastapi_canon.integrations.websockets import RpcEndpoint, serve_websocket
from starlette.websockets import WebSocketState

from backend.features.browser_tunnel.domain import Browser

type BrowserFactory = Callable[[str], Browser]

logger = logging.getLogger(__name__)


class BrowserTunnel:
    """Run the backend-owned RPC adapter against one internal CDP stream."""

    def __init__(self, browser_factory: BrowserFactory) -> None:
        self._browser_factory = browser_factory

    async def serve(
        self, websocket: WebSocket, cdp_url: str, endpoint: RpcEndpoint
    ) -> None:
        browser = self._browser_factory(cdp_url)
        try:
            await browser.start()
            with suppress(WebSocketDisconnect):
                await serve_websocket(
                    endpoint,
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
