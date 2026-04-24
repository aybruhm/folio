from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from uuid import UUID
from datetime import date
from typing import List, Optional, Tuple

from domain.value_objects.money import Currency
from domain.ports.outbound.repositories import IPriceHistoryRepository, IFxRateRepository
from infrastructure.db.models import PriceHistoryModel, FxRateModel

class PriceHistoryRepository(IPriceHistoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, asset_id: UUID, date_val: date, close: int, currency: Currency
    ) -> None:
        model = PriceHistoryModel(
            asset_id=asset_id,
            date=date_val,
            close=close,
            currency=currency.value,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_history(
        self, asset_id: UUID, start: date, end: date
    ) -> List[Tuple[date, int]]:
        result = await self.session.execute(
            select(PriceHistoryModel)
            .where(
                and_(
                    PriceHistoryModel.asset_id == asset_id,
                    PriceHistoryModel.date >= start,
                    PriceHistoryModel.date <= end,
                )
            )
            .order_by(PriceHistoryModel.date.asc())
        )
        models = result.scalars().all()
        return [(m.date, int(m.close)) for m in models]

    async def get_latest(self, asset_id: UUID) -> Optional[Tuple[date, int]]:
        result = await self.session.execute(
            select(PriceHistoryModel)
            .where(PriceHistoryModel.asset_id == asset_id)
            .order_by(PriceHistoryModel.date.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return (model.date, int(model.close)) if model else None

class FxRateRepository(IFxRateRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, from_currency: Currency, to_currency: Currency, date_val: date, rate: int
    ) -> None:
        model = FxRateModel(
            from_currency=from_currency.value,
            to_currency=to_currency.value,
            date=date_val,
            rate=rate,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_rate(
        self, from_currency: Currency, to_currency: Currency, date_val: date
    ) -> Optional[int]:
        result = await self.session.execute(
            select(FxRateModel).where(
                and_(
                    FxRateModel.from_currency == from_currency.value,
                    FxRateModel.to_currency == to_currency.value,
                    FxRateModel.date == date_val,
                )
            )
        )
        model = result.scalar_one_or_none()
        return int(model.rate) if model else None

    async def get_latest_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[int]:
        result = await self.session.execute(
            select(FxRateModel)
            .where(
                and_(
                    FxRateModel.from_currency == from_currency.value,
                    FxRateModel.to_currency == to_currency.value,
                )
            )
            .order_by(FxRateModel.date.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return int(model.rate) if model else None
