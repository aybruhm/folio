from datetime import date

import pytest

from application.analytics.timeframe import timeframe_start


@pytest.mark.happy_path
@pytest.mark.parametrize(
    "timeframe,today,expected",
    [
        ("ytd", date(2026, 10, 30), date(2025, 12, 31)),
        ("3m", date(2026, 10, 30), date(2026, 7, 30)),
        ("1y", date(2026, 10, 30), date(2025, 10, 30)),
        ("3y", date(2026, 10, 30), date(2023, 10, 30)),
        ("5y", date(2026, 10, 30), date(2021, 10, 30)),
        ("1Y", date(2026, 10, 30), date(2025, 10, 30)),
    ],
)
def test_timeframe_start(timeframe, today, expected):
    assert timeframe_start(timeframe, today) == expected


@pytest.mark.edge_case
@pytest.mark.parametrize(
    "timeframe,today,expected",
    [
        ("3m", date(2026, 5, 31), date(2026, 2, 28)),
        ("1y", date(2024, 2, 29), date(2023, 2, 28)),
        ("3m", date(2026, 1, 15), date(2025, 10, 15)),
    ],
)
def test_timeframe_start_clamps_month_ends(timeframe, today, expected):
    assert timeframe_start(timeframe, today) == expected


@pytest.mark.edge_case
@pytest.mark.parametrize("timeframe", ["all", "", "bogus", None])
def test_timeframe_start_is_none_for_all_time(timeframe):
    assert timeframe_start(timeframe, date(2026, 10, 30)) is None
