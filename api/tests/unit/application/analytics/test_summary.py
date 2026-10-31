from datetime import date

import pytest

from application.analytics.summary import (
    convert_analytics,
    make_factor_lookup,
    merge_analytics,
    scale_analytics,
)
from domain.services.performance import PerformanceInputs, PerformanceService


def _analytics(current_value, total_invested, holdings, history, contributions):
    return {
        "current_value": current_value,
        "total_invested": total_invested,
        "total_gain_loss": current_value - total_invested,
        "allocation": [{"label": "stock", "value": current_value}],
        "sector_breakdown": [{"label": "Tech", "value": current_value}],
        "holdings": holdings,
        "performance_history": history,
        "contribution_history": contributions,
        "top_holdings": [],
    }


@pytest.mark.happy_path
def test_scale_analytics_scales_every_monetary_field():
    item = _analytics(
        100.0,
        80.0,
        [
            {
                "ticker": "AAPL",
                "current_price": 10.0,
                "market_value": 100.0,
                "cost_basis": 80.0,
                "total_invested": 80.0,
                "total_return": 20.0,
                "quantity": 10.0,
            }
        ],
        [{"name": "Jan 2026", "value": 100.0}],
        [{"name": "Jan 2026", "value": 80.0}],
    )

    scale_analytics(item, 1.5)

    assert item["current_value"] == 150.0
    assert item["total_invested"] == 120.0
    assert item["total_gain_loss"] == 30.0
    assert item["holdings"][0]["market_value"] == 150.0
    assert item["holdings"][0]["total_invested"] == 120.0
    assert item["holdings"][0]["quantity"] == 10.0
    assert item["performance_history"][0]["value"] == 150.0
    assert item["allocation"][0]["value"] == 150.0


@pytest.mark.happy_path
def test_merge_analytics_sums_series_and_merges_holdings():
    a = _analytics(
        300.0,
        200.0,
        [
            {"ticker": "AAPL", "name": "Apple", "market_value": 200.0},
            {"ticker": "MSFT", "name": "Microsoft", "market_value": 100.0},
        ],
        [{"name": "Dec 2025", "value": 250.0}, {"name": "Jan 2026", "value": 300.0}],
        [{"name": "Dec 2025", "value": 200.0}],
    )
    b = _analytics(
        100.0,
        100.0,
        [{"ticker": "AAPL", "name": "Apple", "market_value": 100.0}],
        [{"name": "Jan 2026", "value": 100.0}],
        [{"name": "Jan 2026", "value": 100.0}],
    )

    summary = merge_analytics([(b, None), (a, None)], "USD", "1y")

    assert summary["currency"] == "USD"
    assert summary["portfolio_count"] == 2
    assert summary["current_value"] == 400.0
    assert summary["total_invested"] == 300.0
    assert summary["total_gain_loss"] == 100.0
    assert summary["total_gain_loss_percent"] == pytest.approx(33.33)
    # Chronological across a year boundary, regardless of input order.
    assert summary["performance_history"] == [
        {"name": "Dec 2025", "value": 250.0},
        {"name": "Jan 2026", "value": 400.0},
    ]
    assert [p["name"] for p in summary["contribution_history"]] == [
        "Dec 2025",
        "Jan 2026",
    ]
    assert summary["allocation"] == [{"label": "stock", "value": 400.0}]
    assert summary["top_holdings"] == [
        {"ticker": "AAPL", "name": "Apple", "value": 300.0, "percent": 75.0},
        {"ticker": "MSFT", "name": "Microsoft", "value": 100.0, "percent": 25.0},
    ]


@pytest.mark.happy_path
def test_merge_analytics_computes_combined_return_not_an_average():
    # Small portfolio up 50%, large one down 10% over the same year.
    small = PerformanceInputs(
        beginning_value=0.0,
        ending_value=150.0,
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
        cash_flows=[(date(2025, 1, 1), 100.0)],
    )
    large = PerformanceInputs(
        beginning_value=0.0,
        ending_value=90_000.0,
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
        cash_flows=[(date(2025, 1, 1), 100_000.0)],
    )
    items = [
        (_analytics(150.0, 100.0, [], [], []), small),
        (_analytics(90_000.0, 100_000.0, [], [], []), large),
    ]

    summary = merge_analytics(items, "USD", "1y")

    expected = PerformanceService.summarize(PerformanceInputs.combine([small, large]))
    assert summary["twr"] == expected["twr"]
    assert summary["mwr"] == expected["mwr"]
    # About -9.95%, nowhere near the +20% a simple average would give.
    assert float(summary["twr"]) == pytest.approx(-9.95, abs=0.01)


@pytest.mark.edge_case
def test_merge_analytics_with_no_portfolios_returns_zeros():
    summary = merge_analytics([], "EUR", "all")

    assert summary["portfolio_count"] == 0
    assert summary["current_value"] == 0
    assert summary["twr"] == "0"
    assert summary["top_holdings"] == []
    assert summary["performance_history"] == []


@pytest.mark.happy_path
def test_performance_inputs_scale_and_combine():
    a = PerformanceInputs(
        beginning_value=10.0,
        ending_value=20.0,
        start_date=date(2025, 3, 1),
        end_date=date(2026, 1, 1),
        cash_flows=[(date(2025, 4, 1), 5.0)],
    )
    b = PerformanceInputs(
        beginning_value=0.0,
        ending_value=30.0,
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 2),
        cash_flows=[(date(2025, 2, 1), 25.0)],
    )

    scaled = a.scaled(2)
    combined = PerformanceInputs.combine([scaled, b])

    assert scaled.cash_flows == [(date(2025, 4, 1), 10.0)]
    assert combined.beginning_value == 20.0
    assert combined.ending_value == 70.0
    assert combined.start_date == date(2025, 1, 1)
    assert combined.end_date == date(2026, 1, 2)
    assert len(combined.cash_flows) == 2
    assert PerformanceInputs.combine([]) is None


@pytest.mark.happy_path
def test_make_factor_lookup_uses_last_rate_on_or_before_date():
    lookup = make_factor_lookup(
        [(date(2025, 1, 10), 2.0), (date(2025, 1, 1), 1.0), (date(2025, 1, 5), 0.0)]
    )

    assert lookup(date(2024, 12, 1)) == 1.0  # before the series: first rate
    assert lookup(date(2025, 1, 1)) == 1.0
    assert lookup(date(2025, 1, 9)) == 1.0  # zero rates are ignored
    assert lookup(date(2025, 1, 10)) == 2.0
    assert lookup(date(2026, 1, 1)) == 2.0
    assert make_factor_lookup([]) is None


@pytest.mark.happy_path
def test_convert_analytics_uses_dated_rates_for_the_past():
    item = _analytics(
        1000.0,
        800.0,
        [],
        [{"name": "Jan 2025", "value": 500.0}, {"name": "Feb 2025", "value": 1000.0}],
        [{"name": "Jan 2025", "value": 800.0}],
    )
    inputs = PerformanceInputs(
        beginning_value=0.0,
        ending_value=1000.0,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 2, 10),
        cash_flows=[(date(2025, 1, 15), 800.0)],
    )
    lookup = make_factor_lookup([(date(2025, 1, 1), 2.0), (date(2025, 2, 1), 1.0)])

    converted = convert_analytics(
        item, inputs, current_factor=0.5, factor_on=lookup, today=date(2025, 2, 10)
    )

    assert item["current_value"] == 500.0  # today's rate
    assert item["performance_history"] == [
        {"name": "Jan 2025", "value": 1000.0},  # January's rate
        {"name": "Feb 2025", "value": 500.0},  # last point: today's rate
    ]
    assert item["contribution_history"] == [{"name": "Jan 2025", "value": 1600.0}]
    assert converted.cash_flows == [(date(2025, 1, 15), 1600.0)]
    assert converted.ending_value == 500.0


@pytest.mark.edge_case
def test_convert_analytics_without_history_uses_todays_rate():
    item = _analytics(100.0, 80.0, [], [{"name": "Jan 2025", "value": 50.0}], [])
    inputs = PerformanceInputs(0.0, 100.0, date(2025, 1, 1), date(2025, 2, 1), [])

    converted = convert_analytics(item, inputs, current_factor=2.0)

    assert item["performance_history"] == [{"name": "Jan 2025", "value": 100.0}]
    assert converted.ending_value == 200.0
