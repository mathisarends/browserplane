from uuid import UUID

from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    SessionRepository,
)
from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    BrowserCheckpoint,
    Session,
)


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}

    async def save(self, session: Session) -> Session:
        self._sessions[session.id] = session
        return session

    async def get_by_id(self, *, session_id: UUID) -> Session | None:
        return self._sessions.get(session_id)

    async def list(self) -> tuple[Session, ...]:
        return tuple(
            sorted(
                self._sessions.values(),
                key=lambda session: session.created_at,
                reverse=True,
            )
        )


class InMemoryBrowserCheckpointRepository(BrowserCheckpointRepository):
    def __init__(self) -> None:
        self._checkpoints: dict[UUID, BrowserCheckpoint] = {}

    async def save(self, checkpoint: BrowserCheckpoint) -> BrowserCheckpoint:
        self._checkpoints[checkpoint.id] = checkpoint
        return checkpoint

    async def get_by_id(self, *, checkpoint_id: UUID) -> BrowserCheckpoint | None:
        return self._checkpoints.get(checkpoint_id)

    async def list(self) -> tuple[BrowserCheckpoint, ...]:
        return tuple(
            sorted(
                self._checkpoints.values(),
                key=lambda checkpoint: checkpoint.created_at,
                reverse=True,
            )
        )

    async def delete(self, checkpoint_id: UUID) -> bool:
        return self._checkpoints.pop(checkpoint_id, None) is not None


class InMemoryAuthenticationProfileRepository(AuthenticationProfileRepository):
    def __init__(self) -> None:
        self._profiles: dict[UUID, AuthenticationProfile] = {}

    async def save(self, profile: AuthenticationProfile) -> AuthenticationProfile:
        self._profiles[profile.id] = profile
        return profile

    async def get_by_id(self, *, profile_id: UUID) -> AuthenticationProfile | None:
        return self._profiles.get(profile_id)

    async def list(self) -> tuple[AuthenticationProfile, ...]:
        return tuple(
            sorted(
                self._profiles.values(),
                key=lambda profile: profile.created_at,
                reverse=True,
            )
        )

    async def delete(self, profile_id: UUID) -> bool:
        return self._profiles.pop(profile_id, None) is not None
