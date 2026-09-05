from backend.features.sessions.application.models import (
    Session,
    SessionStatus,
    SuspendedSession,
)
from backend.features.sessions.presentation.schemas import SessionResponse

SESSION_PATH = "/api/v1/sessions"


def to_session_response(session: Session | SuspendedSession) -> SessionResponse:
    if isinstance(session, SuspendedSession):
        return _to_suspended_response(session)
    return SessionResponse(
        id=session.id,
        status=SessionStatus.ACTIVE,
        owner_id=session.lease.owner_id,
        expires_at=session.lease.expires_at,
        created_at=session.lease.created_at,
        browser_id=session.browser_id,
        tunnel_path=f"{SESSION_PATH}/{session.id}/tunnel",
        screencast_path=f"{SESSION_PATH}/{session.id}/screencast",
    )


def _to_suspended_response(suspended: SuspendedSession) -> SessionResponse:
    return SessionResponse(
        id=suspended.id,
        status=SessionStatus.SUSPENDED,
        owner_id=suspended.owner_id,
        expires_at=suspended.expires_at,
        created_at=suspended.created_at,
    )
