import calendar
from datetime import date

_TIMEFRAME_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "3y": 36, "5y": 60}


def _shift_months(d: date, months: int) -> date:
    index = d.year * 12 + (d.month - 1) - months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def timeframe_start(timeframe: str, today: date | None = None) -> date | None:
    """Valuation date the window opens on, or None for all-time.

    Flows strictly after this date fall inside the window; the portfolio's
    end-of-day value on it is the window's beginning value. "all" and unknown
    values mean all-time.
    """
    today = today or date.today()
    key = (timeframe or "").strip().lower()
    if key == "ytd":
        return date(today.year - 1, 12, 31)
    months = _TIMEFRAME_MONTHS.get(key)
    return _shift_months(today, months) if months else None
