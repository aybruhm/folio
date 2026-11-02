import calendar
from bisect import bisect_right
from datetime import date, timedelta

# Windows up to this long are sampled weekly; longer ones monthly.
WEEKLY_UP_TO_DAYS = 400
PERIODS = ("ytd", "3m", "6m", "1y", "3y", "5y", "10y")

# yfinance quotes some London and Johannesburg listings in pence/cents.
_MINOR_UNITS = {"GBp": "GBP", "GBX": "GBP", "ZAc": "ZAR", "ZAC": "ZAR", "ILA": "ILS"}


def normalize_currency(code: str | None) -> str | None:
    """ISO code for a quote currency; pence and cents map to their major unit.
    A constant scale doesn't change a return, only the currency does."""
    if not code:
        return None
    return _MINOR_UNITS.get(code, code.upper())


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def sample_dates(start: date, end: date) -> list[date]:
    """`start`, then weekly points (windows up to ~13 months) or month-ends
    (longer windows), always finishing on `end`."""
    if end <= start:
        return [start]
    points = [start]
    if (end - start).days <= WEEKLY_UP_TO_DAYS:
        current = start + timedelta(days=7)
        while current < end:
            points.append(current)
            current += timedelta(days=7)
    else:
        year, month = start.year, start.month
        while True:
            point = _month_end(year, month)
            if point >= end:
                break
            if point > start:
                points.append(point)
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    points.append(end)
    return points


def chain_returns(
    dates: list[date],
    values: list[float],
    flows: list[tuple[date, float]],
) -> list[float]:
    """Cumulative return at each date, 0.0 on the first.

    `values[i]` is the portfolio value at the end of `dates[i]`. `flows` are
    (date, amount) with money in positive (a buy) and money out negative (a
    sell); a flow counts in the period (previous date, date] that contains it.
    Each period's return is (end - start - flows) / (start + time-weighted
    flows); a period with no capital at work counts as 0.
    """
    if len(dates) != len(values):
        raise ValueError("dates and values must have the same length")
    if not dates:
        return []

    cumulative = 1.0
    result = [0.0]
    for i in range(1, len(dates)):
        period_start, period_end = dates[i - 1], dates[i]
        span = (period_end - period_start).days
        net_flow = 0.0
        weighted_flow = 0.0
        for flow_date, amount in flows:
            if period_start < flow_date <= period_end:
                net_flow += amount
                weight = (period_end - flow_date).days / span if span else 0.0
                weighted_flow += amount * weight
        capital = values[i - 1] + weighted_flow
        period_return = (
            (values[i] - values[i - 1] - net_flow) / capital if capital > 0 else 0.0
        )
        cumulative *= 1.0 + period_return
        result.append(cumulative - 1.0)
    return result


def price_return_series(
    closes: list[tuple[date, float]],
    dates: list[date],
) -> list[float]:
    """Cumulative price return at each date, 0.0 on the first.

    Uses the last close on or before each date, so weekends and holidays carry
    the previous close forward. `closes` must be sorted by date.
    """
    if not closes or not dates:
        return []
    close_dates = [d for d, _ in closes]

    def price_on(day: date) -> float:
        index = bisect_right(close_dates, day) - 1
        return closes[max(index, 0)][1]

    base = price_on(dates[0])
    if base <= 0:
        return []
    return [price_on(d) / base - 1.0 for d in dates]


def annualized(total_return: float, days: int) -> float | None:
    """Compound annual rate for a return earned over `days`. None for windows
    under a year, where annualizing only exaggerates a short run."""
    if days < 365 or total_return <= -1.0:
        return None
    return (1.0 + total_return) ** (365.25 / days) - 1.0


def effective_start(
    period_start: date | None,
    first_trade: date,
    benchmark_first: date,
) -> tuple[date, str | None]:
    """Where the comparison really starts, and what limited it ("portfolio",
    "benchmark" or None when the requested period fits).

    Both lines must cover the same days: a 5-year request for a portfolio that
    is 8 months old compares 8 months, not 5 years of the index against 8 of
    the portfolio.
    """
    start = period_start or first_trade
    limit = None
    if first_trade > start:
        start, limit = first_trade, "portfolio"
    if benchmark_first > start:
        start, limit = benchmark_first, "benchmark"
    return start, limit
