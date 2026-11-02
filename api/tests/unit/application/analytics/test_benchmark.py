from datetime import date

import pytest

from application.analytics.benchmark import (
    PERIODS,
    annualized,
    chain_returns,
    effective_start,
    normalize_currency,
    price_return_series,
    sample_dates,
)
from application.analytics.timeframe import timeframe_start

D = date


@pytest.mark.happy_path
def test_chain_returns_compounds_periods_without_flows():
    dates = [D(2026, 1, 1), D(2026, 1, 8), D(2026, 1, 15)]

    result = chain_returns(dates, [100.0, 110.0, 121.0], [])

    assert result == pytest.approx([0.0, 0.10, 0.21])


@pytest.mark.happy_path
def test_adding_money_is_not_counted_as_performance():
    # 100 grows to 200 only because 100 was added at the end of the second
    # period: no gain at all.
    dates = [D(2026, 1, 1), D(2026, 1, 8), D(2026, 1, 15)]

    result = chain_returns(dates, [100.0, 100.0, 200.0], [(D(2026, 1, 15), 100.0)])

    assert result == pytest.approx([0.0, 0.0, 0.0])


@pytest.mark.happy_path
def test_flow_in_the_middle_of_a_period_is_time_weighted():
    # 100 at the start, +100 added 3 days into a 7 day period, 220 at the end.
    # weight = 4/7, capital = 100 + 100*4/7, gain = 220 - 100 - 100 = 20
    dates = [D(2026, 1, 1), D(2026, 1, 8)]
    flows = [(D(2026, 1, 4), 100.0)]

    result = chain_returns(dates, [100.0, 220.0], flows)

    assert result[1] == pytest.approx(20 / (100 + 100 * 4 / 7))


@pytest.mark.happy_path
def test_starting_from_nothing_uses_the_first_deposit_as_capital():
    # First buy of 100 on day 1 of a 7 day period, worth 105 at the end:
    # weight 6/7, so the return is 5 / (100 * 6/7).
    dates = [D(2026, 1, 1), D(2026, 1, 8)]

    result = chain_returns(dates, [0.0, 105.0], [(D(2026, 1, 2), 100.0)])

    assert result[1] == pytest.approx(5 / (100 * 6 / 7))


@pytest.mark.edge_case
def test_withdrawals_are_negative_flows():
    # 200 falls to 120 after 100 is withdrawn: the remaining 20 is a 10% gain
    # on the 200 at work (withdrawn on the last day, so full weight 0).
    dates = [D(2026, 1, 1), D(2026, 1, 8)]

    result = chain_returns(dates, [200.0, 120.0], [(D(2026, 1, 8), -100.0)])

    assert result[1] == pytest.approx((120 - 200 + 100) / 200)


@pytest.mark.edge_case
def test_a_period_with_no_capital_counts_as_zero():
    dates = [D(2026, 1, 1), D(2026, 1, 8), D(2026, 1, 15)]

    # Empty, then a deposit on the last day of the second period (weight 0).
    result = chain_returns(dates, [0.0, 0.0, 50.0], [(D(2026, 1, 15), 50.0)])

    assert result == [0.0, 0.0, 0.0]


@pytest.mark.edge_case
def test_flows_outside_the_window_are_ignored():
    dates = [D(2026, 1, 8), D(2026, 1, 15)]
    flows = [(D(2026, 1, 8), 999.0), (D(2026, 2, 1), 999.0)]  # on the start day, after the end

    assert chain_returns(dates, [100.0, 110.0], flows) == pytest.approx([0.0, 0.10])


@pytest.mark.grumpy_path
def test_chain_returns_rejects_mismatched_lengths_and_handles_empty():
    with pytest.raises(ValueError):
        chain_returns([D(2026, 1, 1)], [1.0, 2.0], [])
    assert chain_returns([], [], []) == []


@pytest.mark.happy_path
def test_price_return_is_relative_to_the_first_date_and_carries_prices_forward():
    closes = [(D(2026, 1, 1), 100.0), (D(2026, 1, 2), 100.0), (D(2026, 1, 5), 110.0)]
    # Jan 3-4 is a weekend: the Jan 2 close carries forward.
    dates = [D(2026, 1, 1), D(2026, 1, 4), D(2026, 1, 6)]

    assert price_return_series(closes, dates) == pytest.approx([0.0, 0.0, 0.10])


@pytest.mark.edge_case
def test_price_return_handles_empty_and_bad_prices():
    assert price_return_series([], [D(2026, 1, 1)]) == []
    assert price_return_series([(D(2026, 1, 1), 0.0)], [D(2026, 1, 1)]) == []


@pytest.mark.happy_path
def test_short_windows_are_sampled_weekly_and_end_on_the_end_date():
    points = sample_dates(D(2026, 10, 1), D(2026, 11, 2))

    assert points[0] == D(2026, 10, 1)
    assert points[1] == D(2026, 10, 8)
    assert points[-1] == D(2026, 11, 2)
    assert all(b > a for a, b in zip(points, points[1:]))


@pytest.mark.happy_path
def test_long_windows_are_sampled_at_month_ends():
    points = sample_dates(D(2021, 11, 2), D(2026, 11, 2))

    assert points[:3] == [D(2021, 11, 2), D(2021, 11, 30), D(2021, 12, 31)]
    assert points[-2:] == [D(2026, 10, 31), D(2026, 11, 2)]
    assert len(points) == 62
    assert D(2024, 2, 29) in points  # leap year month end


@pytest.mark.edge_case
def test_sample_dates_when_the_window_is_empty():
    assert sample_dates(D(2026, 11, 2), D(2026, 11, 2)) == [D(2026, 11, 2)]
    assert sample_dates(D(2026, 11, 3), D(2026, 11, 2)) == [D(2026, 11, 3)]


@pytest.mark.happy_path
def test_annualized_only_for_windows_of_a_year_or_more():
    assert annualized(0.10, 365) == pytest.approx(0.10, abs=0.001)
    # Doubling over exactly 1095 days compounds at 2 ** (365.25 / 1095) - 1 a year.
    assert annualized(1.0, 1095) == pytest.approx(2 ** (365.25 / 1095) - 1)
    assert annualized(0.10, 200) is None
    assert annualized(-1.0, 1000) is None


@pytest.mark.happy_path
@pytest.mark.parametrize(
    "period_start,first_trade,bench_first,expected",
    [
        (D(2025, 1, 1), D(2020, 1, 1), D(2015, 1, 1), (D(2025, 1, 1), None)),
        (D(2025, 1, 1), D(2025, 6, 1), D(2015, 1, 1), (D(2025, 6, 1), "portfolio")),
        (D(2016, 1, 1), D(2010, 1, 1), D(2017, 3, 1), (D(2017, 3, 1), "benchmark")),
        (D(2016, 1, 1), D(2018, 1, 1), D(2020, 1, 1), (D(2020, 1, 1), "benchmark")),
        # No requested period (all time) starts at the first trade, which is not a limit.
        (None, D(2022, 5, 5), D(2015, 1, 1), (D(2022, 5, 5), None)),
    ],
)
def test_effective_start_uses_the_latest_of_the_three_dates(
    period_start, first_trade, bench_first, expected
):
    assert effective_start(period_start, first_trade, bench_first) == expected


@pytest.mark.edge_case
@pytest.mark.parametrize(
    "code,expected",
    [("GBp", "GBP"), ("GBX", "GBP"), ("ZAc", "ZAR"), ("usd", "USD"), ("EUR", "EUR"), ("", None), (None, None)],
)
def test_normalize_currency(code, expected):
    assert normalize_currency(code) == expected


@pytest.mark.happy_path
def test_every_benchmark_period_has_a_start_date():
    today = D(2026, 11, 2)
    starts = {p: timeframe_start(p, today) for p in PERIODS}

    assert all(starts.values())
    assert starts["ytd"] == D(2025, 12, 31)
    assert starts["6m"] == D(2026, 5, 2)
    assert starts["10y"] == D(2016, 11, 2)
