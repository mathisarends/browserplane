from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from backend.features.leases.application.ports import LeaseStore
from backend.features.leases.domain.models import Lease, LeaseState
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
            generation=model.generation,
            state=LeaseState(model.state),
            last_renewed_at=model.last_renewed_at,
            expires_at=model.expires_at,
            reclaim_after=model.reclaim_after,
            created_at=model.created_at,
            reclaim_started_at=model.reclaim_started_at,
            released_at=model.released_at,
            release_reason=model.release_reason,
            cleanup_attempts=model.cleanup_attempts,
            cleanup_retry_at=model.cleanup_retry_at,
        )

    def to_model(self, entity: Lease) -> LeaseModel:
        return LeaseModel(
            id=entity.id,
            browser_id=entity.browser_id,
            owner_id=entity.owner_id,
            generation=entity.generation,
            state=entity.state.value,
            last_renewed_at=entity.last_renewed_at,
            expires_at=entity.expires_at,
            reclaim_after=entity.reclaim_after,
            created_at=entity.created_at,
            reclaim_started_at=entity.reclaim_started_at,
            released_at=entity.released_at,
            release_reason=entity.release_reason,
            cleanup_attempts=entity.cleanup_attempts,
            cleanup_retry_at=entity.cleanup_retry_at,
        )

    async def save(self, lease: Lease) -> Lease:
        return await super().save(lease)

    async def list_current(self) -> tuple[Lease, ...]:
        statement = (
            select(LeaseModel)
            .where(LeaseModel.state != LeaseState.RELEASED.value)
            .order_by(LeaseModel.created_at.desc())
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)

    async def get(self, lease_id: UUID, *, for_update: bool = False) -> Lease | None:
        statement = select(LeaseModel).where(LeaseModel.id == lease_id)
        if for_update:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return self.to_domain(model) if model is not None else None

    async def claim_due(
        self, now: datetime, *, limit: int, reason: str
    ) -> tuple[Lease, ...]:
        statement = (
            select(LeaseModel)
            .where(
                or_(
                    (LeaseModel.state == LeaseState.ACTIVE.value)
                    & (LeaseModel.reclaim_after <= now),
                    (LeaseModel.state == LeaseState.FAILED.value)
                    & (LeaseModel.cleanup_retry_at <= now),
                )
            )
            .order_by(col(LeaseModel.reclaim_after))
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        models = (await self._session.scalars(statement)).all()
        claimed: list[Lease] = []
        for model in models:
            lease = self.to_domain(model).begin_reclaim(now, reason=reason)
            claimed.append(await self.save(lease))
        return tuple(claimed)

    async def renew(
        self,
        lease_id: UUID,
        *,
        now: datetime,
        ttl: timedelta,
        grace_period: timedelta,
    ) -> Lease | None:
        lease = await self.get(lease_id, for_update=True)
        if lease is None:
            return None
        try:
            renewed = lease.renew(
                now,
                expires_at=now + ttl,
                reclaim_after=now + ttl + grace_period,
            )
        except ValueError:
            return None
        return await self.save(renewed)
