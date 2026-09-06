from uuid import UUID

from backend.features.sessions.application.models import (
    AuthenticationStateSnapshot,
    BrowserStateSnapshot,
    SuspendedSession,
)
from backend.features.sessions.application.ports import (
    AuthenticationStateSnapshotRepository,
    BrowserStateSnapshotRepository,
    SuspendedSessionRepository,
)


class InMemorySuspendedSessionRepository(SuspendedSessionRepository):
    """Process-local repository, used to run the app without Postgres."""

    def __init__(self) -> None:
        self._suspended: dict[UUID, SuspendedSession] = {}

    async def save(self, *, suspended: SuspendedSession) -> SuspendedSession:
        self._suspended[suspended.id] = suspended
        return suspended

    async def get_by_id(self, *, session_id: UUID) -> SuspendedSession | None:
        return self._suspended.get(session_id)

    async def list(self) -> tuple[SuspendedSession, ...]:
        return tuple(
            sorted(
                self._suspended.values(),
                key=lambda suspended: suspended.created_at,
                reverse=True,
            )
        )

    async def delete(self, *, session_id: UUID) -> None:
        self._suspended.pop(session_id, None)


class InMemoryBrowserStateSnapshotRepository(BrowserStateSnapshotRepository):
    def __init__(self) -> None:
        self._snapshots: dict[UUID, BrowserStateSnapshot] = {}

    async def save(self, *, snapshot: BrowserStateSnapshot) -> BrowserStateSnapshot:
        self._snapshots[snapshot.id] = snapshot
        return snapshot

    async def list(self) -> tuple[BrowserStateSnapshot, ...]:
        return tuple(
            sorted(
                self._snapshots.values(),
                key=lambda snapshot: snapshot.created_at,
                reverse=True,
            )
        )


class InMemoryAuthenticationStateSnapshotRepository(
    AuthenticationStateSnapshotRepository
):
    def __init__(self) -> None:
        self._snapshots: dict[UUID, AuthenticationStateSnapshot] = {}

    async def save(
        self, *, snapshot: AuthenticationStateSnapshot
    ) -> AuthenticationStateSnapshot:
        self._snapshots[snapshot.id] = snapshot
        return snapshot

    async def list(self) -> tuple[AuthenticationStateSnapshot, ...]:
        return tuple(
            sorted(
                self._snapshots.values(),
                key=lambda snapshot: snapshot.created_at,
                reverse=True,
            )
        )
