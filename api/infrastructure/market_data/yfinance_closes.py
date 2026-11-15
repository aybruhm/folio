"""Read close prices out of yfinance history frames, skipping incomplete bars.

yfinance can return the latest bar with NaN prices but a real volume while the
day's data is still settling (seen with yfinance 1.7 / pandas 3.1). Converting
that NaN to an integer raised, and one bad row discarded the whole series.
"""

import pandas as pd


def valid_closes(data: pd.DataFrame | None = None) -> pd.Series:
    """The Close column without NaN or non-positive values."""
    if data is None or data.empty or "Close" not in data.columns:
        return pd.Series(dtype=float)
    closes = data["Close"]
    return closes[closes.notna() & (closes > 0)]  # type: ignore


def last_close(data: pd.DataFrame | None = None) -> float | None:
    """The most recent valid close, or None if there is none."""
    closes = valid_closes(data)
    return float(closes.iloc[-1]) if len(closes) else None
