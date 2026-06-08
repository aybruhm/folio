from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.entities.models import Trade
from domain.ports.outbound.repositories import ITradeRepository
from domain.value_objects.money import Currency, TradeType
from infrastructure.db.models import TradeModel


class TradeRepository(ITradeRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, trade: Trade) -> None:
        model = TradeModel(
            id=trade.id,
            portfolio_id=trade.portfolio_id,
            asset_id=trade.asset_id,
            ticker=trade.ticker,
            trade_type=trade.trade_type.value,
            trade_date=trade.trade_date,
            quantity=trade.quantity,
            price=trade.price,
            trade_currency=trade.trade_currency.value,
            fees=trade.fees,
            notes=trade.notes,
            source=trade.source,
            import_batch_id=trade.import_batch_id,
            market_data_provider=trade.market_data_provider,
            created_at=trade.created_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, trade_id: UUID) -> Optional[Trade]:
        model = await self.session.get(TradeModel, trade_id)
        return self._to_domain(model) if model else None

    async def list_by_portfolio(
        self,
        portfolio_id: UUID,
        ticker: Optional[str] = None,
        trade_type: Optional[TradeType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Trade], int]:
        query = select(TradeModel).where(TradeModel.portfolio_id == portfolio_id)

        if ticker:
            normalized = f"%{ticker.lower()}%"
            query = query.where(func.lower(TradeModel.ticker).like(normalized))
        if trade_type:
            query = query.where(TradeModel.trade_type == trade_type.value)
        if start_date:
            query = query.where(func.date(TradeModel.trade_date) >= start_date)
        if end_date:
            query = query.where(func.date(TradeModel.trade_date) <= end_date)

        count_result = await self.session.execute(
            select(func.count(TradeModel.id)).where(
                TradeModel.portfolio_id == portfolio_id
            )
            if not any([ticker, trade_type, start_date, end_date])
            else select(func.count(TradeModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        result = await self.session.execute(
            query.order_by(TradeModel.trade_date.desc()).offset(skip).limit(limit)
        )
        models = result.scalars().all()

        return [self._to_domain(m) for m in models], total

    async def list_by_asset(self, asset_id: UUID) -> List[Trade]:
        result = await self.session.execute(
            select(TradeModel)
            .where(TradeModel.asset_id == asset_id)
            .order_by(TradeModel.trade_date.asc())
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def list_all_tickers(self) -> List[str]:
        """Return distinct tickers from all trades."""
        from sqlalchemy import distinct

        result = await self.session.execute(select(distinct(TradeModel.ticker)))
        return [row[0] for row in result.all()]

    async def update(self, trade: Trade) -> None:
        model = await self.session.get(TradeModel, trade.id)
        if model:
            model.asset_id = trade.asset_id
            model.ticker = trade.ticker
            model.trade_type = trade.trade_type.value
            model.trade_date = trade.trade_date
            model.quantity = trade.quantity
            model.price = trade.price
            model.trade_currency = trade.trade_currency.value
            model.fees = trade.fees
            model.notes = trade.notes
            await self.session.flush()

    async def delete(self, trade_id: UUID) -> None:
        model = await self.session.get(TradeModel, trade_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def delete_batch(self, trade_ids: List[UUID]) -> int:
        result = await self.session.execute(
            select(TradeModel).where(TradeModel.id.in_(trade_ids))
        )
        models = result.scalars().all()
        deleted_count = len(models)
        for model in models:
            await self.session.delete(model)
        await self.session.flush()
        return deleted_count

    @staticmethod
    def _to_domain(model: TradeModel) -> Trade:
        return Trade(
            id=model.id,
            portfolio_id=model.portfolio_id,
            asset_id=model.asset_id,
            ticker=model.ticker,
            trade_type=TradeType(model.trade_type),
            trade_date=model.trade_date,
            quantity=int(model.quantity),
            price=int(model.price),
            trade_currency=Currency(model.trade_currency),
            fees=int(model.fees) if model.fees else 0,
            notes=model.notes,
            source=model.source,
            import_batch_id=model.import_batch_id,
            market_data_provider=model.market_data_provider,
            created_at=model.created_at,
        )
