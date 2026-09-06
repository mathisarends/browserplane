from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    SessionRepository,
)
from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    BrowserCheckpoint,
    Session,
    SessionStatus,
)
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.infrastructure.database.models import (
    AuthenticationProfileModel,
    BrowserCheckpointModel,
    SessionModel,
)
from backend.infrastructure.database.repository import SqlRepository


class SqlSessionRepository(SqlRepository[SessionModel, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SessionModel)

    def to_domain(self, model: SessionModel) -> Session:
        return Session(
            id=model.id,
            owner_id=model.owner_id,
            status=SessionStatus(model.status),
            created_at=model.created_at,
            expires_at=model.expires_at,
            browser_checkpoint_id=model.browser_checkpoint_id,
        )

    def to_model(self, entity: Session) -> SessionModel:
        return SessionModel(
            id=entity.id,
            owner_id=entity.owner_id,
            status=entity.status.value,
            created_at=entity.created_at,
            expires_at=entity.expires_at,
            browser_checkpoint_id=entity.browser_checkpoint_id,
        )

    async def get_by_id(self, *, session_id: UUID) -> Session | None:
        return await self.find_by_id(session_id)

    async def list(self) -> tuple[Session, ...]:
        statement = select(SessionModel).order_by(SessionModel.created_at.desc())
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)


class SqlAuthenticationProfileRepository(
    SqlRepository[AuthenticationProfileModel, AuthenticationProfile],
    AuthenticationProfileRepository,
):
    def __init__(
        self, session: AsyncSession, cipher: AuthenticationStateCipher
    ) -> None:
        super().__init__(session, AuthenticationProfileModel)
        self._cipher = cipher

    def to_domain(self, model: AuthenticationProfileModel) -> AuthenticationProfile:
        return AuthenticationProfile(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            authentication_state=self._cipher.decrypt(model.authentication_state),
            created_at=model.created_at,
        )

    def to_model(self, entity: AuthenticationProfile) -> AuthenticationProfileModel:
        return AuthenticationProfileModel(
            id=entity.id,
            owner_id=entity.owner_id,
            name=entity.name,
            authentication_state=self._cipher.encrypt(entity.authentication_state),
            created_at=entity.created_at,
        )

    async def get_by_id(self, *, profile_id: UUID) -> AuthenticationProfile | None:
        return await self.find_by_id(profile_id)

    async def list(self) -> tuple[AuthenticationProfile, ...]:
        statement = select(AuthenticationProfileModel).order_by(
            AuthenticationProfileModel.created_at.desc()
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)


class SqlBrowserCheckpointRepository(
    SqlRepository[BrowserCheckpointModel, BrowserCheckpoint],
    BrowserCheckpointRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BrowserCheckpointModel)

    def to_domain(self, model: BrowserCheckpointModel) -> BrowserCheckpoint:
        return BrowserCheckpoint(
            id=model.id,
            owner_id=model.owner_id,
            browser_state=model.browser_state,
            authentication_profile_id=model.authentication_profile_id,
            created_at=model.created_at,
        )

    def to_model(self, entity: BrowserCheckpoint) -> BrowserCheckpointModel:
        return BrowserCheckpointModel(
            id=entity.id,
            owner_id=entity.owner_id,
            browser_state=entity.browser_state,
            authentication_profile_id=entity.authentication_profile_id,
            created_at=entity.created_at,
        )

    async def get_by_id(self, *, checkpoint_id: UUID) -> BrowserCheckpoint | None:
        return await self.find_by_id(checkpoint_id)

    async def list(self) -> tuple[BrowserCheckpoint, ...]:
        statement = select(BrowserCheckpointModel).order_by(
            BrowserCheckpointModel.created_at.desc()
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)
