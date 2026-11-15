from collections.abc import Callable
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.market_data.yfinance_closes import last_close, valid_closes
from application.analytics.analytics_interactor import AnalyticsInteractor
from application.analytics.summary import make_factor_lookup
from application.analytics.timeframe import timeframe_start
from domain.services.performance import PerformanceInputs, PerformanceService
from domain.value_objects.money import Currency


async def fetch_fx_factor(from_ccy: str, to_ccy: str) -> float:
    if from_ccy == to_ccy:
        return 1.0
    import yfinance as yf

    def latest_close(ticker: str) -> float:
        try:
            return last_close(yf.Ticker(ticker).history(period="1d")) or 0.0
        except Exception:
            return 0.0

    direct = latest_close(f"{from_ccy}{to_ccy}=X")
    if direct > 0:
        return direct
    inverse = latest_close(f"{to_ccy}{from_ccy}=X")
    return 1 / inverse if inverse > 0 else 0.0


async def fetch_fx_factor_history(
    from_ccy: str, to_ccy: str, start: date, end: date
) -> list[tuple[date, float]]:
    if from_ccy == to_ccy:
        return []
    import yfinance as yf

    def closes(ticker: str) -> list[tuple[date, float]]:
        try:
            data = yf.Ticker(ticker).history(start=start, end=end + timedelta(days=1))
            return [(idx.date(), float(c)) for idx, c in valid_closes(data).items()]
        except Exception:
            return []

    direct = closes(f"{from_ccy}{to_ccy}=X")
    if direct:
        return direct
    return [(d, 1 / c) for d, c in closes(f"{to_ccy}{from_ccy}=X")]


async def build_portfolio_analytics(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
    base_currency: Currency = Currency.USD,
    interactor_factory: Callable = AnalyticsInteractor,
) -> dict:
    analytics, _ = await portfolio_analytics_with_inputs(
        session, portfolio_id, timeframe, base_currency, interactor_factory
    )
    return analytics


async def portfolio_analytics_with_inputs(
    session: AsyncSession,
    portfolio_id: UUID,
    timeframe: str,
    base_currency: Currency = Currency.USD,
    interactor_factory: Callable = AnalyticsInteractor,
) -> tuple[dict, PerformanceInputs | None]:
    interactor = interactor_factory(session, base_currency)
    start_date = timeframe_start(timeframe)

    holdings = await interactor.get_holdings(portfolio_id, base_currency)
    performance_inputs = await interactor.get_performance_inputs(
        portfolio_id, start_date
    )
    performance = PerformanceService.summarize(performance_inputs)
    allocation_raw = await interactor.get_allocation(portfolio_id)
    performance_history = await interactor.get_performance_history(
        portfolio_id, timeframe
    )
    contribution_history = await interactor.get_contribution_history(
        portfolio_id, start_date
    )
    sector_breakdown = await interactor.get_sector_breakdown(portfolio_id)

    current_value = sum(float(h["market_value"]) for h in holdings)
    total_invested = sum(float(h["cost_basis"]) for h in holdings)
    total_gain_loss = current_value - total_invested
    total_gain_loss_percent = (
        (total_gain_loss / total_invested * 100) if total_invested > 0 else 0.0
    )

    allocation = [
        {"label": a["name"], "value": float(a["value"])} for a in allocation_raw
    ]

    holdings_with_weight = [
        {
            **h,
            "weight_percent": (
                round((float(h["market_value"]) / current_value) * 100, 2)
                if current_value > 0
                else 0.0
            ),
        }
        for h in holdings
    ]

    top_holdings_by_weight = sorted(
        holdings_with_weight,
        key=lambda h: float(h.get("weight_percent", 0)),
        reverse=True,
    )[:10]

    return {
        "portfolio_id": str(portfolio_id),
        "total_invested": float(total_invested),
        "current_value": float(current_value),
        "total_gain_loss": float(total_gain_loss),
        "holdings": holdings_with_weight,
        "total_gain_loss_percent": float(round(total_gain_loss_percent, 2)),
        "twr": performance.get("twr", "0"),
        "mwr": performance.get("mwr", "0"),
        "allocation": allocation,
        "top_holdings": [
            {
                "ticker": h.get("ticker"),
                "name": h.get("name", h.get("ticker")),
                "value": float(h.get("market_value", 0)),
                "percent": float(h.get("weight_percent", 0)),
            }
            for h in top_holdings_by_weight
        ],
        "performance_history": performance_history,
        "contribution_history": contribution_history,
        "sector_breakdown": sector_breakdown,
        "timeframe": timeframe,
    }, performance_inputs


async def dated_factor(
    from_ccy: Currency, to_ccy: Currency, start: date, end: date
) -> Callable[[date], float] | None:
    if from_ccy == to_ccy:
        return lambda _day: 1.0
    current = await fetch_fx_factor(from_ccy.value, to_ccy.value)
    if not current:
        return None
    lookup = make_factor_lookup(
        await fetch_fx_factor_history(
            from_ccy.value, to_ccy.value, start - timedelta(days=7), end
        )
    )
    return lookup or (lambda _day: current)
