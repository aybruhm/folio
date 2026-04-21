from uuid import UUID, uuid4
from typing import List, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal

from api.domain.entities.models import Trade, Asset
from api.domain.value_objects.money import Currency, TradeType, AssetMetadata
from api.domain.ports.inbound.use_cases import ITradeUseCase, CreateTradeRequest
from api.domain.ports.outbound.repositories import (
    ITradeRepository, IAssetRepository, IPortfolioRepository
)
from api.adapters.outbound.persistence.trade_repository import TradeRepository
from api.adapters.outbound.persistence.asset_repository import AssetRepository
from api.adapters.outbound.persistence.portfolio_repository import PortfolioRepository
from api.adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from sqlalchemy.ext.asyncio import AsyncSession

class TradeInteractor(ITradeUseCase):
    def __init__(self, session: AsyncSession):
        self.trade_repo: ITradeRepository = TradeRepository(session)
        self.asset_repo: IAssetRepository = AssetRepository(session)
        self.portfolio_repo: IPortfolioRepository = PortfolioRepository(session)
        self.yfinance = YFinanceAdapter()
    
    async def create_trade(self, request: CreateTradeRequest) -> UUID:
        portfolio = await self.portfolio_repo.get_by_id(request.portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {request.portfolio_id} not found")
        
        asset = await self.asset_repo.get_by_ticker(request.ticker)
        if not asset:
            metadata = await self.yfinance.get_asset_metadata(request.ticker)
            if not metadata:
                raise ValueError(f"Cannot find asset metadata for {request.ticker}")
            
            asset = Asset.from_metadata(request.ticker, metadata)
            await self.asset_repo.add(asset)
        
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
            filtered_trades = [t for t in filtered_trades if t.trade_date >= start_date]
        if end_date:
            filtered_trades = [t for t in filtered_trades if t.trade_date <= end_date]
        
        return [self._trade_to_dict(t) for t in filtered_trades], len(filtered_trades)
    
    async def update_trade(self, trade_id: UUID, request: CreateTradeRequest) -> None:
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        trade.quantity = request.quantity
        trade.price = request.price
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
            'quantity': str(trade.quantity),
            'price': str(trade.price),
            'trade_currency': trade.trade_currency.value,
            'fees': str(trade.fees),
            'notes': trade.notes,
            'created_at': trade.created_at.isoformat(),
        }
