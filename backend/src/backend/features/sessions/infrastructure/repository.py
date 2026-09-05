from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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
from backend.infrastructure.orm import (
    AuthenticationStateSnapshotModel,
    BrowserStateSnapshotModel,
    SuspendedSessionModel,
)
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
            authentication_state=model.authentication_state,
            browser_state=model.browser_state,
            created_at=model.created_at,
            expires_at=model.expires_at,
        )

    def to_model(self, entity: SuspendedSession) -> SuspendedSessionModel:
        return SuspendedSessionModel(
            id=entity.id,
            owner_id=entity.owner_id,
            authentication_state=entity.authentication_state,
            browser_state=entity.browser_state,
            created_at=entity.created_at,
            expires_at=entity.expires_at,
        )

    async def save(self, *, suspended: SuspendedSession) -> SuspendedSession:
        """Suspending twice under the same id overwrites the older state."""
        return await self.save_entity(suspended)

    async def get_by_id(self, *, session_id: UUID) -> SuspendedSession | None:
        return await self.find_by_id(session_id)

    async def list_all(self) -> tuple[SuspendedSession, ...]:
        statement = select(SuspendedSessionModel).order_by(
            SuspendedSessionModel.created_at.desc()
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)

    async def delete(self, *, session_id: UUID) -> None:
        await self.delete_entity(session_id)


class SqlAuthenticationStateSnapshotRepository(
    SqlRepository[AuthenticationStateSnapshotModel, AuthenticationStateSnapshot],
    AuthenticationStateSnapshotRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuthenticationStateSnapshotModel)

    def to_domain(
        self, model: AuthenticationStateSnapshotModel
    ) -> AuthenticationStateSnapshot:
        return AuthenticationStateSnapshot(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            source_browser=model.source_browser,
            authentication_state=model.authentication_state,
            created_at=model.created_at,
        )

    def to_model(
        self, entity: AuthenticationStateSnapshot
    ) -> AuthenticationStateSnapshotModel:
        return AuthenticationStateSnapshotModel(
            id=entity.id,
            owner_id=entity.owner_id,
            name=entity.name,
            source_browser=entity.source_browser,
            authentication_state=entity.authentication_state,
            created_at=entity.created_at,
        )

    async def save(
        self, *, snapshot: AuthenticationStateSnapshot
    ) -> AuthenticationStateSnapshot:
        return await self.save_entity(snapshot)

    async def list_all(self) -> tuple[AuthenticationStateSnapshot, ...]:
        statement = select(AuthenticationStateSnapshotModel).order_by(
            AuthenticationStateSnapshotModel.created_at.desc()
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)


class SqlBrowserStateSnapshotRepository(
    SqlRepository[BrowserStateSnapshotModel, BrowserStateSnapshot],
    BrowserStateSnapshotRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BrowserStateSnapshotModel)

    def to_domain(self, model: BrowserStateSnapshotModel) -> BrowserStateSnapshot:
        return BrowserStateSnapshot(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            source_browser=model.source_browser,
            browser_state=model.browser_state,
            created_at=model.created_at,
        )

    def to_model(self, entity: BrowserStateSnapshot) -> BrowserStateSnapshotModel:
        return BrowserStateSnapshotModel(
            id=entity.id,
            owner_id=entity.owner_id,
            name=entity.name,
            source_browser=entity.source_browser,
            browser_state=entity.browser_state,
            created_at=entity.created_at,
        )

    async def save(self, *, snapshot: BrowserStateSnapshot) -> BrowserStateSnapshot:
        return await self.save_entity(snapshot)

    async def list_all(self) -> tuple[BrowserStateSnapshot, ...]:
        statement = select(BrowserStateSnapshotModel).order_by(
            BrowserStateSnapshotModel.created_at.desc()
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)
