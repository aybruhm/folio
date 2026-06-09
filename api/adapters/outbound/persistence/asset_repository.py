from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.entities.models import Asset
from domain.ports.outbound.repositories import IAssetRepository
from domain.value_objects.money import AssetClass, Currency
from infrastructure.db.models import AssetModel


class AssetRepository(IAssetRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, asset: Asset) -> None:
        model = AssetModel(
            id=asset.id,
            ticker=asset.ticker,
            name=asset.name,
            asset_class=asset.asset_class.value,
            currency=asset.currency.value,
            exchange=asset.exchange,
            sector=asset.sector,
            industry=asset.industry,
            country=asset.country,
            isin=asset.isin,
            market_data_provider=asset.market_data_provider,
            created_at=asset.created_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_ticker(self, ticker: str) -> Optional[Asset]:
        result = await self.session.execute(
            select(AssetModel).where(
                func.upper(AssetModel.ticker) == func.upper(ticker)
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    async def get_by_id(self, asset_id: UUID) -> Optional[Asset]:
        model = await self.session.get(AssetModel, asset_id)
        return self._to_domain(model) if model else None

    async def update_classification(
        self,
        asset_id: UUID,
        asset_class: str,
        currency: str,
        market_data_provider: str = "yfinance",
    ) -> None:
        model = await self.session.get(AssetModel, asset_id)
        if model:
            model.asset_class = asset_class
            model.currency = currency
            model.market_data_provider = market_data_provider
            await self.session.flush()

    async def list_all(self) -> List[Asset]:
        result = await self.session.execute(select(AssetModel))
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def search_by_ticker(self, query: str, limit: int = 10) -> List[Asset]:
        search_query = f"%{query}%"
        result = await self.session.execute(
            select(AssetModel)
            .where(
                (func.upper(AssetModel.ticker).like(func.upper(search_query)))
                | (func.upper(AssetModel.name).like(func.upper(search_query)))
            )
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    @staticmethod
    def _to_domain(model: AssetModel) -> Asset:
        return Asset(
            id=model.id,
            ticker=model.ticker,
            name=model.name,
            asset_class=AssetClass(model.asset_class),
            currency=Currency(model.currency),
            exchange=model.exchange,
            sector=model.sector,
            industry=model.industry,
            country=model.country,
            isin=model.isin,
            market_data_provider=model.market_data_provider,
            created_at=model.created_at,
        )
