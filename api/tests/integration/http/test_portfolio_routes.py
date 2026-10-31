from datetime import date
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
