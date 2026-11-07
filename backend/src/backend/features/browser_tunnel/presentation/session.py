import logging
from contextlib import suppress
from typing import Annotated
from uuid import UUID

from fastapi import Path, WebSocket, WebSocketDisconnect
from fastapi_canon.integrations.websockets import (
    CanonWebSocketRouter,
    Inject,
    RpcLimits,
    ServerVariable,
    serve_websocket,
)
from fastapi_canon.integrations.websockets.adapters.dishka import Dishka
from starlette.websockets import WebSocketState

from backend.features.browser_tunnel.domain import Browser
from backend.features.browser_tunnel.infrastructure.cdp_browser import CdpBrowser
from backend.features.browser_tunnel.infrastructure.settings import BrowserSettings
from backend.features.browser_tunnel.presentation.rpc import (
    BROWSER_CHANNEL,
)
from backend.features.browsers.application.exceptions import BrowserNotFoundException
from backend.features.browsers.infrastructure.routes import BrowserWorkerRoutes
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import SessionNotActiveException
from backend.features.sessions.infrastructure.lease_keeper import SessionLeaseKeeper
from backend.features.sessions.presentation.connection import (
    log_disconnect,
    resolve_session,
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
                await serve_websocket(
                    BROWSER_ENDPOINT,
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


async def session_tunnel(
    session_id: Annotated[UUID, Path(alias="sessionId")],
    websocket: WebSocket,
    tunnel: Inject[BrowserTunnel],
    lease_keeper: Inject[SessionLeaseKeeper],
    routes: Inject[BrowserWorkerRoutes],
) -> None:
    session = await resolve_session(websocket, lease_keeper, session_id, renew=True)
    if session is None:
        return
    try:
        logger.info(
            "Session tunnel connected session_id=%s owner_id=%s browser_id=%s "
            "slot=%s generation=%s expires_at=%s",
            session_id,
            session.owner_id,
            session.browser_id,
            session.browser.slot.id,
            session.lease_generation,
            session.expires_at.isoformat() if session.expires_at else None,
        )
        await lease_keeper.run(
            session_id,
            tunnel.serve(websocket, routes.cdp_url(session.browser.slot)),
        )
    except (
        LeaseNotFoundException,
        BrowserNotFoundException,
        SessionNotActiveException,
    ):
        logger.info(
            "Session tunnel lost its lease session_id=%s; closing transport",
            session_id,
        )
        await websocket.close(code=1008, reason="Session lease expired")
    finally:
        # State capture is an independent HTTP operation. Keep the lease alive
        # when this transport drops so state can still be read from the worker.
        # DELETE /sessions/{id} or the TTL releases the browser.
        await log_disconnect(lease_keeper, session_id)


router = CanonWebSocketRouter(version=2, resolver=Dishka())
BROWSER_ENDPOINT = router.socket(
    "/sessions/{sessionId}/tunnel",
    name="backendSession",
    channels=(BROWSER_CHANNEL,),
    limits=RpcLimits(max_concurrency=1),
    serve=session_tunnel,
)
BROWSER_CONTRACT = router.contract(
    title="Browser Backend",
    base_url="ws://127.0.0.1:8000/api/v1",
    variables={"sessionId": ServerVariable(default="{sessionId}")},
)
