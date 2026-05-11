from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from adapters.outbound.persistence.asset_repository import AssetRepository
from adapters.outbound.persistence.price_repository import (
    FxRateRepository,
    PriceHistoryRepository,
)
from adapters.outbound.persistence.trade_repository import TradeRepository
from domain.ports.inbound.use_cases import IAnalyticsUseCase
from domain.ports.outbound.repositories import (
    IAssetRepository,
    IFxRateRepository,
    IPriceHistoryRepository,
    ITradeRepository,
)
from domain.services.performance import AllocationService, PerformanceService
from domain.value_objects.money import Currency


class AnalyticsInteractor(IAnalyticsUseCase):
    def __init__(self, session: AsyncSession, portfolio_base_currency: Currency):
        self.trade_repo: ITradeRepository = TradeRepository(session)
        self.asset_repo: IAssetRepository = AssetRepository(session)
        self.price_repo: IPriceHistoryRepository = PriceHistoryRepository(session)
        self.fx_repo: IFxRateRepository = FxRateRepository(session)
        self.yfinance = YFinanceAdapter()
        self.base_currency = portfolio_base_currency

    async def _resolve_price(self, asset_id: UUID, ticker: str) -> int:
        asset = await self.asset_repo.get_by_id(asset_id)
        symbol = ticker.upper()
        if asset and asset.asset_class.value == "crypto" and "-" not in symbol:
            symbol = f"{symbol}-{asset.currency.value}"
        _, price = await self.yfinance.get_current_price(symbol)
        return price

    async def get_holdings(
        self, portfolio_id: UUID, in_currency: Optional[Currency] = None
    ) -> List[dict]:
        trades, _ = await self.trade_repo.list_by_portfolio(
            portfolio_id, skip=0, limit=10000
        )

        holdings_by_asset: dict = {}
        for trade in trades:
            if trade.ticker not in holdings_by_asset:
                holdings_by_asset[trade.ticker] = {
                    "asset_id": trade.asset_id,
                    "ticker": trade.ticker,
                    "quantity": 0,  # ×10000
                    "cost_basis": 0,  # ×100
                    "trades": [],
                }

            holding = holdings_by_asset[trade.ticker]
            holding["quantity"] += trade.quantity
            # quantity×10000 * price×100 → ÷10000 → ×100
            holding["cost_basis"] += (trade.quantity * trade.price) // 10000
            holding["trades"].append(trade)

        result = []
        for ticker, holding_data in holdings_by_asset.items():
            if holding_data["quantity"] <= 0:
                continue

            asset = await self.asset_repo.get_by_id(holding_data["asset_id"])
            is_cash = asset and asset.asset_class.value == "cash"
            cost_basis_int = holding_data["cost_basis"]

            if is_cash:
                # Cash is always worth face value — market value equals cost basis
                market_value_int = cost_basis_int
                current_price_int = (
                    (cost_basis_int * 10000) // holding_data["quantity"]
                    if holding_data["quantity"] > 0
                    else 0
                )
                total_return_int = 0
            else:
                current_price_int = await self._resolve_price(
                    holding_data["asset_id"], ticker
                )
                if current_price_int == 0:
                    latest = await self.price_repo.get_latest(holding_data["asset_id"])
                    if latest:
                        current_price_int = latest[1]

                # quantity×10000 * price×100 → ÷10000 → ×100
                market_value_int = (
                    holding_data["quantity"] * current_price_int
                ) // 10000
                total_return_int = market_value_int - cost_basis_int

            result.append(
                {
                    "asset_id": str(holding_data["asset_id"]),
                    "ticker": ticker,
                    "quantity": holding_data["quantity"] / 10000,
                    "current_price": current_price_int / 100,
                    "market_value": market_value_int / 100,
                    "cost_basis": cost_basis_int / 100,
                    "total_return": total_return_int / 100,
                    "total_return_percent": (
                        round(total_return_int / cost_basis_int * 100, 2)
                        if cost_basis_int > 0
                        else 0.0
                    ),
                    "weight_percent": "0",
                }
            )

        return result

    async def calculate_performance(
        self,
        portfolio_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        trades, _ = await self.trade_repo.list_by_portfolio(
            portfolio_id, skip=0, limit=10000
        )

        if not trades:
            return {"twr": "0", "mwr": "0"}

        cash_flows = []
        for t in trades:
            if t.trade_type.value in ["buy", "sell"]:
                trade_date = (
                    t.trade_date.date()
                    if hasattr(t.trade_date, "date")
                    else t.trade_date
                )
                # Divide by 10000 to get actual cents for PerformanceService
                cost = (t.quantity * t.price) // 10000 + t.fees
                if t.trade_type.value == "buy":
                    cash_flows.append((trade_date, -(cost / 100)))
                else:
                    cash_flows.append((trade_date, cost / 100))

        holdings = await self.get_holdings(portfolio_id)
        beginning_value = 0.0
        ending_value = sum(h["market_value"] for h in holdings)

        first_trade_date = trades[0].trade_date
        first_trade_date = (
            first_trade_date.date()
            if hasattr(first_trade_date, "date")
            else first_trade_date
        )
        actual_start = start_date or first_trade_date
        actual_end = end_date or date.today()

        twr = PerformanceService.calculate_twr(
            beginning_value,
            ending_value,
            cash_flows,
            actual_start,
            actual_end,
        )
        mwr = PerformanceService.calculate_mwr(
            beginning_value,
            ending_value,
            cash_flows,
            actual_start,
            actual_end,
        )

        return {
            "twr": str(round(twr * 100, 2)),
            "mwr": str(round(mwr * 100, 2)),
            "start_date": actual_start.isoformat(),
            "end_date": actual_end.isoformat(),
        }

    async def get_allocation(
        self, portfolio_id: UUID, group_by: str = "asset_class"
    ) -> List[dict]:
        holdings = await self.get_holdings(portfolio_id)

        asset_classes = {}
        for h in holdings:
            asset = await self.asset_repo.get_by_ticker(h["ticker"])
            asset_classes[h["ticker"]] = asset.asset_class.value if asset else "stock"

        allocation = AllocationService.group_by_attribute(
            [
                {
                    "asset_class": asset_classes[h["ticker"]],
                    "ticker": h["ticker"],
                    "market_value": h["market_value"],
                }
                for h in holdings
            ],
            group_by,
        )

        return [
            {
                "name": item["name"],
                "value": str(item["value"]),
                "weight_percent": str(item["weight_percent"]),
            }
            for item in allocation
        ]

    async def get_performance_history(
        self, portfolio_id: UUID, timeframe: str = "1y"
    ) -> List[dict]:
        trades, _ = await self.trade_repo.list_by_portfolio(
            portfolio_id, skip=0, limit=10000
        )
        if not trades:
            return []

        trades_sorted = sorted(
            trades,
            key=lambda t: (
                t.trade_date.date() if hasattr(t.trade_date, "date") else t.trade_date
            ),
        )
        first_date = (
            trades_sorted[0].trade_date.date()
            if hasattr(trades_sorted[0].trade_date, "date")
            else trades_sorted[0].trade_date
        )
        end_date = date.today()

        # Monthly sample points from first trade to today
        sample_dates: List[date] = []
        d = first_date.replace(day=1)
        while d <= end_date:
            sample_dates.append(d)
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        if sample_dates[-1] != end_date:
            sample_dates.append(end_date)

        # Fetch stored price history for every asset in one pass
        asset_ids = {t.asset_id: t.ticker for t in trades_sorted}
        price_map: dict = {}  # ticker -> {date -> price_int (×100)}
        for asset_id, ticker in asset_ids.items():
            history = await self.price_repo.get_history(asset_id, first_date, end_date)
            price_map[ticker] = {dt: p for dt, p in history}

        def _price_on(ticker: str, target: date) -> int:
            ph = price_map.get(ticker, {})
            d = target
            while d >= first_date:
                if d in ph:
                    return ph[d]
                d -= timedelta(days=1)
            return 0

        result = []
        for sample_date in sample_dates:
            positions: dict = {}
            for t in trades_sorted:
                t_date = (
                    t.trade_date.date()
                    if hasattr(t.trade_date, "date")
                    else t.trade_date
                )
                if t_date > sample_date:
                    break
                if t.trade_type.value == "buy":
                    positions[t.ticker] = positions.get(t.ticker, 0) + t.quantity
                elif t.trade_type.value == "sell":
                    positions[t.ticker] = positions.get(t.ticker, 0) - t.quantity

            portfolio_value = 0.0
            for ticker, qty_int in positions.items():
                if qty_int <= 0:
                    continue
                price_int = _price_on(ticker, sample_date)
                # qty×10000 * price×100 → ÷1000000 → actual dollar value
                portfolio_value += (qty_int * price_int) / 1000000

            result.append(
                {
                    "name": sample_date.strftime("%b %Y"),
                    "value": round(portfolio_value, 2),
                }
            )

        return result

    async def get_contribution_history(self, portfolio_id: UUID) -> List[dict]:
        trades, _ = await self.trade_repo.list_by_portfolio(
            portfolio_id, skip=0, limit=10000
        )
        if not trades:
            return []

        monthly: dict = {}
        for t in trades:
            if t.trade_type.value not in ("buy", "sell"):
                continue
            t_date = (
                t.trade_date.date() if hasattr(t.trade_date, "date") else t.trade_date
            )
            key = t_date.strftime("%b %Y")
            amount = (t.quantity * t.price) // 10000 / 100
            if t.trade_type.value == "buy":
                monthly[key] = monthly.get(key, 0.0) + amount
            else:
                monthly[key] = monthly.get(key, 0.0) - amount

        # Sort chronologically
        from datetime import datetime

        return sorted(
            [{"name": k, "value": round(v, 2)} for k, v in monthly.items()],
            key=lambda x: datetime.strptime(x["name"], "%b %Y"),
        )

    async def get_sector_breakdown(self, portfolio_id: UUID) -> List[dict]:
        holdings = await self.get_holdings(portfolio_id)

        sectors: dict = {}
        for h in holdings:
            asset = await self.asset_repo.get_by_ticker(h["ticker"])
            sector = (asset.sector or "Unknown") if asset else "Unknown"
            sectors[sector] = sectors.get(sector, 0.0) + h["market_value"]

        total = sum(sectors.values())
        return [
            {"label": s, "value": round(v, 2)}
            for s, v in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        ]

    async def get_benchmark_comparison(
        self,
        portfolio_id: UUID,
        benchmark_tickers: List[str],
        start_date: Optional[date] = None,
    ) -> dict:
        portfolio_perf = await self.calculate_performance(portfolio_id, start_date)

        benchmark_data = {}
        for ticker in benchmark_tickers:
            await self.yfinance.get_price_history(
                ticker,
                start_date or date.today().replace(year=date.today().year - 1),
                date.today(),
            )
            benchmark_data[ticker] = {
                "name": ticker,
                "twr": "0",
                "alpha": "0",
            }

        return {
            "portfolio_twr": portfolio_perf["twr"],
            "benchmarks": benchmark_data,
        }
