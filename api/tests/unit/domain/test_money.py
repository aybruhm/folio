from datetime import date

import pytest

from domain.value_objects.money import Currency, DateRange


@pytest.mark.happy_path
@pytest.mark.parametrize("code", ["USD", "EUR", "JPY"])
def test_currency_validate_accepts_known_codes(code):
    assert Currency.validate(code) is True


@pytest.mark.grumpy_path
@pytest.mark.parametrize("code", ["usd", "ZZZ", "", "US"])
def test_currency_validate_rejects_unknown_codes(code):
    assert Currency.validate(code) is False


@pytest.mark.happy_path
def test_date_range_days_calculates_span():
    span = DateRange(start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert span.days() == 30


@pytest.mark.edge_case
def test_date_range_allows_same_start_and_end_date():
    span = DateRange(start=date(2024, 1, 1), end=date(2024, 1, 1))

    assert span.days() == 0


@pytest.mark.grumpy_path
def test_date_range_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="start date must be <= end date"):
        DateRange(start=date(2024, 2, 1), end=date(2024, 1, 1))


@pytest.mark.happy_path
def test_currency_validate_accepts_nigerian_naira_code():
    assert Currency.validate("NGN") is True
