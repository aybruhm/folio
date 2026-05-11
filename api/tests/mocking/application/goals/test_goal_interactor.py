from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from application.goals import goal_interactor as goal_module
from domain.entities.models import Goal
from domain.ports.inbound.use_cases import CreateGoalRequest
from domain.value_objects.money import Currency


class FakeGoalRepository:
    def __init__(self, *_args, **_kwargs):
        self.goals = {}
        self.added = []
        self.updated = []
        self.deleted = []

    async def add(self, goal: Goal) -> None:
        self.goals[goal.id] = goal
        self.added.append(goal)

    async def get_by_id(self, goal_id):
        return self.goals.get(goal_id)

    async def list_by_portfolio(self, portfolio_id):
        return [g for g in self.goals.values() if g.portfolio_id == portfolio_id]

    async def update(self, goal: Goal) -> None:
        self.goals[goal.id] = goal
        self.updated.append(goal)

    async def delete(self, goal_id) -> None:
        self.deleted.append(goal_id)
        self.goals.pop(goal_id, None)


def _goal_repo(monkeypatch):
    repo = FakeGoalRepository()
    monkeypatch.setattr(goal_module, "GoalRepository", lambda session: repo)
    return repo


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_goal_adds_goal_and_returns_id(monkeypatch):
    repo = _goal_repo(monkeypatch)
    interactor = goal_module.GoalInteractor(session=object())
    portfolio_id = uuid4()
    request = CreateGoalRequest(
        portfolio_id=portfolio_id,
        name="Fire",
        target_net_worth=1000000,
        target_net_worth_currency=Currency.USD,
        target_date=date.today() + timedelta(days=365),
        monthly_savings=50000,
        monthly_savings_currency=Currency.USD,
        expected_annual_return=700,
    )

    goal_id = await interactor.create_goal(request)

    assert goal_id == repo.added[0].id
    assert repo.added[0].portfolio_id == portfolio_id
    assert repo.added[0].name == "Fire"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_goal_returns_serialized_data(monkeypatch):
    repo = _goal_repo(monkeypatch)
    interactor = goal_module.GoalInteractor(session=object())
    goal = Goal(
        id=uuid4(),
        portfolio_id=uuid4(),
        name="House",
        target_net_worth=2500000,
        target_net_worth_currency=Currency.USD,
        target_date=date(2026, 1, 1),
        monthly_savings=100000,
        monthly_savings_currency=Currency.USD,
        expected_annual_return=500,
        created_at=datetime(2024, 1, 1, 10, 0),
        updated_at=datetime(2024, 1, 2, 10, 0),
    )
    repo.goals[goal.id] = goal

    result = await interactor.get_goal(goal.id)

    assert result["id"] == str(goal.id)
    assert result["target_net_worth"] == 25000.0
    assert result["monthly_savings"] == 1000.0
    assert result["expected_annual_return"] == 5.0


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_list_goals_returns_portfolio_goals(monkeypatch):
    repo = _goal_repo(monkeypatch)
    interactor = goal_module.GoalInteractor(session=object())
    portfolio_id = uuid4()
    repo.goals = {
        uuid4(): Goal(
            id=uuid4(),
            portfolio_id=portfolio_id,
            name="Goal A",
            target_net_worth=1000,
            target_net_worth_currency=Currency.USD,
            target_date=date(2026, 1, 1),
            monthly_savings=100,
            monthly_savings_currency=Currency.USD,
            expected_annual_return=500,
            created_at=datetime(2024, 1, 1, 10, 0),
            updated_at=datetime(2024, 1, 2, 10, 0),
        ),
        uuid4(): Goal(
            id=uuid4(),
            portfolio_id=uuid4(),
            name="Goal B",
            target_net_worth=2000,
            target_net_worth_currency=Currency.USD,
            target_date=date(2026, 1, 1),
            monthly_savings=200,
            monthly_savings_currency=Currency.USD,
            expected_annual_return=500,
            created_at=datetime(2024, 1, 1, 10, 0),
            updated_at=datetime(2024, 1, 2, 10, 0),
        ),
    }

    result = await interactor.list_goals(portfolio_id)

    assert len(result) == 1
    assert result[0]["name"] == "Goal A"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_update_goal_replaces_frozen_goal(monkeypatch):
    repo = _goal_repo(monkeypatch)
    interactor = goal_module.GoalInteractor(session=object())
    goal = Goal(
        id=uuid4(),
        portfolio_id=uuid4(),
        name="Old",
        target_net_worth=1000,
        target_net_worth_currency=Currency.USD,
        target_date=date(2026, 1, 1),
        monthly_savings=100,
        monthly_savings_currency=Currency.USD,
        expected_annual_return=500,
        created_at=datetime(2024, 1, 1, 10, 0),
        updated_at=datetime(2024, 1, 1, 10, 0),
    )
    repo.goals[goal.id] = goal
    request = CreateGoalRequest(
        portfolio_id=goal.portfolio_id,
        name="New",
        target_net_worth=2000,
        target_net_worth_currency=Currency.EUR,
        target_date=date(2026, 6, 1),
        monthly_savings=200,
        monthly_savings_currency=Currency.EUR,
        expected_annual_return=700,
    )

    await interactor.update_goal(goal.id, request)

    updated = repo.goals[goal.id]
    assert updated.name == "New"
    assert updated.target_net_worth_currency == Currency.EUR
    assert updated.monthly_savings_currency == Currency.EUR
    assert repo.updated[0].id == goal.id


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_projection_uses_fire_services(monkeypatch):
    repo = _goal_repo(monkeypatch)
    interactor = goal_module.GoalInteractor(session=object())
    goal = Goal(
        id=uuid4(),
        portfolio_id=uuid4(),
        name="Fire",
        target_net_worth=1000000,
        target_net_worth_currency=Currency.USD,
        target_date=date.today() + timedelta(days=120),
        monthly_savings=50000,
        monthly_savings_currency=Currency.USD,
        expected_annual_return=700,
        created_at=datetime(2024, 1, 1, 10, 0),
        updated_at=datetime(2024, 1, 1, 10, 0),
    )
    repo.goals[goal.id] = goal

    monkeypatch.setattr(
        goal_module.FIREService,
        "calculate_projection",
        lambda **kwargs: {
            "projected_value": 1234.56,
            "shortfall": 789.0,
            "progress_percent": 12.5,
            "will_reach_target": True,
        },
    )
    monkeypatch.setattr(
        goal_module.FIREService, "calculate_required_return", lambda **kwargs: 0.08
    )

    result = await interactor.get_projection(goal.id)

    assert result["goal_id"] == str(goal.id)
    assert result["projected_value"] == "1234.56"
    assert result["required_annual_return"] == "0.08"
    assert result["will_reach_target"] is True
