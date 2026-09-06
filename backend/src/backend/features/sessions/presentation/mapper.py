from collections.abc import Sequence

from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    BrowserCheckpoint,
    ResolvedSession,
)
from backend.features.sessions.presentation.schemas import (
    AuthenticationProfileResponse,
    BrowserCheckpointResponse,
    OpenSessionResponse,
    OwnerSessionsResponse,
    SessionResponse,
)

SESSION_PATH = "/api/v1/sessions"


def to_session_response(context: ResolvedSession) -> SessionResponse:
    session = context.session
    has_browser = context.browser_id is not None
    return SessionResponse(
        id=session.id,
        status=session.status,
        owner_id=session.owner_id,
        expires_at=context.expires_at,
        created_at=session.created_at,
        browser_checkpoint_id=session.browser_checkpoint_id,
        lease_generation=context.lease_generation,
        reclaim_after=context.reclaim_after,
        browser_id=context.browser_id,
        tunnel_path=(f"{SESSION_PATH}/{session.id}/tunnel" if has_browser else None),
        screencast_path=(
            f"{SESSION_PATH}/{session.id}/screencast" if has_browser else None
        ),
    )


def to_open_session_response(
    session: ResolvedSession, *, remaining_capacity: int
) -> OpenSessionResponse:
    return OpenSessionResponse(
        **to_session_response(session).model_dump(),
        remaining_capacity=remaining_capacity,
    )


def to_owner_sessions_response(
    sessions: Sequence[ResolvedSession], *, remaining_capacity: int
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
