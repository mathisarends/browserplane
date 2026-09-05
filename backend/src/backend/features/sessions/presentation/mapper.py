from collections.abc import Sequence

from backend.features.sessions.application.models import (
    AuthenticationStateSnapshot,
    BrowserStateSnapshot,
    Session,
    SessionStatus,
    SuspendedSession,
)
from backend.features.sessions.presentation.schemas import (
    AuthenticationStateSnapshotResponse,
    BrowserStateSnapshotResponse,
    OpenSessionResponse,
    OwnerSessionsResponse,
    SessionResponse,
)
from generated.data_plane import AuthenticationStateSchema, BrowserStateSchema

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


def to_open_session_response(
    session: Session, *, remaining_capacity: int
) -> OpenSessionResponse:
    response = to_session_response(session)
    return OpenSessionResponse(
        **response.model_dump(), remaining_capacity=remaining_capacity
    )


def to_owner_sessions_response(
    sessions: Sequence[Session | SuspendedSession], *, remaining_capacity: int
) -> OwnerSessionsResponse:
    return OwnerSessionsResponse(
        sessions=[to_session_response(session) for session in sessions],
        remaining_capacity=remaining_capacity,
    )


def _to_suspended_response(suspended: SuspendedSession) -> SessionResponse:
    return SessionResponse(
        id=suspended.id,
        status=SessionStatus.SUSPENDED,
        owner_id=suspended.owner_id,
        expires_at=suspended.expires_at,
        created_at=suspended.created_at,
    )


def to_browser_state_snapshot_response(
    snapshot: BrowserStateSnapshot,
) -> BrowserStateSnapshotResponse:
    return BrowserStateSnapshotResponse(
        id=snapshot.id,
        name=snapshot.name,
        source_browser=snapshot.source_browser,
        created_at=snapshot.created_at,
        browser_state=BrowserStateSchema.model_validate(snapshot.browser_state),
    )


def to_authentication_state_snapshot_response(
    snapshot: AuthenticationStateSnapshot,
) -> AuthenticationStateSnapshotResponse:
    return AuthenticationStateSnapshotResponse(
        id=snapshot.id,
        name=snapshot.name,
        source_browser=snapshot.source_browser,
        created_at=snapshot.created_at,
        authentication_state=AuthenticationStateSchema.model_validate(
            snapshot.authentication_state
        ),
    )
