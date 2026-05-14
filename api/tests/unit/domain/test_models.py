from datetime import datetime
from uuid import UUID, uuid4

import pytest

from domain.entities.models import Asset, FxRate, Holding, Portfolio, Trade
from domain.value_objects.money import AssetClass, AssetMetadata, Currency, TradeType


@pytest.mark.smoke
def test_asset_from_metadata_maps_domain_fields():
    metadata = AssetMetadata(
        ticker="AAPL",
        name="Apple Inc.",
        asset_class="stock",
        currency=Currency.USD,
        exchange="NASDAQ",
        sector="Technology",
        industry="Consumer Electronics",
        country="US",
        isin="US0378331005",
    )

    asset = Asset.from_metadata("AAPL", metadata)

    assert asset.ticker == "AAPL"
    assert asset.name == "Apple Inc."
    assert asset.asset_class == AssetClass.STOCK
    assert asset.currency == Currency.USD
    assert asset.exchange == "NASDAQ"
    assert asset.isin == "US0378331005"
    assert isinstance(asset.id, UUID)


@pytest.mark.edge_case
def test_asset_from_metadata_uses_ticker_when_name_missing_or_blank():
    missing_name = AssetMetadata(
        ticker="MPW",
        name="",
        asset_class="stock",
        currency=Currency.USD,
    )

    asset = Asset.from_metadata("MPW", missing_name)

    assert asset.name == "MPW"
    assert asset.market_data_provider == "yfinance"


@pytest.mark.edge_case
def test_asset_from_metadata_stores_explicit_market_data_provider():
    metadata = AssetMetadata(
        ticker="BRK.B",
        name="Berkshire Hathaway B",
        asset_class="stock",
        currency=Currency.USD,
    )

    asset = Asset.from_metadata("BRK.B", metadata, market_data_provider="tiingo")

    assert asset.market_data_provider == "tiingo"


@pytest.mark.parametrize(
    "quantity,price,fees,expected",
    [
        (100000, 18520, 495, 185695),
        (25000, 10000, 0, 25000),
    ],
)
@pytest.mark.happy_path
def test_trade_total_cost_scales_values(quantity, price, fees, expected):
    trade = Trade(
        id=uuid4(),
        portfolio_id=uuid4(),
        asset_id=uuid4(),
        ticker="AAPL",
        trade_type=TradeType.BUY,
        trade_date=datetime(2024, 1, 1, 9, 30),
        quantity=quantity,
        price=price,
        trade_currency=Currency.USD,
        fees=fees,
    )

    assert trade.total_cost() == expected


@pytest.mark.smoke
def test_holding_total_return_percent_uses_cost_basis():
    holding = Holding(
        asset_id=uuid4(),
        ticker="AAPL",
        quantity=100000,
        current_price=20000,
        cost_basis=150000,
        market_value=200000,
        total_return=50000,
        unrealised_pnl=50000,
    )

    assert holding.total_return_percent == pytest.approx(33.3333333333)


@pytest.mark.edge_case
def test_holding_total_return_percent_returns_zero_for_zero_cost_basis():
    holding = Holding(
        asset_id=uuid4(),
        ticker="CASH",
        quantity=100,
        current_price=100,
        cost_basis=0,
        market_value=10000,
        total_return=0,
        unrealised_pnl=0,
    )

    assert holding.total_return_percent == 0.0


@pytest.mark.happy_path
def test_portfolio_update_mutates_expected_fields():
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Growth",
        base_currency=Currency.USD,
        description="Old description",
        created_at=datetime(2024, 1, 1, 10, 0),
        updated_at=datetime(2024, 1, 1, 10, 0),
    )

    portfolio.update(name="Income", description="New description")

    assert portfolio.name == "Income"
    assert portfolio.description == "New description"
    assert portfolio.updated_at > datetime(2024, 1, 1, 10, 0)


@pytest.mark.happy_path
def test_fx_rate_convert_scales_amount():
    rate = FxRate(
        from_currency=Currency.USD,
        to_currency=Currency.EUR,
        date=datetime(2024, 1, 1).date(),
        rate=92,
    )

    assert rate.convert(10000) == 9200


def test_holding_weight_matches_market_value():
    holding = Holding(
        asset_id=uuid4(),
        ticker="AAPL",
        quantity=100000,
        current_price=20000,
        cost_basis=150000,
        market_value=200000,
        total_return=50000,
        unrealised_pnl=50000,
    )

    assert holding.weight == 200000


@pytest.mark.edge_case
def test_portfolio_update_no_values_keeps_description_and_only_updates_timestamp():
    initial_time = datetime(2024, 1, 1, 10, 0)
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Growth",
        base_currency=Currency.USD,
        description="Keep me",
        created_at=initial_time,
        updated_at=initial_time,
    )

    portfolio.update(name="", description=None)

    assert portfolio.name == "Growth"
    assert portfolio.description == "Keep me"
    assert portfolio.updated_at > initial_time
