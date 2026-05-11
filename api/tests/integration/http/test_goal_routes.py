from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from adapters.inbound.http import goal_routes
from domain.value_objects.money import Currency


class FakeGoalInteractor:
    def __init__(self, mode="happy"):
        self.mode = mode
        self.goal_id = uuid4()
        self.last_create = None
        self.last_update = None

    async def list_goals(self, portfolio_id):
        if self.mode == "list-error":
            raise RuntimeError("list failed")
        return [{"id": str(self.goal_id), "portfolio_id": str(portfolio_id), "name": "Fire"}]

    async def create_goal(self, request):
        self.last_create = request
        return self.goal_id

    async def get_goal(self, goal_id):
        if self.mode == "missing":
            raise ValueError(f"Goal {goal_id} not found")
        return {
            "id": str(goal_id),
            "portfolio_id": str(uuid4()),
            "name": "Fire",
            "target_net_worth": 10000.0,
            "target_net_worth_currency": "USD",
            "target_date": "2026-01-01",
            "monthly_savings": 100.0,
            "monthly_savings_currency": "USD",
            "expected_annual_return": 7.0,
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-02T10:00:00",
        }

    async def update_goal(self, goal_id, request):
        if self.mode == "missing":
            raise ValueError(f"Goal {goal_id} not found")
        if self.mode == "update-error":
            raise RuntimeError("update failed")
        self.last_update = (goal_id, request)

    async def delete_goal(self, goal_id):
        if self.mode == "missing":
            raise ValueError(f"Goal {goal_id} not found")
        if self.mode == "delete-error":
            raise RuntimeError("delete failed")

    async def get_projection(self, goal_id):
        if self.mode == "missing":
            raise ValueError(f"Goal {goal_id} not found")
        if self.mode == "projection-error":
            raise RuntimeError("projection failed")
        return {
            "goal_id": str(goal_id),
            "name": "Fire",
            "current_value": "100.0",
            "target_value": "1000.0",
            "target_date": "2026-01-01",
            "days_remaining": 120,
            "projected_value": "1234.56",
            "shortfall": "0",
            "progress_percent": "12.5",
            "will_reach_target": True,
            "required_annual_return": "0.08",
            "expected_annual_return": "0.07",
        }


def _patch_goal_interactor(monkeypatch, interactor):
    monkeypatch.setattr(goal_routes, "GoalInteractor", lambda session: interactor)


@pytest.mark.integration
@pytest.mark.happy_path
@pytest.mark.parametrize(
    "method,path,body,params,expected_status",
    [
        ("get", "/api/v1/goals/", None, {"portfolio_id": str(uuid4())}, 200),
        (
            "post",
            "/api/v1/goals/",
            {
                "portfolio_id": str(uuid4()),
                "name": "Fire",
                "target_net_worth": 10000.0,
                "target_net_worth_currency": "USD",
                "target_date": "2026-01-01",
                "monthly_savings": 100.0,
                "monthly_savings_currency": "USD",
                "expected_annual_return": 7.0,
            },
            None,
            201,
        ),
        ("get", "/api/v1/goals/{id}", None, None, 200),
        (
            "put",
            "/api/v1/goals/{id}",
            {
                "portfolio_id": str(uuid4()),
                "name": "Updated",
                "target_net_worth": 20000.0,
                "target_net_worth_currency": "EUR",
                "target_date": "2026-06-01",
                "monthly_savings": 200.0,
                "monthly_savings_currency": "EUR",
                "expected_annual_return": 8.0,
            },
            None,
            200,
        ),
        ("delete", "/api/v1/goals/{id}", None, None, 204),
        ("get", "/api/v1/goals/{id}/projection", None, None, 200),
    ],
)
def test_goal_routes(authed_client, monkeypatch, method, path, body, params, expected_status):
    interactor = FakeGoalInteractor()
    _patch_goal_interactor(monkeypatch, interactor)
    goal_id = interactor.goal_id
    response = authed_client.request(
        method,
        path.replace("{id}", str(goal_id)),
        json=body,
        params=params,
    )

    assert response.status_code == expected_status
    if method == "post":
        assert interactor.last_create.target_net_worth == 1000000
        assert interactor.last_create.monthly_savings == 10000
    if method == "put":
        assert interactor.last_update[1].target_net_worth_currency == Currency.EUR
    if method == "get" and path.endswith("{id}"):
        assert response.json()["name"] == "Fire"


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_goal_error_paths(authed_client, monkeypatch):
    interactor = FakeGoalInteractor(mode="missing")
    _patch_goal_interactor(monkeypatch, interactor)
    missing = authed_client.get(f"/api/v1/goals/{uuid4()}")
    projection = authed_client.get(f"/api/v1/goals/{uuid4()}/projection")
    assert missing.status_code == 404
    assert projection.status_code == 404


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize("method,path", [("put", "/api/v1/goals/{id}"), ("delete", "/api/v1/goals/{id}")])
def test_goal_update_delete_missing_paths(authed_client, monkeypatch, method, path):
    interactor = FakeGoalInteractor(mode="missing")
    _patch_goal_interactor(monkeypatch, interactor)
    body = {
        "portfolio_id": str(uuid4()),
        "name": "Updated",
        "target_net_worth": 20000.0,
        "target_net_worth_currency": "EUR",
        "target_date": "2026-06-01",
        "monthly_savings": 200.0,
        "monthly_savings_currency": "EUR",
        "expected_annual_return": 8.0,
    }
    response = authed_client.request(
        method, path.replace("{id}", str(uuid4())), json=(body if method == "put" else None)
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_goal_create_rejects_invalid_currency(authed_client, monkeypatch):
    interactor = FakeGoalInteractor()
    _patch_goal_interactor(monkeypatch, interactor)
    response = authed_client.post(
        "/api/v1/goals/",
        json={
            "portfolio_id": str(uuid4()),
            "name": "Fire",
            "target_net_worth": 10000.0,
            "target_net_worth_currency": "XXX",
            "target_date": "2026-01-01",
            "monthly_savings": 100.0,
            "monthly_savings_currency": "USD",
            "expected_annual_return": 7.0,
        },
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_goal_list_generic_exception_returns_400(authed_client, monkeypatch):
    interactor = FakeGoalInteractor(mode="list-error")
    _patch_goal_interactor(monkeypatch, interactor)
    response = authed_client.get("/api/v1/goals/", params={"portfolio_id": str(uuid4())})
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_goal_update_delete_projection_generic_exceptions_return_400(authed_client, monkeypatch):
    body = {
        "portfolio_id": str(uuid4()),
        "name": "Updated",
        "target_net_worth": 20000.0,
        "target_net_worth_currency": "EUR",
        "target_date": "2026-06-01",
        "monthly_savings": 200.0,
        "monthly_savings_currency": "EUR",
        "expected_annual_return": 8.0,
    }

    _patch_goal_interactor(monkeypatch, FakeGoalInteractor(mode="update-error"))
    update = authed_client.put(f"/api/v1/goals/{uuid4()}", json=body)
    assert update.status_code == 400

    _patch_goal_interactor(monkeypatch, FakeGoalInteractor(mode="delete-error"))
    delete = authed_client.delete(f"/api/v1/goals/{uuid4()}")
    assert delete.status_code == 400

    _patch_goal_interactor(monkeypatch, FakeGoalInteractor(mode="projection-error"))
    projection = authed_client.get(f"/api/v1/goals/{uuid4()}/projection")
    assert projection.status_code == 400
