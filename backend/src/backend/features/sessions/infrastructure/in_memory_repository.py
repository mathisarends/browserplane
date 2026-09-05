from uuid import UUID

from backend.features.sessions.application.models import SuspendedSession
from backend.features.sessions.application.ports import SuspendedSessionRepository


class InMemorySuspendedSessionRepository(SuspendedSessionRepository):
    """Process-local repository, used to run the app without Postgres."""

    def __init__(self) -> None:
        self._suspended: dict[UUID, SuspendedSession] = {}

    async def save(self, *, suspended: SuspendedSession) -> SuspendedSession:
        self._suspended[suspended.id] = suspended
        return suspended

    async def get_by_id(self, *, session_id: UUID) -> SuspendedSession | None:
        return self._suspended.get(session_id)

    async def delete(self, *, session_id: UUID) -> None:
        self._suspended.pop(session_id, None)
