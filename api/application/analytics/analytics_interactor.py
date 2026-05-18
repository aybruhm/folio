from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.market_data.ngnmarket_adapter import NgnMarketAdapter
from adapters.outbound.market_data.price_cache import PriceCache
from adapters.outbound.market_data.tiingo_adapter import TiingoAdapter
from adapters.outbound.market_data.tradingview_adapter import TradingviewAdapter
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
        self.tiingo = TiingoAdapter()
        self.ngnmarket = NgnMarketAdapter()
        self.tradingview = TradingviewAdapter()
        self.base_currency = portfolio_base_currency

    @staticmethod
    def _normalize_provider(provider: str | None) -> str:
        normalized = (provider or "yfinance").strip().lower()
        return (
            normalized
            if normalized in {"yfinance", "tiingo", "ngnmarket", "tradingview"}
            else "yfinance"
        )

    async def _get_price_from_provider(self, symbol: str, provider: str):
        selected = self._normalize_provider(provider)

        if selected == "tiingo":
            return await self.tiingo.get_current_price(symbol)

        if selected == "ngnmarket":
            chart = await self.ngnmarket.get_index_chart(symbol)
            if chart and chart.get("data"):
                last = chart["data"][-1]
                price = last.get("index_value")
                if price is not None:
                    return (date.today(), round(float(price) * 100))
            return (date.today(), 0)

        if selected == "tradingview":
            return await self.tradingview.get_current_price(symbol)

        return await self.yfinance.get_current_price(symbol)

    async def _resolve_price(
        self, asset_id: UUID, ticker: str, provider_hint: Optional[str] = None
    ) -> int:
        asset = await self.asset_repo.get_by_id(asset_id)
        symbol = ticker.upper()
        if asset and asset.asset_class.value == "crypto" and "-" not in symbol:
            symbol = f"{symbol}-{asset.currency.value}"

        provider = self._normalize_provider(
            provider_hint or (asset.market_data_provider if asset else "yfinance")
        )

        if provider == "tiingo" and "." in symbol:
            symbol = symbol.replace(".", "-")

        # Check Valkey cache before making any upstream calls.
        # A cached sentinel (price=0) means the ticker is unsupported
        # across all providers — skip the cascade entirely.
        cache = PriceCache()
        cached = await cache.get_price(symbol)
        if cached is not None:
            return cached[1]

        price_date, price = await self._get_price_from_provider(symbol, provider)

        if price == 0:
            # Cascade through every other provider in priority order
            fallback_order = ["tiingo", "tradingview", "ngnmarket", "yfinance"]
            for fallback in fallback_order:
                if fallback == provider:
                    continue
                price_date, price = await self._get_price_from_provider(
                    symbol, fallback
                )
                if price > 0:
                    break

        # Persist successful non-yfinance lookups too, so reloads don't
        # repeatedly hit upstream APIs (especially rate-limited providers).
        if price > 0:
            await cache.set_price(symbol, price_date or date.today(), price)
            return price

        # If all providers returned 0, the YFinanceAdapter will have
        # already cached a sentinel in get_current_price. If a
        # non-yfinance provider was used directly we cache one here.
        await cache.set_price(symbol, date.today(), 0)

        return price

    async def _get_fx_rate(self, from_ccy: str, to_ccy: str) -> int:
        """Return the ×100 rate for *from_ccy* → *to_ccy*.

        Checks the Valkey-backed PriceCache first; falls back to a
        direct Yahoo Finance lookup via the ``{from}{to}=X`` ticker.
        """
        if from_ccy == to_ccy:
            return 100

        # In-memory fallback cache (survives Valkey connection failures)
        if not hasattr(self, "_fx_rate_cache"):
            self._fx_rate_cache: dict[tuple[str, str], int] = {}

        mem_key = (from_ccy, to_ccy)
        if mem_key in self._fx_rate_cache:
            return self._fx_rate_cache[mem_key]

        # Check Valkey cache first
        cache = PriceCache()
        cached = await cache.get_fx_rate(from_ccy, to_ccy)
        if cached is not None:
            self._fx_rate_cache[mem_key] = cached
            return cached

        # Allow tests to inject a fake Ticker via _fx_ticker_factory
        factory = getattr(self, "_fx_ticker_factory", None)
        if factory is None:
            import yfinance as yf

            factory = yf.Ticker

        async def _fetch_one(frm: str, to: str) -> int:
            ticker = f"{frm}{to}=X"
            try:
                t = factory(ticker)
                data = t.history(period="1d")
                if data.empty:
                    return 0
                close = float(data["Close"].iloc[-1])
                return round(close * 100)
            except Exception:
                return 0

        # Try direct rate first
        rate = await _fetch_one(from_ccy, to_ccy)

        # If direct rate is zero (weak→strong), try inverse and use division
        if rate == 0:
            inv_rate = await _fetch_one(to_ccy, from_ccy)
            if inv_rate > 0:
                self._fx_rate_cache[mem_key] = -inv_rate
                await cache.set_fx_rate(from_ccy, to_ccy, -inv_rate)
                return -inv_rate

        self._fx_rate_cache[mem_key] = rate
        await cache.set_fx_rate(from_ccy, to_ccy, rate)
        return rate

    async def _convert_amount(self, amount: int, from_ccy: str, to_ccy: str) -> int:
        """Convert *amount* (×100 int) from *from_ccy* to *to_ccy*."""
        if from_ccy == to_ccy:
            return amount
        rate = await self._get_fx_rate(from_ccy, to_ccy)
        if rate == 0:
            return amount
        if rate < 0:
            # Inverse rate: amount * 100 / |rate|
            return (amount * 100) // -rate
        # Direct rate: amount * rate / 100
        return (amount * rate) // 100

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
            # The asset's native currency (what prices are quoted in)
            asset_currency = asset.currency if asset else self.base_currency
            provider_hint = None
            if holding_data["trades"]:
                provider_hint = getattr(
                    holding_data["trades"][-1], "market_data_provider", None
                )

            if not provider_hint and asset:
                provider_hint = getattr(asset, "market_data_provider", None)

            if is_cash:
                cash_balance_int = 0  # ×100 — built in base currency
                for trade in holding_data["trades"]:
                    trade_value_int = (trade.quantity * trade.price) // 10000
                    converted = await self._convert_amount(
                        trade_value_int,
                        trade.trade_currency.value,
                        self.base_currency.value,
                    )
                    if trade.trade_type.value == "buy":
                        cash_balance_int += converted
                    elif trade.trade_type.value == "sell":
                        cash_balance_int -= converted

                if cash_balance_int <= 0:
                    continue

                cost_basis_int = cash_balance_int
                market_value_int = cash_balance_int
                current_price_int = 100  # $1.00 equivalent
                total_return_int = 0
                quantity_int = cash_balance_int * 100  # at $1, quantity×10000
            else:
                # FIFO lots — costs converted to base currency per trade
                lots: list[
                    dict
                ] = []  # [{"qty": int(×10000), "cost": int(×100 in base ccy)}]
                for trade in holding_data["trades"]:
                    if trade.trade_type.value == "buy":
                        trade_cost_in_trade_ccy = (
                            trade.quantity * trade.price
                        ) // 10000 + trade.fees
                        trade_cost_in_base = await self._convert_amount(
                            trade_cost_in_trade_ccy,
                            trade.trade_currency.value,
                            self.base_currency.value,
                        )
                        lots.append({"qty": trade.quantity, "cost": trade_cost_in_base})
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

                # Cost basis is already in base currency
                cost_basis_int = sum(lot["cost"] for lot in lots)

                # Price comes from the provider in the asset's native currency
                price_in_asset_ccy = await self._resolve_price(
                    holding_data["asset_id"], ticker, provider_hint=provider_hint
                )
                if price_in_asset_ccy == 0:
                    latest = await self.price_repo.get_latest(holding_data["asset_id"])
                    if latest:
                        price_in_asset_ccy = latest[1]

                # Convert price from asset currency to base currency
                current_price_int = await self._convert_amount(
                    price_in_asset_ccy,
                    asset_currency.value,
                    self.base_currency.value,
                )

                # Market value = qty × price (in base currency)
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
                # Trade value in trade currency (×100 int)
                trade_value_int = (t.quantity * t.price) // 10000 + t.fees
                # Convert to base currency
                converted = await self._convert_amount(
                    trade_value_int,
                    t.trade_currency.value,
                    self.base_currency.value,
                )
                amount = converted / 100

                if t.trade_type.value == "buy":
                    cash_flows.append((trade_date, amount))
                else:
                    cash_flows.append((trade_date, -amount))

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
        ticker_asset_currency: dict = {}  # ticker -> Currency (asset's native currency)
        fallback_current_price: dict = {}
        latest_provider_for_ticker = {}
        for t in trades_sorted:
            latest_provider_for_ticker[t.ticker] = getattr(
                t, "market_data_provider", None
            )

        for asset_id, ticker in asset_ids.items():
            history = await self.price_repo.get_history(asset_id, first_date, end_date)
            price_map[ticker] = {dt: p for dt, p in history}

            asset = await self.asset_repo.get_by_id(asset_id)
            is_cash = bool(asset and asset.asset_class.value == "cash")
            ticker_is_cash[ticker] = is_cash
            ticker_asset_currency[ticker] = (
                asset.currency if asset else self.base_currency
            )

            provider_hint = latest_provider_for_ticker.get(ticker)
            if not provider_hint and asset:
                provider_hint = getattr(asset, "market_data_provider", None)
            # Last-resort fallback if there is no historical price at all.
            if is_cash:
                fallback_current_price[ticker] = 100  # $1.00 for cash instruments
            else:
                fallback_current_price[ticker] = await self._resolve_price(
                    asset_id, ticker, provider_hint=provider_hint
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
                asset_ccy = ticker_asset_currency.get(ticker, self.base_currency)

                if ticker_is_cash.get(ticker):
                    cash_balance_int = 0  # ×100 — built in base currency
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
                        converted = await self._convert_amount(
                            trade_value_int,
                            t.trade_currency.value,
                            self.base_currency.value,
                        )
                        if t.trade_type.value == "buy":
                            cash_balance_int += converted
                        elif t.trade_type.value == "sell":
                            cash_balance_int -= converted

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

                # Value in asset currency (×100 int), then convert to base
                value_in_asset_ccy = (qty_int * price_int) // 10000
                converted = await self._convert_amount(
                    value_in_asset_ccy,
                    asset_ccy.value,
                    self.base_currency.value,
                )
                portfolio_value += converted / 100

            label = sample_date.strftime("%b %Y")
            point = {"name": label, "value": round(portfolio_value, 2)}
            if result and result[-1]["name"] == label:
                result[-1] = point
            else:
                result.append(point)

        # Replace the last data point with the actual current holdings value
        # so the chart always ends at the real portfolio value, not a stale
        # historical price.
        holdings = await self.get_holdings(portfolio_id, self.base_currency)
        current_total = sum(h["market_value"] for h in holdings)
        if result:
            today_label = date.today().strftime("%b %Y")
            result[-1] = {"name": today_label, "value": round(current_total, 2)}

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
            # Trade value in trade currency (×100 int)
            trade_value_int = (t.quantity * t.price) // 10000
            # Convert to base currency
            converted = await self._convert_amount(
                trade_value_int,
                t.trade_currency.value,
                self.base_currency.value,
            )
            amount = converted / 100
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
