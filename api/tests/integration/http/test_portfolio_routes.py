from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from adapters.inbound.http import portfolio_routes
from application.analytics.timeframe import timeframe_start
from domain.services.performance import PerformanceInputs, PerformanceService
from domain.value_objects.money import Currency


class FakePortfolioInteractor:
    def __init__(self, owner_id: UUID, mode: str = "happy"):
        self.owner_id = owner_id
        self.mode = mode
        self.portfolio_id = uuid4()
        self.last_create = None
        self.last_update = None
        self.deleted = []
        self.last_list_include_archived = None
        self.archived_calls = []

    async def list_portfolios(self, user_id, include_archived=False):
        self.last_list_include_archived = include_archived
        return [
            {
                "id": str(self.portfolio_id),
                "user_id": str(user_id),
                "name": "Core",
                "base_currency": "USD",
                "description": "Core portfolio",
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-02T10:00:00",
            }
        ]

    async def create_portfolio(self, request, user_id):
        if self.mode == "create-error":
            raise RuntimeError("create failed")
        self.last_create = (request, user_id)
        return self.portfolio_id

    async def get_portfolio(self, portfolio_id):
        if self.mode == "missing":
            raise ValueError(f"Portfolio {portfolio_id} not found")
        return {
            "id": str(portfolio_id),
            "user_id": str(self.owner_id if self.mode != "wrong-owner" else uuid4()),
            "name": "Core",
            "base_currency": "USD",
            "description": "Core portfolio",
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-02T10:00:00",
        }

    async def update_portfolio(self, portfolio_id, name=None, description=None):
        if self.mode == "missing":
            raise ValueError(f"Portfolio {portfolio_id} not found")
        if self.mode == "update-error":
            raise RuntimeError("update failed")
        self.last_update = (portfolio_id, name, description)

    async def delete_portfolio(self, portfolio_id):
        if self.mode == "missing":
            raise ValueError(f"Portfolio {portfolio_id} not found")
        if self.mode == "delete-error":
            raise RuntimeError("delete failed")
        self.deleted.append(portfolio_id)

    async def set_archived(self, portfolio_id, archived):
        if self.mode == "archive-error":
            raise RuntimeError("archive failed")
        self.archived_calls.append((portfolio_id, archived))

    async def get_portfolio_analytics(self, portfolio_id, timeframe="1y"):
        return {
            "portfolio_id": str(portfolio_id),
            "total_invested": 100.0,
            "current_value": 125.0,
            "total_gain_loss": 25.0,
            "total_gain_loss_percent": 25.0,
            "twr": "12.5",
            "mwr": "10.5",
            "allocation": [{"label": "Stocks", "value": 100.0}],
            "performance_history": [{"name": "Jan 2024", "value": 100.0}],
            "contribution_history": [{"name": "Jan 2024", "value": 100.0}],
            "sector_breakdown": [{"label": "Tech", "value": 100.0}],
            "timeframe": timeframe,
        }

    async def get_holdings(self, portfolio_id, in_currency=None):
        return {
            "data": [{"ticker": "AAPL", "quantity": 10.0, "current_price": 185.2}],
            "currency": (in_currency or Currency.USD).value,
            "total_value": 1852.0,
        }

    async def get_performance(self, portfolio_id):
        return {
            "portfolio_id": str(portfolio_id),
            "returns": 12.5,
            "returns_percent": 12.5,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "data_points": [],
        }

    async def get_allocation(self, portfolio_id, group_by="asset_class"):
        return {
            "portfolio_id": str(portfolio_id),
            "allocations": [
                {"category": "Stocks", "value": 100.0, "percent": 100.0, "holdings": []}
            ],
            "group_by": group_by,
        }


def _patch_portfolio_interactor(monkeypatch, interactor):
    monkeypatch.setattr(
        portfolio_routes, "PortfolioInteractor", lambda session: interactor
    )


_FAKE_PERFORMANCE_INPUTS = PerformanceInputs(
    beginning_value=0.0,
    ending_value=1852.0,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    cash_flows=[(date(2024, 1, 1), 1500.0)],
)


class FakeAnalyticsInteractor:
    async def get_holdings(self, portfolio_id, in_currency=None):
        return [
            {
                "ticker": "AAPL",
                "quantity": 10.0,
                "current_price": 185.2,
                "market_value": 1852.0,
                "cost_basis": 1500.0,
                "total_invested": 1500.0,
                "total_return": 352.0,
                "total_return_percent": 23.47,
            }
        ]

    async def calculate_performance(self, portfolio_id):
        return {"twr": "12.5", "mwr": "10.5"}

    async def get_performance_inputs(self, portfolio_id, start_date=None):
        self.last_start_date = start_date
        return _FAKE_PERFORMANCE_INPUTS

    async def get_allocation(self, portfolio_id, group_by="asset_class"):
        return [{"name": "Stocks", "value": 1852.0, "weight_percent": 100.0}]

    async def get_performance_history(self, portfolio_id, timeframe):
        return [{"name": "Jan 2024", "value": 100.0}]

    async def get_contribution_history(self, portfolio_id, start_date=None):
        return [{"name": "Jan 2024", "value": 100.0}]

    async def get_sector_breakdown(self, portfolio_id):
        return [{"label": "Tech", "value": 1852.0}]


def _patch_analytics_interactor(monkeypatch, interactor):
    monkeypatch.setattr(
        portfolio_routes, "AnalyticsInteractor", lambda session, currency: interactor
    )


class ErrorAnalyticsInteractor(FakeAnalyticsInteractor):
    def __init__(self, target):
        self.target = target

    async def get_holdings(self, portfolio_id, in_currency=None):
        if self.target == "holdings":
            raise RuntimeError("holdings failed")
        return await super().get_holdings(portfolio_id, in_currency)

    async def calculate_performance(self, portfolio_id):
        if self.target == "performance":
            raise RuntimeError("performance failed")
        return await super().calculate_performance(portfolio_id)

    async def get_allocation(self, portfolio_id, group_by="asset_class"):
        if self.target == "allocation":
            raise RuntimeError("allocation failed")
        return await super().get_allocation(portfolio_id, group_by)


@pytest.mark.integration
@pytest.mark.happy_path
@pytest.mark.parametrize(
    "method,path,payload,params,expected_status,expected_key",
    [
        ("get", "/api/v1/portfolios/", None, None, 200, "Core"),
        (
            "post",
            "/api/v1/portfolios/",
            {"name": "Income", "base_currency": "USD", "description": "Long term"},
            None,
            201,
            "id",
        ),
        ("get", "/api/v1/portfolios/{id}", None, None, 200, "Core"),
        (
            "put",
            "/api/v1/portfolios/{id}",
            None,
            {"name": "Updated", "description": "New"},
            200,
            "Core",
        ),
        ("delete", "/api/v1/portfolios/{id}", None, None, 204, None),
    ],
)
def test_portfolio_crud_routes(
    authed_client,
    monkeypatch,
    fake_user,
    method,
    path,
    payload,
    params,
    expected_status,
    expected_key,
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)
    portfolio_id = interactor.portfolio_id
    resolved_path = path.replace("{id}", str(portfolio_id))

    response = authed_client.request(method, resolved_path, json=payload, params=params)
    assert response.status_code == expected_status
    if method == "post":
        assert interactor.last_create is not None
        assert interactor.last_create[0].base_currency == Currency.USD
    if method == "put":
        assert interactor.last_update == (portfolio_id, "Updated", "New")
    if method == "get" and path.endswith("{id}"):
        assert response.json()["name"] == expected_key
    if method == "get" and path == "/api/v1/portfolios/":
        assert response.json()[0]["name"] == expected_key
    if method == "delete":
        assert interactor.deleted == [portfolio_id]


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.parametrize(
    "path,expected_body",
    [
        ("/api/v1/portfolios/{id}/analytics", "twr"),
        ("/api/v1/portfolios/{id}/holdings", "data"),
        ("/api/v1/portfolios/{id}/performance", "returns"),
        ("/api/v1/portfolios/{id}/allocation", "allocations"),
    ],
)
def test_portfolio_analytics_routes(
    authed_client, monkeypatch, fake_user, path, expected_body
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)
    _patch_analytics_interactor(monkeypatch, FakeAnalyticsInteractor())
    response = authed_client.get(path.replace("{id}", str(interactor.portfolio_id)))

    assert response.status_code == 200
    assert expected_body in response.json()


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "mode,path,expected_status",
    [
        ("missing", "/api/v1/portfolios/{id}", 404),
        ("wrong-owner", "/api/v1/portfolios/{id}", 403),
        ("missing", "/api/v1/portfolios/{id}/analytics", 400),
    ],
)
def test_portfolio_error_paths(
    authed_client, monkeypatch, fake_user, mode, path, expected_status
):
    interactor = FakePortfolioInteractor(fake_user.id, mode=mode)
    _patch_portfolio_interactor(monkeypatch, interactor)
    _patch_analytics_interactor(monkeypatch, FakeAnalyticsInteractor())
    response = authed_client.get(path.replace("{id}", str(interactor.portfolio_id)))

    assert response.status_code == expected_status


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "method,path",
    [("put", "/api/v1/portfolios/{id}"), ("delete", "/api/v1/portfolios/{id}")],
)
def test_portfolio_update_delete_missing_paths(
    authed_client, monkeypatch, fake_user, method, path
):
    interactor = FakePortfolioInteractor(fake_user.id, mode="missing")
    _patch_portfolio_interactor(monkeypatch, interactor)
    _patch_analytics_interactor(monkeypatch, FakeAnalyticsInteractor())
    response = authed_client.request(
        method,
        path.replace("{id}", str(interactor.portfolio_id)),
        params={"name": "X", "description": "Y"} if method == "put" else None,
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.edge_case
def test_portfolio_holdings_allows_currency_override(
    authed_client, monkeypatch, fake_user
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)
    _patch_analytics_interactor(monkeypatch, FakeAnalyticsInteractor())
    response = authed_client.get(
        f"/api/v1/portfolios/{interactor.portfolio_id}/holdings",
        params={"in_currency": "EUR"},
    )
    assert response.status_code == 200
    assert response.json()["currency"] == "EUR"


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_portfolio_create_generic_exception_returns_400(
    authed_client, monkeypatch, fake_user
):
    interactor = FakePortfolioInteractor(fake_user.id, mode="create-error")
    _patch_portfolio_interactor(monkeypatch, interactor)
    response = authed_client.post(
        "/api/v1/portfolios/",
        json={"name": "Income", "base_currency": "USD", "description": "Long term"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_portfolio_update_delete_wrong_owner_paths(
    authed_client, monkeypatch, fake_user
):
    interactor = FakePortfolioInteractor(fake_user.id, mode="wrong-owner")
    _patch_portfolio_interactor(monkeypatch, interactor)
    update = authed_client.put(
        f"/api/v1/portfolios/{interactor.portfolio_id}",
        params={"name": "X", "description": "Y"},
    )
    delete = authed_client.delete(f"/api/v1/portfolios/{interactor.portfolio_id}")
    assert update.status_code == 403
    assert delete.status_code == 403


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_portfolio_update_delete_generic_exception_paths(
    authed_client, monkeypatch, fake_user
):
    _patch_analytics_interactor(monkeypatch, FakeAnalyticsInteractor())
    update_interactor = FakePortfolioInteractor(fake_user.id, mode="update-error")
    _patch_portfolio_interactor(monkeypatch, update_interactor)
    update = authed_client.put(
        f"/api/v1/portfolios/{update_interactor.portfolio_id}",
        params={"name": "X", "description": "Y"},
    )
    assert update.status_code == 400

    delete_interactor = FakePortfolioInteractor(fake_user.id, mode="delete-error")
    _patch_portfolio_interactor(monkeypatch, delete_interactor)
    delete = authed_client.delete(
        f"/api/v1/portfolios/{delete_interactor.portfolio_id}"
    )
    assert delete.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_portfolio_analytics_subroutes_generic_exception_paths(
    authed_client, monkeypatch, fake_user
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)

    _patch_analytics_interactor(monkeypatch, ErrorAnalyticsInteractor("holdings"))
    holdings = authed_client.get(
        f"/api/v1/portfolios/{interactor.portfolio_id}/holdings",
        params={"in_currency": "XXX"},
    )
    assert holdings.status_code == 400

    _patch_analytics_interactor(monkeypatch, ErrorAnalyticsInteractor("performance"))
    performance = authed_client.get(
        f"/api/v1/portfolios/{interactor.portfolio_id}/performance"
    )
    assert performance.status_code == 400

    _patch_analytics_interactor(monkeypatch, ErrorAnalyticsInteractor("allocation"))
    allocation = authed_client.get(
        f"/api/v1/portfolios/{interactor.portfolio_id}/allocation"
    )
    assert allocation.status_code == 400


@pytest.mark.integration
@pytest.mark.happy_path
@pytest.mark.parametrize(
    "params,expected",
    [(None, False), ({"include_archived": "true"}, True)],
)
def test_list_portfolios_passes_include_archived(
    authed_client, monkeypatch, fake_user, params, expected
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)
    response = authed_client.get("/api/v1/portfolios/", params=params)

    assert response.status_code == 200
    assert interactor.last_list_include_archived is expected


@pytest.mark.integration
@pytest.mark.happy_path
@pytest.mark.parametrize("action,archived", [("archive", True), ("unarchive", False)])
def test_archive_routes_toggle_archived(
    authed_client, monkeypatch, fake_user, action, archived
):
    interactor = FakePortfolioInteractor(fake_user.id)
    _patch_portfolio_interactor(monkeypatch, interactor)
    response = authed_client.post(
        f"/api/v1/portfolios/{interactor.portfolio_id}/{action}"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Core"
    assert interactor.archived_calls == [(interactor.portfolio_id, archived)]


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "mode,expected_status",
    [("missing", 404), ("wrong-owner", 403), ("archive-error", 400)],
)
def test_archive_route_error_paths(
    authed_client, monkeypatch, fake_user, mode, expected_status
):
    interactor = FakePortfolioInteractor(fake_user.id, mode=mode)
    _patch_portfolio_interactor(monkeypatch, interactor)
    response = authed_client.post(
        f"/api/v1/portfolios/{interactor.portfolio_id}/archive"
    )

    assert response.status_code == expected_status
    assert interactor.archived_calls == []


class FakeSummaryPortfolioInteractor:
    """Two active portfolios: one in USD, one in EUR."""

    def __init__(self, owner_id):
        self.usd_id = uuid4()
        self.eur_id = uuid4()
        self.owner_id = owner_id

    async def list_portfolios(self, user_id, include_archived=False):
        return [
            {"id": str(self.usd_id), "base_currency": "USD", "name": "US"},
            {"id": str(self.eur_id), "base_currency": "EUR", "name": "EU"},
        ]


def _patch_summary(monkeypatch, fake_user, fx_factor, fx_history=()):
    portfolios = FakeSummaryPortfolioInteractor(fake_user.id)
    analytics = FakeAnalyticsInteractor()
    fx_calls = []

    async def fake_fx(from_ccy, to_ccy):
        fx_calls.append((from_ccy, to_ccy))
        return fx_factor

    async def fake_fx_history(from_ccy, to_ccy, start, end):
        return list(fx_history)

    monkeypatch.setattr(
        portfolio_routes, "PortfolioInteractor", lambda session: portfolios
    )
    _patch_analytics_interactor(monkeypatch, analytics)
    monkeypatch.setattr(portfolio_routes, "_fetch_fx_factor", fake_fx)
    monkeypatch.setattr(portfolio_routes, "_fetch_fx_factor_history", fake_fx_history)
    return portfolios, analytics, fx_calls


@pytest.mark.integration
@pytest.mark.happy_path
def test_analytics_summary_converts_and_merges_portfolios(
    authed_client, monkeypatch, fake_user
):
    _portfolios, _analytics, fx_calls = _patch_summary(
        monkeypatch, fake_user, fx_factor=1.1
    )

    response = authed_client.get(
        "/api/v1/portfolios/analytics/summary",
        params={"timeframe": "all", "in_currency": "USD"},
    )

    assert response.status_code == 200
    body = response.json()
    assert fx_calls == [("EUR", "USD")]
    assert body["currency"] == "USD"
    assert body["portfolio_count"] == 2
    assert body["excluded_portfolio_ids"] == []
    # 1852 USD + 1852 EUR × 1.10
    assert body["current_value"] == pytest.approx(3889.2)
    assert body["top_holdings"][0]["ticker"] == "AAPL"
    assert body["top_holdings"][0]["percent"] == 100.0
    expected = PerformanceService.summarize(
        PerformanceInputs.combine(
            [
                _FAKE_PERFORMANCE_INPUTS,
                _FAKE_PERFORMANCE_INPUTS.scaled(1.1),
            ]
        )
    )
    assert body["twr"] == expected["twr"]


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_analytics_summary_excludes_portfolios_without_fx_rate(
    authed_client, monkeypatch, fake_user
):
    portfolios, _analytics, _fx_calls = _patch_summary(
        monkeypatch, fake_user, fx_factor=0.0
    )

    response = authed_client.get("/api/v1/portfolios/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_count"] == 1
    assert body["current_value"] == 1852.0
    assert body["excluded_portfolio_ids"] == [str(portfolios.eur_id)]


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.parametrize("timeframe", ["all", "1y", "ytd"])
def test_analytics_summary_passes_timeframe_window(
    authed_client, monkeypatch, fake_user, timeframe
):
    _portfolios, analytics, _fx_calls = _patch_summary(
        monkeypatch, fake_user, fx_factor=1.0
    )

    response = authed_client.get(
        "/api/v1/portfolios/analytics/summary", params={"timeframe": timeframe}
    )

    assert response.status_code == 200
    assert response.json()["timeframe"] == timeframe
    assert analytics.last_start_date == timeframe_start(timeframe)


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_analytics_summary_rejects_unknown_currency(
    authed_client, monkeypatch, fake_user
):
    _patch_summary(monkeypatch, fake_user, fx_factor=1.0)

    response = authed_client.get(
        "/api/v1/portfolios/analytics/summary", params={"in_currency": "XXX"}
    )

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.edge_case
def test_analytics_summary_converts_sub_cent_rates(
    authed_client, monkeypatch, fake_user
):
    # NGN→USD-sized rate; a ×100 integer rate would round this to 0.
    _patch_summary(monkeypatch, fake_user, fx_factor=0.00075)

    response = authed_client.get("/api/v1/portfolios/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_count"] == 2
    assert body["excluded_portfolio_ids"] == []
    assert body["current_value"] == pytest.approx(1852.0 + 1.39, abs=0.01)


@pytest.mark.integration
@pytest.mark.happy_path
def test_analytics_summary_converts_history_at_historical_rates(
    authed_client, monkeypatch, fake_user
):
    # EUR was worth 1.2 USD in Jan 2024 and 1.1 today.
    _patch_summary(
        monkeypatch,
        fake_user,
        fx_factor=1.1,
        fx_history=[(date(2024, 1, 2), 1.2)],
    )

    response = authed_client.get("/api/v1/portfolios/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    # Contribution: 100 USD + 100 EUR at January's 1.2 (not today's 1.1).
    assert body["contribution_history"] == [{"name": "Jan 2024", "value": 220.0}]
    # Current value uses today's rate.
    assert body["current_value"] == pytest.approx(1852.0 + 1852.0 * 1.1)


# --- GET /portfolios/analytics/benchmark ---------------------------------------


class FakeBenchmarkPortfolios:
    def __init__(self, portfolios):
        self.portfolios = portfolios

    async def list_portfolios(self, user_id, include_archived=False):
        return self.portfolios

    async def get_portfolio(self, portfolio_id):
        for p in self.portfolios:
            if p["id"] == str(portfolio_id):
                return p
        raise ValueError(f"Portfolio {portfolio_id} not found")


class FakeBenchmarkAnalytics:
    """One instance per portfolio id; `series` maps id to (first_trade, final
    value, flows): flat 100 until the last date, then `final`."""

    registry: dict = {}

    def __init__(self, session, currency):
        pass

    async def get_first_trade_date(self, portfolio_id):
        entry = self.registry.get(str(portfolio_id))
        return entry[0] if entry else None

    async def get_value_series(self, portfolio_id, dates):
        first, final, flows = self.registry[str(portfolio_id)]
        values = [100.0 if d < dates[-1] else final for d in dates]
        return values, [f for f in flows if dates[0] < f[0] <= dates[-1]]


class FakeBenchmarkYahoo:
    """Closes: 100 up to today, `final` on today (stored as x100 integers)."""

    closes_from = None  # first date with a price; default: far back
    final = 105.0
    currency = "USD"

    async def get_price_history(self, ticker, start, end):
        if ticker == "NOPE":
            return []
        first = type(self).closes_from or (start - timedelta(days=5))
        return [(first, 10000), (end, round(type(self).final * 100))]

    async def get_quote_currency(self, ticker):
        return type(self).currency


def _portfolio(owner_id, base="USD", pid=None):
    return {
        "id": str(pid or uuid4()),
        "user_id": str(owner_id),
        "base_currency": base,
        "name": "P",
    }


def _setup_benchmark(
    monkeypatch,
    owner_id,
    portfolios,
    entries,
    fx_factors=None,
    fx_history=None,
    closes_from=None,
    final=105.0,
    quote_currency="USD",
):
    FakeBenchmarkAnalytics.registry = entries
    FakeBenchmarkYahoo.closes_from = closes_from
    FakeBenchmarkYahoo.final = final
    FakeBenchmarkYahoo.currency = quote_currency
    fx_factors = fx_factors or {}
    fx_history = fx_history or {}

    async def factor(from_ccy, to_ccy):
        return fx_factors.get((from_ccy, to_ccy), 0.0)

    async def history(from_ccy, to_ccy, start, end):
        return fx_history.get((from_ccy, to_ccy), [])

    monkeypatch.setattr(
        portfolio_routes, "PortfolioInteractor",
        lambda s: FakeBenchmarkPortfolios(portfolios),
    )
    monkeypatch.setattr(portfolio_routes, "AnalyticsInteractor", FakeBenchmarkAnalytics)
    monkeypatch.setattr(
        portfolio_routes, "build_adapter", lambda provider: FakeBenchmarkYahoo()
    )
    monkeypatch.setattr(portfolio_routes, "_fetch_fx_factor", factor)
    monkeypatch.setattr(portfolio_routes, "_fetch_fx_factor_history", history)


def _get(client, **params):
    params.setdefault("benchmark", "^GSPC")
    return client.get("/api/v1/portfolios/analytics/benchmark", params=params)


@pytest.mark.integration
@pytest.mark.happy_path
def test_benchmark_compares_returns_over_the_period(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    long_ago = date.today() - timedelta(days=2000)
    _setup_benchmark(monkeypatch, fake_user.id, [p], {p["id"]: (long_ago, 110.0, [])})

    response = _get(authed_client, period="1y")

    assert response.status_code == 200
    body = response.json()
    assert body["portfolio"]["return_pct"] == 10.0
    assert body["benchmark"]["return_pct"] == 5.0
    assert body["excess_return_pct"] == 5.0
    assert body["limited_by"] is None
    assert body["benchmark"]["name"] == "S&P 500"
    assert body["currency"] == "USD" and body["portfolio_count"] == 1
    assert body["start_date"] == body["requested_start"]
    first, last = body["series"][0], body["series"][-1]
    assert (first["portfolio"], first["benchmark"]) == (0.0, 0.0)
    assert (last["portfolio"], last["benchmark"]) == (10.0, 5.0)
    assert last["date"] == date.today().isoformat()
    assert body["portfolio"]["annualized_pct"] is not None  # a full year


@pytest.mark.integration
@pytest.mark.edge_case
def test_benchmark_annualizes_multi_year_periods(authed_client, monkeypatch, fake_user):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=5000), 133.1, [])},
        final=133.1,
    )

    body = _get(authed_client, period="3y").json()

    # +33.1% over three years is 10% a year.
    assert body["portfolio"]["annualized_pct"] == pytest.approx(10.0, abs=0.1)
    assert body["benchmark"]["annualized_pct"] == pytest.approx(10.0, abs=0.1)


@pytest.mark.integration
@pytest.mark.edge_case
def test_benchmark_has_no_annualized_figure_for_short_periods(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=2000), 110.0, [])},
    )

    body = _get(authed_client, period="3m").json()

    assert body["portfolio"]["annualized_pct"] is None
    assert body["benchmark"]["annualized_pct"] is None


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "params",
    [
        {"period": "2w"},
        {"period": ""},
        {"benchmark": "DROP TABLE"},
        {"benchmark": ""},
        {"in_currency": "XXX"},
    ],
)
def test_benchmark_rejects_invalid_input(authed_client, monkeypatch, fake_user, params):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=2000), 110.0, [])},
    )

    assert _get(authed_client, **params).status_code == 422


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize("period", ["ytd", "3m", "6m", "1y", "3y", "5y", "10y"])
def test_benchmark_accepts_every_documented_period(
    authed_client, monkeypatch, fake_user, period
):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=5000), 110.0, [])},
    )

    response = _get(authed_client, period=period.upper())

    assert response.status_code == 200
    assert response.json()["period"] == period


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_benchmark_requires_the_callers_own_portfolio(
    authed_client, monkeypatch, fake_user
):
    mine = _portfolio(fake_user.id)
    theirs = _portfolio(uuid4())
    _setup_benchmark(
        monkeypatch, fake_user.id, [mine, theirs],
        {mine["id"]: (date.today() - timedelta(days=900), 110.0, [])},
    )

    assert _get(authed_client, portfolio_id=theirs["id"]).status_code == 403
    assert _get(authed_client, portfolio_id=str(uuid4())).status_code == 404
    assert _get(authed_client, portfolio_id=mine["id"]).status_code == 200


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_benchmark_without_portfolios_trades_or_prices(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)

    _setup_benchmark(monkeypatch, fake_user.id, [], {})
    assert _get(authed_client).status_code == 404  # no portfolios

    _setup_benchmark(monkeypatch, fake_user.id, [p], {})
    assert _get(authed_client).status_code == 404  # portfolio without trades

    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=900), 110.0, [])},
    )
    missing = _get(authed_client, benchmark="NOPE")
    assert missing.status_code == 404
    assert "NOPE" in missing.json()["detail"]


@pytest.mark.integration
@pytest.mark.edge_case
def test_a_young_portfolio_limits_the_comparison_window(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    first_trade = date.today() - timedelta(days=40)
    _setup_benchmark(monkeypatch, fake_user.id, [p], {p["id"]: (first_trade, 110.0, [])})

    body = _get(authed_client, period="5y").json()

    assert body["limited_by"] == "portfolio"
    assert body["start_date"] == first_trade.isoformat()
    assert body["requested_start"] < body["start_date"]
    assert body["series"][0]["date"] == first_trade.isoformat()


@pytest.mark.integration
@pytest.mark.edge_case
def test_a_young_benchmark_limits_the_comparison_window(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    bench_first = date.today() - timedelta(days=100)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=2000), 110.0, [])},
        closes_from=bench_first,
    )

    body = _get(authed_client, period="1y").json()

    assert body["limited_by"] == "benchmark"
    assert body["start_date"] == bench_first.isoformat()


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_a_portfolio_started_this_week_cannot_be_compared_yet(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=3), 110.0, [])},
    )

    response = _get(authed_client)

    assert response.status_code == 422
    assert "at least a week" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.happy_path
def test_portfolio_in_another_currency_is_converted_at_each_dates_rate(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id, base="EUR")
    long_ago = date.today() - timedelta(days=2000)
    # EUR worth 1.00 USD until today, 1.10 today. 100 EUR -> 110 EUR is +10% in
    # euros but 100 USD -> 121 USD in dollars.
    _setup_benchmark(
        monkeypatch, fake_user.id, [p], {p["id"]: (long_ago, 110.0, [])},
        fx_factors={("EUR", "USD"): 1.1},
        fx_history={("EUR", "USD"): [(long_ago, 1.0), (date.today(), 1.1)]},
    )

    body = _get(authed_client, in_currency="USD").json()

    assert body["portfolio"]["return_pct"] == 21.0


@pytest.mark.integration
@pytest.mark.happy_path
def test_benchmark_in_another_currency_is_converted_too(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    long_ago = date.today() - timedelta(days=2000)
    # A London-listed ETF quoted in pence: GBp -> GBP. Up 5% in pounds, and
    # the pound rose 1.00 -> 1.20 against the dollar: 1.05 * 1.2 - 1 = 26%.
    _setup_benchmark(
        monkeypatch, fake_user.id, [p], {p["id"]: (long_ago, 110.0, [])},
        fx_factors={("GBP", "USD"): 1.2},
        fx_history={("GBP", "USD"): [(long_ago, 1.0), (date.today(), 1.2)]},
        quote_currency="GBp",
    )

    body = _get(authed_client, benchmark="IWDA.L").json()

    assert body["benchmark"]["return_pct"] == 26.0
    assert body["benchmark"]["converted"] is True
    assert body["benchmark"]["quote_currency"] == "GBP"


@pytest.mark.integration
@pytest.mark.edge_case
def test_benchmark_is_flagged_when_its_currency_cannot_be_converted(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=2000), 110.0, [])},
        quote_currency="JPY",  # no JPY->USD rate available
    )

    body = _get(authed_client, benchmark="^N225").json()

    assert body["benchmark"]["converted"] is False
    assert body["benchmark"]["return_pct"] == 5.0  # left in its own currency


@pytest.mark.integration
@pytest.mark.edge_case
def test_portfolios_without_an_exchange_rate_are_excluded(
    authed_client, monkeypatch, fake_user, fake_valkey
):
    usd = _portfolio(fake_user.id)
    ngn = _portfolio(fake_user.id, base="NGN")
    long_ago = date.today() - timedelta(days=2000)
    entries = {usd["id"]: (long_ago, 110.0, []), ngn["id"]: (long_ago, 200.0, [])}
    _setup_benchmark(monkeypatch, fake_user.id, [usd, ngn], entries)

    body = _get(authed_client).json()

    assert body["excluded_portfolio_ids"] == [ngn["id"]]
    assert body["portfolio_count"] == 1
    assert body["portfolio"]["return_pct"] == 10.0  # only the USD one

    fake_valkey.store.clear()  # the first answer was cached
    _setup_benchmark(monkeypatch, fake_user.id, [ngn], {ngn["id"]: entries[ngn["id"]]})
    response = _get(authed_client)
    assert response.status_code == 422
    assert "unavailable" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.happy_path
def test_all_portfolios_are_combined_when_none_is_chosen(
    authed_client, monkeypatch, fake_user
):
    a = _portfolio(fake_user.id)
    b = _portfolio(fake_user.id)
    long_ago = date.today() - timedelta(days=2000)
    # +20% and -10% on equal capital combine to +5%, not their average of 5% by
    # accident: 100 + 100 -> 120 + 90 = 210 on 200.
    _setup_benchmark(
        monkeypatch, fake_user.id, [a, b],
        {a["id"]: (long_ago, 120.0, []), b["id"]: (long_ago, 90.0, [])},
    )

    body = _get(authed_client).json()

    assert body["portfolio_count"] == 2
    assert body["portfolio"]["return_pct"] == 5.0


@pytest.mark.integration
@pytest.mark.happy_path
def test_money_added_during_the_period_is_not_counted_as_gain(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    long_ago = date.today() - timedelta(days=2000)
    # Worth 100 until today, then 200, because 100 was added today: no gain.
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (long_ago, 200.0, [(date.today(), 100.0)])},
    )

    assert _get(authed_client).json()["portfolio"]["return_pct"] == 0.0


@pytest.mark.integration
@pytest.mark.edge_case
def test_benchmark_catalog_names_and_custom_tickers(
    authed_client, monkeypatch, fake_user
):
    p = _portfolio(fake_user.id)
    _setup_benchmark(
        monkeypatch, fake_user.id, [p],
        {p["id"]: (date.today() - timedelta(days=900), 110.0, [])},
    )

    # Case-insensitive input; the catalog supplies the display name.
    crypto = _get(authed_client, benchmark="btc-usd").json()["benchmark"]
    assert (crypto["ticker"], crypto["name"]) == ("BTC-USD", "Bitcoin")
    assert crypto["return_pct"] == 5.0
    # Anything else Yahoo knows is a custom benchmark, named by its ticker.
    custom = _get(authed_client, benchmark="mstr").json()["benchmark"]
    assert (custom["ticker"], custom["name"]) == ("MSTR", "MSTR")


# --- benchmark providers and cache ----------------------------------------------


class FakeNgxPulse(FakeBenchmarkYahoo):
    enabled = True

    def __init__(self):
        self._enabled = type(self).enabled

    async def get_quote_currency(self, ticker):
        raise AssertionError("only Yahoo is asked for a quote currency")


def _use_providers(monkeypatch, chosen):
    """Route build_adapter() to fakes and record which providers were asked for."""

    def build(provider):
        chosen.append(provider)
        return FakeNgxPulse() if provider != "yfinance" else FakeBenchmarkYahoo()

    monkeypatch.setattr(portfolio_routes, "build_adapter", build)


def _one_portfolio(monkeypatch, fake_user, **kwargs):
    p = _portfolio(fake_user.id)
    long_ago = date.today() - timedelta(days=2000)
    _setup_benchmark(monkeypatch, fake_user.id, [p], {p["id"]: (long_ago, 110.0, [])}, **kwargs)
    return p


@pytest.mark.integration
@pytest.mark.happy_path
def test_catalog_tickers_are_served_by_their_own_provider(
    authed_client, monkeypatch, fake_user
):
    _one_portfolio(monkeypatch, fake_user, fx_factors={("NGN", "USD"): 0.001})
    chosen: list[str] = []
    _use_providers(monkeypatch, chosen)

    body = _get(authed_client, benchmark="NGX:ASI").json()

    assert chosen == ["ngxpulse"]
    assert body["benchmark"]["provider"] == "ngxpulse"
    assert body["benchmark"]["name"] == "NGX All-Share Index"
    assert body["benchmark"]["quote_currency"] == "NGN"


@pytest.mark.integration
@pytest.mark.happy_path
def test_a_custom_ticker_can_name_its_provider(authed_client, monkeypatch, fake_user):
    _one_portfolio(monkeypatch, fake_user, fx_factors={("NGN", "USD"): 0.001})
    chosen: list[str] = []
    _use_providers(monkeypatch, chosen)

    body = _get(authed_client, benchmark="NGX30", provider="ngnmarket").json()

    assert chosen == ["ngnmarket"]
    assert body["benchmark"]["provider"] == "ngnmarket"
    assert body["benchmark"]["quote_currency"] == "NGN"


@pytest.mark.integration
@pytest.mark.edge_case
def test_other_tickers_default_to_yahoo(authed_client, monkeypatch, fake_user):
    _one_portfolio(monkeypatch, fake_user)
    chosen: list[str] = []
    _use_providers(monkeypatch, chosen)

    assert _get(authed_client, benchmark="MSFT").json()["benchmark"]["provider"] == "yfinance"
    assert chosen == ["yfinance"]


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.parametrize("provider", ["tiingo", "tradingview", "nope"])
def test_providers_that_cannot_serve_benchmarks_are_rejected(
    authed_client, monkeypatch, fake_user, provider
):
    _one_portfolio(monkeypatch, fake_user)

    response = _get(authed_client, provider=provider)

    assert response.status_code == 422
    assert "provider must be one of" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.edge_case
def test_a_provider_without_an_api_key_says_so(authed_client, monkeypatch, fake_user):
    _one_portfolio(monkeypatch, fake_user)
    _use_providers(monkeypatch, [])
    monkeypatch.setattr(FakeNgxPulse, "enabled", False)

    response = _get(authed_client, benchmark="NGX:ASI")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "NGXPulse isn't set up on this server, so NGX:ASI can't be loaded."
    )


@pytest.mark.integration
@pytest.mark.edge_case
def test_a_missing_series_names_the_provider(authed_client, monkeypatch, fake_user):
    _one_portfolio(monkeypatch, fake_user)

    response = _get(authed_client, benchmark="NOPE")

    assert response.status_code == 404
    assert response.json()["detail"] == "No price history found for NOPE on Yahoo Finance"


@pytest.mark.integration
@pytest.mark.edge_case
def test_a_missing_series_from_a_keyed_provider_hints_at_the_key(
    authed_client, monkeypatch, fake_user
):
    _one_portfolio(monkeypatch, fake_user)
    _use_providers(monkeypatch, [])

    response = _get(authed_client, benchmark="NOPE", provider="ngxpulse")

    assert response.status_code == 404
    assert "API key" in response.json()["detail"]
    assert "NGXPulse" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.happy_path
def test_a_repeat_comparison_is_served_from_the_cache(
    authed_client, monkeypatch, fake_user, fake_valkey
):
    _one_portfolio(monkeypatch, fake_user)
    calls = []
    original = FakeBenchmarkYahoo.get_price_history

    async def counting(self, ticker, start, end):
        calls.append(ticker)
        return await original(self, ticker, start, end)

    monkeypatch.setattr(FakeBenchmarkYahoo, "get_price_history", counting)

    first = _get(authed_client)
    second = _get(authed_client)

    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    assert second.json() == first.json()
    assert calls == ["^GSPC"]
    assert list(fake_valkey.expiries.values())[-1] == 35 * 60
    assert "generated_at" in first.json()


@pytest.mark.integration
@pytest.mark.edge_case
def test_the_cache_is_separate_per_period_currency_and_benchmark(
    authed_client, monkeypatch, fake_user
):
    _one_portfolio(monkeypatch, fake_user, fx_factors={("USD", "EUR"): 0.9})

    _get(authed_client)
    different = [
        _get(authed_client, period="3y"),
        _get(authed_client, in_currency="EUR"),
        _get(authed_client, benchmark="VOO"),
    ]

    assert [r.headers["X-Cache"] for r in different] == ["MISS"] * 3


@pytest.mark.integration
@pytest.mark.security
def test_one_users_cache_is_not_served_to_another(
    authed_client, monkeypatch, fake_user
):
    from adapters.inbound.http.dependencies import get_current_user
    from domain.entities.models import User
    from main import app

    _one_portfolio(monkeypatch, fake_user)
    assert _get(authed_client).headers["X-Cache"] == "MISS"

    other = User(
        id=uuid4(),
        email="other@example.com",
        hashed_password="x",
        is_active=True,
        created_at=fake_user.created_at,
    )
    app.dependency_overrides[get_current_user] = lambda: other
    _one_portfolio(monkeypatch, other)

    assert _get(authed_client).headers["X-Cache"] == "MISS"


@pytest.mark.integration
@pytest.mark.edge_case
def test_failures_are_not_cached(authed_client, monkeypatch, fake_user, fake_valkey):
    _one_portfolio(monkeypatch, fake_user)

    assert _get(authed_client, benchmark="NOPE").status_code == 404

    assert not [k for k in fake_valkey.store if "NOPE" in k]


@pytest.mark.integration
@pytest.mark.happy_path
def test_changing_trades_drops_cached_comparisons(
    authed_client, monkeypatch, fake_user
):
    from adapters.inbound.http import trade_routes

    class FakeTrades:
        def __init__(self, session):
            pass

        async def delete_batch_trades(self, trade_ids):
            return len(trade_ids)

    monkeypatch.setattr(trade_routes, "TradeInteractor", FakeTrades)
    _one_portfolio(monkeypatch, fake_user)
    assert _get(authed_client).headers["X-Cache"] == "MISS"
    assert _get(authed_client).headers["X-Cache"] == "HIT"

    deleted = authed_client.post(
        "/api/v1/trades/bulk/delete", json={"trade_ids": [str(uuid4())]}
    )

    assert deleted.status_code == 204
    assert _get(authed_client).headers["X-Cache"] == "MISS"
