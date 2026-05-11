import pytest

from adapters.inbound.http import benchmark_fx_routes


class FakeYFinanceAdapter:
    def __init__(self):
        self.calls = []

    async def get_current_rate(self, from_currency, to_currency):
        self.calls.append((from_currency.value, to_currency.value))
        if to_currency.value == "JPY":
            return 15000
        return 100


@pytest.mark.integration
@pytest.mark.happy_path
def test_benchmark_routes(client):
    listed = client.get("/api/v1/benchmarks/")
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    created = client.post("/api/v1/benchmarks/", params={"ticker": "SPY", "name": "S&P 500"})
    assert created.status_code == 200
    assert created.json() == {"ticker": "SPY", "name": "S&P 500"}

    deleted = client.delete("/api/v1/benchmarks/00000000-0000-0000-0000-000000000001")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"


@pytest.mark.integration
@pytest.mark.edge_case
def test_fx_rates_route(client, monkeypatch):
    monkeypatch.setattr(benchmark_fx_routes, "YFinanceAdapter", lambda: FakeYFinanceAdapter())

    response = client.get("/api/v1/fx/rates", params=[("currencies", "GBP"), ("currencies", "JPY")])
    assert response.status_code == 200
    assert response.json()["USDGBP"] == "1.0"
    assert response.json()["USDJPY"] == "150.0"


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_fx_rates_route_handles_bad_currency(client, monkeypatch):
    class BrokenYFinance:
        async def get_current_rate(self, from_currency, to_currency):
            raise RuntimeError("boom")

    monkeypatch.setattr(benchmark_fx_routes, "YFinanceAdapter", lambda: BrokenYFinance())
    response = client.get("/api/v1/fx/rates", params=[("currencies", "GBP")])
    assert response.status_code == 200
    assert response.json()["USDGBP"] is None


@pytest.mark.integration
@pytest.mark.edge_case
def test_fx_rates_route_uses_default_currency_set(client, monkeypatch):
    monkeypatch.setattr(benchmark_fx_routes, "YFinanceAdapter", lambda: FakeYFinanceAdapter())
    response = client.get("/api/v1/fx/rates")
    assert response.status_code == 200
    assert set(response.json().keys()) == {"USDUSD", "USDGBP", "USDEUR", "USDJPY"}


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_fx_rates_route_outer_exception_returns_400(client, monkeypatch):
    class BrokenInitYFinance:
        def __init__(self):
            raise RuntimeError("init failed")

    monkeypatch.setattr(benchmark_fx_routes, "YFinanceAdapter", BrokenInitYFinance)
    response = client.get("/api/v1/fx/rates")
    assert response.status_code == 400
