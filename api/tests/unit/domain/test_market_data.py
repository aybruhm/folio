import pytest

from domain.services.market_data import normalize_provider


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (None, "yfinance"),
        ("", "yfinance"),
        (" YFINANCE ", "yfinance"),
        ("tiingo", "tiingo"),
        ("unknown", "yfinance"),
    ],
)
def test_normalize_provider(provider, expected):
    assert normalize_provider(provider) == expected
