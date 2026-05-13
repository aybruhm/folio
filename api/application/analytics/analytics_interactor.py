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
        trades_sorted = sorted(
            trades,
            key=lambda t: (
                t.trade_date.date() if hasattr(t.trade_date, "date") else t.trade_date
            ),
        )

        for trade in trades_sorted:
            if trade.ticker not in holdings_by_asset:
                holdings_by_asset[trade.ticker] = {
                    "asset_id": trade.asset_id,
                    "ticker": trade.ticker,
                    "trades": [],
                }

            if trade.trade_type.value in ("buy", "sell"):
                holdings_by_asset[trade.ticker]["trades"].append(trade)

        result = []
        for ticker, holding_data in holdings_by_asset.items():
            asset = await self.asset_repo.get_by_id(holding_data["asset_id"])
            is_cash = bool(asset and asset.asset_class.value == "cash")

            if is_cash:
                # For cash instruments, quantity is often encoded as 1.0 per flow and
                # amount is carried in price. Net cash balance must be derived from
                # signed trade values, not unit counts.
                cash_balance_int = 0  # ×100
                for trade in holding_data["trades"]:
                    trade_value_int = (trade.quantity * trade.price) // 10000
                    if trade.trade_type.value == "buy":
                        cash_balance_int += trade_value_int
                    elif trade.trade_type.value == "sell":
                        cash_balance_int -= trade_value_int

                if cash_balance_int <= 0:
                    continue

                cost_basis_int = cash_balance_int
                market_value_int = cash_balance_int
                current_price_int = 100  # $1.00
                total_return_int = 0
                quantity_int = cash_balance_int * 100  # at $1, quantity×10000
            else:
                # FIFO lots for remaining open position.
                lots: list[dict] = []  # [{"qty": int(×10000), "cost": int(×100)}]
                for trade in holding_data["trades"]:
                    if trade.trade_type.value == "buy":
                        lot_cost_int = (
                            trade.quantity * trade.price
                        ) // 10000 + trade.fees
                        lots.append({"qty": trade.quantity, "cost": lot_cost_int})
                    elif trade.trade_type.value == "sell":
                        remaining_to_sell = trade.quantity
                        while remaining_to_sell > 0 and lots:
                            lot = lots[0]
                            take_qty = min(remaining_to_sell, lot["qty"])
                            take_cost = (lot["cost"] * take_qty) // lot["qty"]

                            lot["qty"] -= take_qty
                            lot["cost"] -= take_cost
                            remaining_to_sell -= take_qty

                            if lot["qty"] <= 0:
                                lots.pop(0)

                quantity_int = sum(lot["qty"] for lot in lots)
                if quantity_int <= 0:
                    continue

                cost_basis_int = sum(lot["cost"] for lot in lots)
                current_price_int = await self._resolve_price(
                    holding_data["asset_id"], ticker
                )
                if current_price_int == 0:
                    latest = await self.price_repo.get_latest(holding_data["asset_id"])
                    if latest:
                        current_price_int = latest[1]

                # quantity×10000 * price×100 → ÷10000 → ×100
                market_value_int = (quantity_int * current_price_int) // 10000
                total_return_int = market_value_int - cost_basis_int

            result.append(
                {
                    "asset_id": str(holding_data["asset_id"]),
                    "ticker": ticker,
                    "quantity": quantity_int / 10000,
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

        trades = sorted(
            trades,
            key=lambda t: (
                t.trade_date.date() if hasattr(t.trade_date, "date") else t.trade_date
            ),
        )

        cash_flows = []
        for t in trades:
            if t.trade_type.value in ["buy", "sell"]:
                trade_date = (
                    t.trade_date.date()
                    if hasattr(t.trade_date, "date")
                    else t.trade_date
                )
                amount = (t.quantity * t.price) // 10000 + t.fees

                # For this app's flow semantics:
                # - buy means cash enters the portfolio (contribution): positive flow
                # - sell means cash leaves the portfolio (withdrawal): negative flow
                if t.trade_type.value == "buy":
                    cash_flows.append((trade_date, amount / 100))
                else:
                    cash_flows.append((trade_date, -(amount / 100)))

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

        twr_percent = round(twr * 100, 2)
        mwr_percent = round(mwr * 100, 2)

        # Avoid returning "-0.0" in API responses.
        if abs(twr_percent) == 0:
            twr_percent = 0.0
        if abs(mwr_percent) == 0:
            mwr_percent = 0.0

        return {
            "twr": str(twr_percent),
            "mwr": str(mwr_percent),
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

        # Monthly sample points from first trade month-end to today
        sample_dates: List[date] = []
        month_start = first_date.replace(day=1)
        while month_start <= end_date:
            next_month_start = (
                month_start.replace(day=28) + timedelta(days=4)
            ).replace(day=1)
            month_end = next_month_start - timedelta(days=1)
            sample_dates.append(min(month_end, end_date))
            month_start = next_month_start

        if sample_dates[-1] != end_date:
            sample_dates.append(end_date)

        # Fetch stored price history for every asset in one pass
        asset_ids = {t.asset_id: t.ticker for t in trades_sorted}
        price_map: dict = {}  # ticker -> {date -> price_int (×100)}
        ticker_is_cash: dict = {}
        fallback_current_price: dict = {}

        for asset_id, ticker in asset_ids.items():
            history = await self.price_repo.get_history(asset_id, first_date, end_date)
            price_map[ticker] = {dt: p for dt, p in history}

            asset = await self.asset_repo.get_by_id(asset_id)
            is_cash = bool(asset and asset.asset_class.value == "cash")
            ticker_is_cash[ticker] = is_cash

            # Last-resort fallback if there is no historical price at all.
            if is_cash:
                fallback_current_price[ticker] = 100  # $1.00 for cash instruments
            else:
                fallback_current_price[ticker] = await self._resolve_price(
                    asset_id, ticker
                )

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
            last_trade_price: dict = {}

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
                    last_trade_price[t.ticker] = t.price
                elif t.trade_type.value == "sell":
                    positions[t.ticker] = positions.get(t.ticker, 0) - t.quantity
                    last_trade_price[t.ticker] = t.price

            portfolio_value = 0.0
            for ticker, qty_int in positions.items():
                if ticker_is_cash.get(ticker):
                    # Cash instruments in this app represent flows as quantity=1 and
                    # price=amount. Value should be the net signed amount, not unit
                    # count × $1.
                    cash_balance_int = 0  # ×100
                    for t in trades_sorted:
                        t_date = (
                            t.trade_date.date()
                            if hasattr(t.trade_date, "date")
                            else t.trade_date
                        )
                        if t_date > sample_date:
                            break
                        if t.ticker != ticker:
                            continue
                        trade_value_int = (t.quantity * t.price) // 10000
                        if t.trade_type.value == "buy":
                            cash_balance_int += trade_value_int
                        elif t.trade_type.value == "sell":
                            cash_balance_int -= trade_value_int

                    if cash_balance_int > 0:
                        portfolio_value += cash_balance_int / 100
                    continue

                if qty_int <= 0:
                    continue

                # Prefer historical price, then fallback to last known trade price,
                # then finally current market price.
                price_int = _price_on(ticker, sample_date)
                if price_int == 0:
                    price_int = int(last_trade_price.get(ticker, 0))
                if price_int == 0:
                    price_int = int(fallback_current_price.get(ticker, 0))

                # qty×10000 * price×100 → ÷1000000 → actual dollar value
                portfolio_value += (qty_int * price_int) / 1000000

            label = sample_date.strftime("%b %Y")
            point = {"name": label, "value": round(portfolio_value, 2)}
            if result and result[-1]["name"] == label:
                result[-1] = point
            else:
                result.append(point)

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
