import logging
from typing import Annotated
from uuid import UUID

from fastapi import Path, WebSocket
from fastapi_canon.integrations.websockets import (
    CanonWebSocketRouter,
    Inject,
    RpcLimits,
    ServerVariable,
)
from fastapi_canon.integrations.websockets.adapters.dishka import Dishka

from backend.features.browser_tunnel.presentation.rpc import BROWSER_CHANNEL
from backend.features.browser_tunnel.presentation.session import BrowserTunnel
from backend.features.browsers.application import (
    BrowserNotFoundException,
    BrowserWorkerRoutes,
)
from backend.features.sessions.application import (
    SessionLeaseKeeper,
    SessionNotActiveException,
    SessionNotFoundException,
)
from backend.features.sessions.presentation.connection import (
    log_disconnect,
    resolve_session,
)

logger = logging.getLogger(__name__)


async def _session_tunnel(
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
            tunnel.serve(
                websocket, routes.cdp_url(session.browser.slot), _BROWSER_ENDPOINT
            ),
        )
    except (
        SessionNotFoundException,
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
_BROWSER_ENDPOINT = router.socket(
    "/sessions/{sessionId}/tunnel",
    name="backendSession",
    channels=(BROWSER_CHANNEL,),
    limits=RpcLimits(max_concurrency=1),
    serve=_session_tunnel,
)
BROWSER_CONTRACT = router.contract(
    title="Browser Backend",
    base_url="ws://127.0.0.1:8000/api/v1",
    variables={"sessionId": ServerVariable(default="{sessionId}")},
)
