from uuid import UUID
from typing import List, Optional
from datetime import date
from decimal import Decimal

from api.domain.entities.models import Holding
from api.domain.value_objects.money import Currency, Money
from api.domain.ports.inbound.use_cases import IAnalyticsUseCase
from api.domain.ports.outbound.repositories import (
    ITradeRepository, IAssetRepository, IPriceHistoryRepository, IFxRateRepository
)
from api.domain.services.performance import PerformanceService, AllocationService
from api.adapters.outbound.persistence.trade_repository import TradeRepository
from api.adapters.outbound.persistence.asset_repository import AssetRepository
from api.adapters.outbound.persistence.price_repository import PriceHistoryRepository, FxRateRepository
from api.adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from sqlalchemy.ext.asyncio import AsyncSession

class AnalyticsInteractor(IAnalyticsUseCase):
    def __init__(self, session: AsyncSession, portfolio_base_currency: Currency):
        self.trade_repo: ITradeRepository = TradeRepository(session)
        self.asset_repo: IAssetRepository = AssetRepository(session)
        self.price_repo: IPriceHistoryRepository = PriceHistoryRepository(session)
        self.fx_repo: IFxRateRepository = FxRateRepository(session)
        self.yfinance = YFinanceAdapter()
        self.base_currency = portfolio_base_currency
    
    async def get_holdings(
        self, portfolio_id: UUID, in_currency: Optional[Currency] = None
    ) -> List[dict]:
        display_currency = in_currency or self.base_currency
        trades, _ = await self.trade_repo.list_by_portfolio(portfolio_id, skip=0, limit=10000)
        
        holdings_by_asset = {}
        for trade in trades:
            if trade.ticker not in holdings_by_asset:
                holdings_by_asset[trade.ticker] = {
                    'asset_id': trade.asset_id,
                    'ticker': trade.ticker,
                    'quantity': Decimal('0'),
                    'cost_basis': Decimal('0'),
                    'trades': []
                }
            
            holding = holdings_by_asset[trade.ticker]
            holding['quantity'] += trade.quantity
            holding['cost_basis'] += trade.quantity * trade.price
            holding['trades'].append(trade)
        
        result = []
        for ticker, holding_data in holdings_by_asset.items():
            if holding_data['quantity'] <= 0:
                continue
            
            current_price_data = await self.yfinance.get_current_price(ticker)
            current_price = Money(current_price_data[1], holding_data['trades'][0].trade_currency)
            
            market_value = current_price.amount * holding_data['quantity']
            cost_basis = holding_data['cost_basis']
            total_return = market_value - cost_basis
            
            result.append({
                'asset_id': str(holding_data['asset_id']),
                'ticker': ticker,
                'quantity': str(holding_data['quantity']),
                'current_price': str(current_price.amount),
                'market_value': str(market_value),
                'cost_basis': str(cost_basis),
                'total_return': str(total_return),
                'total_return_percent': str((total_return / cost_basis * Decimal('100')) if cost_basis > 0 else Decimal('0')),
                'weight_percent': '0',
            })
        
        return result
    
    async def calculate_performance(
        self, portfolio_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> dict:
        trades, _ = await self.trade_repo.list_by_portfolio(portfolio_id, skip=0, limit=10000)
        
        if not trades:
            return {'twr': '0', 'mwr': '0'}
        
        cash_flows = [(t.trade_date, t.quantity * t.price) for t in trades if t.trade_type.value in ['buy', 'sell']]
        beginning_value = Decimal('0')
        ending_value = Decimal('0')
        
        actual_start = start_date or trades[0].trade_date
        actual_end = end_date or date.today()
        
        twr = PerformanceService.calculate_twr(
            beginning_value, ending_value, cash_flows, actual_start, actual_end
        )
        mwr = PerformanceService.calculate_mwr(
            beginning_value, ending_value, cash_flows, actual_start, actual_end
        )
        
        return {
            'twr': str(twr),
            'mwr': str(mwr),
            'start_date': actual_start.isoformat(),
            'end_date': actual_end.isoformat(),
        }
    
    async def get_allocation(
        self, portfolio_id: UUID, group_by: str = 'asset_class'
    ) -> List[dict]:
        holdings = await self.get_holdings(portfolio_id)
        
        allocation = AllocationService.group_by_attribute(
            [
                {
                    'asset_class': 'stock',
                    'sector': 'tech',
                    'industry': 'software',
                    'country': 'us',
                    'currency': 'usd',
                    'ticker': h['ticker'],
                    'market_value': Decimal(h['market_value'])
                }
                for h in holdings
            ],
            group_by
        )
        
        return [
            {
                'name': item['name'],
                'value': str(item['value']),
                'weight_percent': str(item['weight_percent']),
            }
            for item in allocation
        ]
    
    async def get_benchmark_comparison(
        self, portfolio_id: UUID, benchmark_tickers: List[str], start_date: Optional[date] = None
    ) -> dict:
        portfolio_perf = await self.calculate_performance(portfolio_id, start_date)
        
        benchmark_data = {}
        for ticker in benchmark_tickers:
            price_data = await self.yfinance.get_price_history(
                ticker, start_date or date.today().replace(year=date.today().year - 1), date.today()
            )
            benchmark_data[ticker] = {
                'name': ticker,
                'twr': '0',
                'alpha': '0',
            }
        
        return {
            'portfolio_twr': portfolio_perf['twr'],
            'benchmarks': benchmark_data,
        }
