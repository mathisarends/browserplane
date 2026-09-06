import asyncio
import json
import logging
from contextlib import suppress

import pyrpckit as rpc
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.websockets import WebSocketState

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.infrastructure.cdp_browser import CdpBrowser
from backend.features.browser_tunnel.infrastructure.settings import BrowserSettings
from backend.features.browser_tunnel.presentation.rpc import (
    BROWSER_EVENT_METHOD,
    BROWSER_PROTOCOL,
    BrowserEvent,
    browser_event,
    browser_rpc_methods,
)

logger = logging.getLogger(__name__)


class BrowserSession:
    """Serve one viewer: RPC requests in and browser state events out."""

    def __init__(self, websocket: WebSocket, browser: Browser) -> None:
        self._websocket = websocket
        self._browser = browser
        self._send_lock = asyncio.Lock()
        self._server = rpc.RpcServer(
            *browser_rpc_methods(browser),
            protocol=BROWSER_PROTOCOL,
        )

    async def run(self) -> None:
        await self._websocket.accept()
        tasks = (
            asyncio.create_task(self._stream_events()),
            asyncio.create_task(self._serve_requests()),
        )
        try:
            with suppress(WebSocketDisconnect):
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _serve_requests(self) -> None:
        while True:
            raw_request = await self._websocket.receive_text()
            try:
                request = json.loads(raw_request)
            except json.JSONDecodeError:
                await self._send(self._server.failure(None, rpc.RpcParseError()))
                continue
            response = await self._server.handle(request)
            if response is not None:
                await self._send(response)

    async def _stream_events(self) -> None:
        async for event in self._browser.events():
            await self._notify(browser_event(event))

    async def _notify(self, params: BrowserEvent) -> None:
        await self._send(
            rpc.RpcNotification(method=BROWSER_EVENT_METHOD, params=params)
        )

    async def _send(self, message: BaseModel) -> None:
        async with self._send_lock:
            await self._websocket.send_json(
                message.model_dump(mode="json", by_alias=True)
            )


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
            await BrowserSession(websocket, browser).run()
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
