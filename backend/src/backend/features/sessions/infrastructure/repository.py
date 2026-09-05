from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.sessions.application.models import SuspendedSession
from backend.features.sessions.application.ports import SuspendedSessionRepository
from backend.infrastructure.orm import SuspendedSessionModel
from backend.infrastructure.repository import SqlRepository


class SqlSuspendedSessionRepository(
    SqlRepository[SuspendedSessionModel, SuspendedSession],
    SuspendedSessionRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SuspendedSessionModel)

    def to_domain(self, model: SuspendedSessionModel) -> SuspendedSession:
        return SuspendedSession(
            id=model.id,
            owner_id=model.owner_id,
            state=model.state,
            created_at=model.created_at,
            expires_at=model.expires_at,
        )

    def to_model(self, entity: SuspendedSession) -> SuspendedSessionModel:
        return SuspendedSessionModel(
            id=entity.id,
            owner_id=entity.owner_id,
            state=entity.state,
            created_at=entity.created_at,
            expires_at=entity.expires_at,
        )

    async def save(self, *, suspended: SuspendedSession) -> SuspendedSession:
        """Suspending twice under the same id overwrites the older state."""
        return await self.save_entity(suspended)

    async def get_by_id(self, *, session_id: UUID) -> SuspendedSession | None:
        return await self.find_by_id(session_id)

    async def delete(self, *, session_id: UUID) -> None:
        await self.delete_entity(session_id)
