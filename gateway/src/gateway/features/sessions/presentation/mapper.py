from gateway.features.sessions.application.models import Session
from gateway.features.sessions.presentation.schemas import SessionResponse

SESSION_PATH = "/api/v1/sessions"


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        browser_id=session.browser_id,
        owner_id=session.lease.owner_id,
        expires_at=session.lease.expires_at,
        created_at=session.lease.created_at,
        tunnel_path=f"{SESSION_PATH}/{session.id}/tunnel",
        screencast_path=f"{SESSION_PATH}/{session.id}/screencast",
    )
