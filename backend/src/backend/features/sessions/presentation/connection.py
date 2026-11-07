import logging
from uuid import UUID

from fastapi import WebSocket

from backend.features.browsers.application import BrowserNotFoundException
from backend.features.sessions.application import (
    SessionLeaseKeeper,
    SessionNotActiveException,
    SessionNotFoundException,
)
from backend.features.sessions.domain import ResolvedSession

logger = logging.getLogger(__name__)


async def resolve_session(
    websocket: WebSocket,
    lease_keeper: SessionLeaseKeeper,
    session_id: UUID,
    *,
    renew: bool = False,
) -> ResolvedSession | None:
    """Look up the live session, closing the socket in session terms when it is gone."""
    try:
        session = await lease_keeper.resolve(session_id, renew=renew)
        return session
    except (
        SessionNotFoundException,
        BrowserNotFoundException,
        SessionNotActiveException,
    ):
        await websocket.accept()
        await websocket.close(code=1008, reason="Session not found")
        return None


async def log_disconnect(lease_keeper: SessionLeaseKeeper, session_id: UUID) -> None:
    """Say when the unheartbeated lease falls to the reaper, not just that it will."""
    try:
        session = await lease_keeper.resolve(session_id)
    except (
        SessionNotFoundException,
        BrowserNotFoundException,
        SessionNotActiveException,
    ):
        logger.info(
            "Session tunnel disconnected; lease already gone session_id=%s", session_id
        )
        return
    logger.info(
        "Session tunnel disconnected; no more heartbeats, lease left to its TTL "
        "session_id=%s expires_at=%s reclaim_after=%s",
        session_id,
        session.expires_at.isoformat() if session.expires_at else None,
        session.reclaim_after.isoformat() if session.reclaim_after else None,
    )
