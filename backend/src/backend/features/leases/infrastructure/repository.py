from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.features.leases.application.models import Lease
from backend.features.leases.application.ports import LeaseStore
from backend.infrastructure.database.models import LeaseModel
from backend.infrastructure.database.repository import SqlRepository


class SqlLeaseStore(SqlRepository[LeaseModel, Lease], LeaseStore):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LeaseModel)

    def to_domain(self, model: LeaseModel) -> Lease:
        return Lease(
            id=model.id,
            browser_id=model.browser_id,
            owner_id=model.owner_id,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )

    def to_model(self, entity: Lease) -> LeaseModel:
        return LeaseModel(
            id=entity.id,
            browser_id=entity.browser_id,
            owner_id=entity.owner_id,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
        )

    async def add(self, lease: Lease) -> None:
        await self.save_entity(lease)

    async def list(self) -> tuple[Lease, ...]:
        statement = select(LeaseModel).order_by(LeaseModel.created_at.desc())
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)

    async def get(self, lease_id: UUID) -> Lease | None:
        return await self.find_by_id(lease_id)

    async def remove(self, lease_id: UUID) -> None:
        await self.delete_entity(lease_id)
