from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete, select

from backend.features.browsers.application.models import (
    Browser,
    BrowserSlot,
    BrowserState,
)
from backend.features.browsers.application.ports import BrowserRepository
from backend.infrastructure.orm import BrowserModel
from backend.infrastructure.repository import SqlRepository


class SqlBrowserRepository(SqlRepository[BrowserModel, Browser], BrowserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BrowserModel)

    def to_domain(self, model: BrowserModel) -> Browser:
        return Browser(
            slot=BrowserSlot(
                id=model.id,
                browser_worker_url=model.browser_worker_url,
            ),
            created_at=model.created_at,
            state=BrowserState(model.state),
        )

    def to_model(self, entity: Browser) -> BrowserModel:
        return BrowserModel(
            id=entity.id,
            created_at=entity.created_at,
            browser_worker_url=entity.slot.browser_worker_url,
            state=entity.state,
        )

    async def save(self, *, browser: Browser) -> Browser:
        """
        Write a slot, overwriting whatever an earlier boot left behind.

        Provisioning hands out the same slot ids on every start, so seeding the
        pool is an upsert: the fresh row also resets the state, which is what we
        want, because the leases that referenced it are gone.
        """
        return await self.save_entity(browser)

    async def get_by_id(self, *, browser_id: UUID) -> Browser | None:
        return await self.find_by_id(browser_id)

    async def list_all(self) -> tuple[Browser, ...]:
        statement = select(BrowserModel).order_by(col(BrowserModel.created_at))
        models = (await self._session.scalars(statement)).all()
        return tuple(self.to_domain(model) for model in models)

    async def find_available(self) -> Browser | None:
        statement = (
            select(BrowserModel)
            .where(BrowserModel.state == BrowserState.READY)
            .order_by(col(BrowserModel.created_at))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        model = await self._session.scalar(statement)
        return self.to_domain(model) if model is not None else None

    async def delete_all(self) -> None:
        await self._session.execute(delete(BrowserModel))
        await self._session.flush()
