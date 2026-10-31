import calendar
from bisect import bisect_right
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime

from domain.services.performance import PerformanceInputs, PerformanceService

TOP_HOLDINGS_LIMIT = 10

_SCALED_TOTALS = ("total_invested", "current_value", "total_gain_loss")
_SCALED_HOLDING_FIELDS = (
    "current_price",
    "market_value",
    "cost_basis",
    "total_invested",
    "total_return",
)
_SCALED_SERIES = (
    "performance_history",
    "contribution_history",
    "allocation",
    "top_holdings",
    "sector_breakdown",
)


def _scale(value, factor: float) -> float:
    return round(float(value) * factor, 2)


def scale_analytics(item: dict, factor: float) -> None:
    """Multiply every monetary field of *item* by *factor*, in place."""
    for key in _SCALED_TOTALS:
        if key in item:
            item[key] = _scale(item[key], factor)
    for holding in item.get("holdings", []):
        for key in _SCALED_HOLDING_FIELDS:
            if key in holding:
                holding[key] = _scale(holding[key], factor)
    for key in _SCALED_SERIES:
        for point in item.get(key, []):
            point["value"] = _scale(point["value"], factor)


FactorOn = Callable[[date], float]


def make_factor_lookup(series: Sequence[tuple[date, float]]) -> FactorOn | None:
    """FX factor on a date: the last one on or before it, or the first one
    for earlier dates. None when *series* has no usable points."""
    points = sorted((d, f) for d, f in series if f > 0)
    if not points:
        return None
    dates = [d for d, _ in points]

    def factor_on(day: date) -> float:
        return points[max(bisect_right(dates, day) - 1, 0)][1]

    return factor_on


def _month_end(label: str, today: date) -> date:
    first = datetime.strptime(label, "%b %Y").date()
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return min(last, today)


def convert_analytics(
    item: dict,
    inputs: PerformanceInputs | None,
    current_factor: float,
    factor_on: FactorOn | None = None,
    today: date | None = None,
) -> PerformanceInputs | None:
    """Convert *item* in place, and return *inputs*, in the display currency.

    Current figures use *current_factor*. With *factor_on*, past chart points,
    contributions and cash flows use the rate of their own date, so a
    depreciating currency doesn't rewrite history at today's rate.
    """
    today = today or date.today()
    history = item.get("performance_history", [])
    contributions = item.get("contribution_history", [])
    original = {id(p): float(p["value"]) for p in [*history, *contributions]}

    scale_analytics(item, current_factor)
    if factor_on is None:
        return inputs.scaled(current_factor) if inputs else None

    # The last chart point is today's holdings value, so it keeps today's rate.
    for point in [*history[:-1], *contributions]:
        rate = factor_on(_month_end(point["name"], today))
        point["value"] = round(original[id(point)] * rate, 2)

    return inputs.converted(factor_on, current_factor) if inputs else None


def _sum_by(points: Iterable[dict], key: str) -> list[dict]:
    totals: dict = {}
    for point in points:
        totals[point[key]] = totals.get(point[key], 0.0) + float(point["value"])
    return [{key: k, "value": round(v, 2)} for k, v in totals.items()]


def _by_month(points: list[dict]) -> list[dict]:
    return sorted(points, key=lambda p: datetime.strptime(p["name"], "%b %Y"))


def merge_analytics(
    items: list[tuple[dict, PerformanceInputs | None]],
    currency: str,
    timeframe: str,
) -> dict:
    """Combine per-portfolio analytics into one summary.

    TWR and MWR are recomputed from the combined cash flows and values, so
    they match a single portfolio holding everything, rather than averaging
    each portfolio's percentage.
    """
    analytics = [a for a, _ in items]

    current_value = sum(float(a.get("current_value", 0)) for a in analytics)
    total_invested = sum(float(a.get("total_invested", 0)) for a in analytics)
    total_gain_loss = current_value - total_invested

    holdings_by_ticker: dict = {}
    for a in analytics:
        for h in a.get("holdings", []):
            entry = holdings_by_ticker.setdefault(
                h["ticker"],
                {"ticker": h["ticker"], "name": h.get("name"), "value": 0.0},
            )
            entry["value"] += float(h.get("market_value", 0))
    top_holdings = sorted(
        holdings_by_ticker.values(), key=lambda h: h["value"], reverse=True
    )[:TOP_HOLDINGS_LIMIT]
    for h in top_holdings:
        h["name"] = h["name"] or h["ticker"]
        h["percent"] = (
            round(h["value"] / current_value * 100, 2) if current_value > 0 else 0.0
        )
        h["value"] = round(h["value"], 2)

    performance = PerformanceService.summarize(
        PerformanceInputs.combine([i for _, i in items if i is not None])
    )

    def series(key: str) -> list[dict]:
        return [p for a in analytics for p in a.get(key, [])]

    return {
        "currency": currency,
        "timeframe": timeframe,
        "portfolio_count": len(items),
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain_loss": round(total_gain_loss, 2),
        "total_gain_loss_percent": (
            round(total_gain_loss / total_invested * 100, 2)
            if total_invested > 0
            else 0.0
        ),
        "twr": performance["twr"],
        "mwr": performance["mwr"],
        "allocation": _sum_by(series("allocation"), "label"),
        "sector_breakdown": _sum_by(series("sector_breakdown"), "label"),
        "performance_history": _by_month(
            _sum_by(series("performance_history"), "name")
        ),
        "contribution_history": _by_month(
            _sum_by(series("contribution_history"), "name")
        ),
        "top_holdings": top_holdings,
    }
