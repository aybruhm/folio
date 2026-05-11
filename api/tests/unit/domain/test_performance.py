from datetime import date

import pytest

from domain.services.performance import (
    AllocationService,
    FIREService,
    PerformanceService,
)


@pytest.mark.smoke
def test_calculate_twr_without_cash_flows_uses_simple_return():
    result = PerformanceService.calculate_twr(
        beginning_value=100.0,
        ending_value=150.0,
        cash_flows=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == pytest.approx(0.5)


@pytest.mark.edge_case
def test_calculate_twr_returns_zero_when_beginning_value_is_zero():
    result = PerformanceService.calculate_twr(
        beginning_value=0.0,
        ending_value=150.0,
        cash_flows=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == 0.0


@pytest.mark.edge_case
def test_calculate_twr_returns_zero_for_zero_day_range():
    result = PerformanceService.calculate_twr(
        beginning_value=100.0,
        ending_value=110.0,
        cash_flows=[(date(2024, 1, 1), 10.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
    )

    assert result == 0.0


@pytest.mark.happy_path
def test_calculate_twr_accounts_for_weighted_cash_flows():
    result = PerformanceService.calculate_twr(
        beginning_value=100.0,
        ending_value=130.0,
        cash_flows=[(date(2024, 1, 6), 20.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 11),
    )

    assert result == pytest.approx(0.0909090909)


@pytest.mark.edge_case
def test_calculate_twr_returns_zero_when_denominator_is_zero():
    result = PerformanceService.calculate_twr(
        beginning_value=100.0,
        ending_value=150.0,
        cash_flows=[(date(2024, 1, 1), -100.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
    )

    assert result == 0.0


@pytest.mark.smoke
def test_calculate_mwr_without_cash_flows_uses_simple_return():
    result = PerformanceService.calculate_mwr(
        beginning_value=100.0,
        ending_value=125.0,
        cash_flows=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == pytest.approx(0.25)


@pytest.mark.edge_case
def test_calculate_mwr_returns_zero_when_beginning_value_is_zero():
    result = PerformanceService.calculate_mwr(
        beginning_value=0.0,
        ending_value=0.0,
        cash_flows=[],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == 0.0


@pytest.mark.smoke
def test_calculate_mwr_with_cash_flows_uses_solver_branch():
    result = PerformanceService.calculate_mwr(
        beginning_value=100.0,
        ending_value=121.0,
        cash_flows=[(date(2024, 1, 2), 0.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == pytest.approx(0.21, abs=0.02)


@pytest.mark.edge_case
def test_calculate_mwr_stops_when_npv_is_flat():
    result = PerformanceService.calculate_mwr(
        beginning_value=100.0,
        ending_value=40.0,
        cash_flows=[(date(2024, 1, 1), 50.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
    )

    assert result == pytest.approx(0.1)


@pytest.mark.grumpy_path
def test_calculate_mwr_breaks_on_solver_exception():
    class BrokenDate(date):
        def __sub__(self, other):  # pragma: no cover - exercised via exception path
            raise RuntimeError("boom")

    result = PerformanceService.calculate_mwr(
        beginning_value=100.0,
        ending_value=120.0,
        cash_flows=[(BrokenDate(2024, 1, 2), 10.0)],
        start_date=BrokenDate(2024, 1, 1),
        end_date=BrokenDate(2024, 12, 31),
    )

    assert result == pytest.approx(0.1)


@pytest.mark.happy_path
def test_group_by_attribute_aggregates_holding_values():
    holdings = [
        {"sector": "Technology", "market_value": 120.0},
        {"sector": "Technology", "market_value": 80.0},
        {"sector": "Finance", "market_value": 50.0},
    ]

    result = AllocationService.group_by_attribute(holdings, "sector")

    assert result == [
        {"name": "Technology", "value": 200.0, "weight_percent": 80.0},
        {"name": "Finance", "value": 50.0, "weight_percent": 20.0},
    ]


@pytest.mark.edge_case
def test_group_by_attribute_uses_unknown_bucket_for_missing_data():
    holdings = [{"market_value": 42.0}]

    result = AllocationService.group_by_attribute(holdings, "sector")

    assert result == [{"name": "Unknown", "value": 42.0, "weight_percent": 100.0}]


@pytest.mark.smoke
def test_calculate_future_value_handles_zero_rate():
    result = FIREService.calculate_future_value(
        present_value=1000.0,
        monthly_savings=100.0,
        annual_return=0.0,
        months=12,
    )

    assert result == 2200.0


@pytest.mark.smoke
def test_calculate_projection_reports_target_progress():
    result = FIREService.calculate_projection(
        current_value=50_000.0,
        target_value=100_000.0,
        monthly_savings=1_000.0,
        annual_return=0.06,
        target_months=12,
    )

    assert result["projected_value"] > 50_000.0
    assert result["progress_percent"] == 50.0
    assert "shortfall" in result


@pytest.mark.edge_case
def test_calculate_projection_zero_rate_reports_months_to_target():
    result = FIREService.calculate_projection(
        current_value=50_000.0,
        target_value=100_000.0,
        monthly_savings=1_000.0,
        annual_return=0.0,
        target_months=12,
    )

    assert result == {
        "months_to_target": 50,
        "projected_value": 62_000.0,
        "shortfall": 38_000.0,
        "progress_percent": 50.0,
    }


@pytest.mark.edge_case
def test_calculate_required_return_returns_zero_when_target_is_already_met():
    result = FIREService.calculate_required_return(
        current_value=100_000.0,
        target_value=80_000.0,
        monthly_savings=500.0,
        target_months=12,
    )

    assert result == 0.0


@pytest.mark.edge_case
def test_calculate_required_return_stops_when_derivative_is_zero():
    result = FIREService.calculate_required_return(
        current_value=10_000.0,
        target_value=20_000.0,
        monthly_savings=0.0,
        target_months=0,
    )

    assert result == pytest.approx(0.07)


@pytest.mark.grumpy_path
def test_calculate_required_return_returns_none_for_impossible_negative_savings():
    result = FIREService.calculate_required_return(
        current_value=0.0,
        target_value=100.0,
        monthly_savings=-10.0,
        target_months=12,
    )

    assert result is None


@pytest.mark.grumpy_path
def test_calculate_mwr_uses_fallback_when_rate_goes_out_of_bounds(monkeypatch):
    monkeypatch.setattr("builtins.min", lambda *args, **kwargs: 10.0)
    monkeypatch.setattr("builtins.max", lambda *args, **kwargs: 10.0)

    result = PerformanceService.calculate_mwr(
        beginning_value=100.0,
        ending_value=120.0,
        cash_flows=[(date(2024, 1, 2), 100.0)],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result == pytest.approx(0.2)


@pytest.mark.happy_path
def test_calculate_required_return_solves_positive_rate():
    result = FIREService.calculate_required_return(
        current_value=50_000.0,
        target_value=100_000.0,
        monthly_savings=1_000.0,
        target_months=12,
    )

    assert result is not None
    assert result > 0
