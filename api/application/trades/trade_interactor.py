from uuid import UUID, uuid4
from typing import List, Optional, Tuple
from datetime import date, datetime

from domain.entities.models import Trade, Asset
from domain.value_objects.money import Currency, TradeType, AssetClass, AssetMetadata
from domain.ports.inbound.use_cases import ITradeUseCase, CreateTradeRequest
from domain.ports.outbound.repositories import (
    ITradeRepository, IAssetRepository, IPortfolioRepository
)
from adapters.outbound.persistence.trade_repository import TradeRepository
from adapters.outbound.persistence.asset_repository import AssetRepository
from adapters.outbound.persistence.portfolio_repository import PortfolioRepository
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from sqlalchemy.ext.asyncio import AsyncSession

class TradeInteractor(ITradeUseCase):
    def __init__(self, session: AsyncSession):
        self.trade_repo: ITradeRepository = TradeRepository(session)
        self.asset_repo: IAssetRepository = AssetRepository(session)
        self.portfolio_repo: IPortfolioRepository = PortfolioRepository(session)
        self.yfinance = YFinanceAdapter()
    
    async def _resolve_asset(self, ticker: str, currency: Currency, asset_class: AssetClass | None) -> Asset:
        asset = await self.asset_repo.get_by_ticker(ticker)
        if not asset:
            if asset_class == AssetClass.CASH:
                asset = Asset(
                    id=uuid4(),
                    ticker=ticker,
                    name=ticker,
                    asset_class=AssetClass.CASH,
                    currency=currency,
                )
                await self.asset_repo.add(asset)
            else:
                metadata = await self.yfinance.get_asset_metadata(ticker, currency.value)
                if not metadata:
                    raise ValueError(f"Cannot find asset metadata for {ticker}")
                asset = Asset.from_metadata(ticker, metadata)
                await self.asset_repo.add(asset)
        elif asset_class != AssetClass.CASH:
            metadata = await self.yfinance.get_asset_metadata(ticker, currency.value)
            if metadata and (
                asset.asset_class.value != metadata.asset_class
                or asset.currency.value != metadata.currency.value
            ):
                await self.asset_repo.update_classification(
                    asset.id, metadata.asset_class, metadata.currency.value
                )
                asset = await self.asset_repo.get_by_ticker(ticker)
        return asset

    async def create_trade(self, request: CreateTradeRequest) -> UUID:
        portfolio = await self.portfolio_repo.get_by_id(request.portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {request.portfolio_id} not found")

        asset = await self._resolve_asset(request.ticker, request.trade_currency, request.asset_class)
        
        trade = Trade(
            id=uuid4(),
            portfolio_id=request.portfolio_id,
            asset_id=asset.id,
            ticker=request.ticker,
            trade_type=request.trade_type,
            trade_date=request.trade_date,
            quantity=request.quantity,
            price=request.price,
            trade_currency=request.trade_currency,
            fees=request.fees,
            created_at=datetime.utcnow(),
        )
        
        await self.trade_repo.add(trade)
        return trade.id
    
    async def get_trade(self, trade_id: UUID) -> dict:
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        return self._trade_to_dict(trade)
    
    async def list_trades(
        self,
        portfolio_id: Optional[UUID] = None,
        ticker: Optional[str] = None,
        trade_type: Optional[TradeType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[dict], int]:
        if portfolio_id:
            trades, total = await self.trade_repo.list_by_portfolio(portfolio_id, skip, limit)
        else:
            raise ValueError("portfolio_id required for listing trades")
        
        filtered_trades = trades
        if ticker:
            filtered_trades = [t for t in filtered_trades if t.ticker.upper() == ticker.upper()]
        if trade_type:
            filtered_trades = [t for t in filtered_trades if t.trade_type == trade_type]
        if start_date:
            filtered_trades = [t for t in filtered_trades if (t.trade_date.date() if hasattr(t.trade_date, 'date') else t.trade_date) >= start_date]
        if end_date:
            filtered_trades = [t for t in filtered_trades if (t.trade_date.date() if hasattr(t.trade_date, 'date') else t.trade_date) <= end_date]
        
        return [self._trade_to_dict(t) for t in filtered_trades], len(filtered_trades)
    
    async def update_trade(self, trade_id: UUID, request: CreateTradeRequest) -> None:
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")

        asset = await self._resolve_asset(request.ticker, request.trade_currency, request.asset_class)

        trade.asset_id = asset.id
        trade.ticker = request.ticker
        trade.trade_type = request.trade_type
        trade.trade_date = request.trade_date
        trade.quantity = request.quantity
        trade.price = request.price
        trade.trade_currency = request.trade_currency
        trade.fees = request.fees

        await self.trade_repo.update(trade)
    
    async def delete_trade(self, trade_id: UUID) -> None:
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        await self.trade_repo.delete(trade_id)
    
    @staticmethod
    def _trade_to_dict(trade: Trade) -> dict:
        return {
            'id': str(trade.id),
            'portfolio_id': str(trade.portfolio_id),
            'asset_id': str(trade.asset_id),
            'ticker': trade.ticker,
            'trade_type': trade.trade_type.value,
            'trade_date': trade.trade_date.isoformat(),
            'quantity': trade.quantity / 100,
            'price': trade.price / 100,
            'trade_currency': trade.trade_currency.value,
            'fees': trade.fees / 100,
            'notes': trade.notes,
            'created_at': trade.created_at.isoformat(),
        }
