from collections.abc import Sequence

from backend.features.sessions.domain.models import (
    ActiveSession,
    AuthenticationProfile,
    BrowserCheckpoint,
    Session,
)
from backend.features.sessions.presentation.schemas import (
    AuthenticationProfileResponse,
    BrowserCheckpointResponse,
    OpenSessionResponse,
    OwnerSessionsResponse,
    SessionResponse,
)

SESSION_PATH = "/api/v1/sessions"


def to_session_response(session: ActiveSession | Session) -> SessionResponse:
    aggregate = session.session if isinstance(session, ActiveSession) else session
    return SessionResponse(
        id=aggregate.id,
        status=aggregate.status,
        owner_id=aggregate.owner_id,
        expires_at=(
            session.lease.expires_at
            if isinstance(session, ActiveSession)
            else aggregate.expires_at
        ),
        created_at=aggregate.created_at,
        browser_checkpoint_id=aggregate.browser_checkpoint_id,
        lease_generation=(
            session.lease.generation if isinstance(session, ActiveSession) else None
        ),
        reclaim_after=(
            session.lease.reclaim_after if isinstance(session, ActiveSession) else None
        ),
        browser_id=session.browser_id if isinstance(session, ActiveSession) else None,
        tunnel_path=(
            f"{SESSION_PATH}/{aggregate.id}/tunnel"
            if isinstance(session, ActiveSession)
            else None
        ),
        screencast_path=(
            f"{SESSION_PATH}/{aggregate.id}/screencast"
            if isinstance(session, ActiveSession)
            else None
        ),
    )


def to_open_session_response(
    session: ActiveSession, *, remaining_capacity: int
) -> OpenSessionResponse:
    return OpenSessionResponse(
        **to_session_response(session).model_dump(),
        remaining_capacity=remaining_capacity,
    )


def to_owner_sessions_response(
    sessions: Sequence[ActiveSession | Session], *, remaining_capacity: int
) -> OwnerSessionsResponse:
    return OwnerSessionsResponse(
        sessions=[to_session_response(session) for session in sessions],
        remaining_capacity=remaining_capacity,
    )


def to_browser_checkpoint_response(
    checkpoint: BrowserCheckpoint,
) -> BrowserCheckpointResponse:
    return BrowserCheckpointResponse(
        id=checkpoint.id,
        created_at=checkpoint.created_at,
        authentication_profile_id=checkpoint.authentication_profile_id,
    )


def to_authentication_profile_response(
    profile: AuthenticationProfile,
) -> AuthenticationProfileResponse:
    return AuthenticationProfileResponse(
        id=profile.id,
        name=profile.name,
        created_at=profile.created_at,
    )
