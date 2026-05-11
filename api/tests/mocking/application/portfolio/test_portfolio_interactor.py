from datetime import datetime
from uuid import uuid4

import pytest

from application.portfolio import portfolio_interactor as portfolio_module
from domain.entities.models import Portfolio
from domain.ports.inbound.use_cases import CreatePortfolioRequest
from domain.value_objects.money import Currency


class FakePortfolioRepository:
    def __init__(self, *_args, **_kwargs):
        self.portfolios = {}
        self.added = []
        self.updated = []
        self.deleted = []

    async def add(self, portfolio: Portfolio) -> None:
        self.portfolios[portfolio.id] = portfolio
        self.added.append(portfolio)

    async def get_by_id(self, portfolio_id):
        return self.portfolios.get(portfolio_id)

    async def list_by_user(self, user_id):
        return [p for p in self.portfolios.values() if p.user_id == user_id]

    async def update(self, portfolio: Portfolio) -> None:
        self.portfolios[portfolio.id] = portfolio
        self.updated.append(portfolio)

    async def delete(self, portfolio_id) -> None:
        self.deleted.append(portfolio_id)
        self.portfolios.pop(portfolio_id, None)


def _portfolio_repo(monkeypatch):
    repo = FakePortfolioRepository()
    monkeypatch.setattr(portfolio_module, "PortfolioRepository", lambda session: repo)
    return repo


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_create_portfolio_adds_portfolio_and_returns_id(monkeypatch):
    repo = _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())
    user_id = uuid4()
    request = CreatePortfolioRequest(
        name="Retirement",
        base_currency=Currency.USD,
        description="Long-term holdings",
    )

    portfolio_id = await interactor.create_portfolio(request, user_id)

    assert portfolio_id == repo.added[0].id
    assert repo.added[0].user_id == user_id
    assert repo.added[0].name == "Retirement"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_get_portfolio_returns_serialized_data(monkeypatch):
    repo = _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Income",
        base_currency=Currency.EUR,
        description="Dividend-focused",
        created_at=datetime(2024, 1, 1, 10, 0),
        updated_at=datetime(2024, 1, 2, 10, 0),
    )
    repo.portfolios[portfolio.id] = portfolio

    result = await interactor.get_portfolio(portfolio.id)

    assert result == {
        "id": str(portfolio.id),
        "user_id": str(portfolio.user_id),
        "name": "Income",
        "base_currency": "EUR",
        "description": "Dividend-focused",
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-01-02T10:00:00",
    }


@pytest.mark.asyncio
@pytest.mark.grumpy_path
async def test_get_portfolio_raises_when_missing(monkeypatch):
    _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())

    with pytest.raises(ValueError, match="Portfolio"):
        await interactor.get_portfolio(uuid4())


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_list_portfolios_returns_only_user_items(monkeypatch):
    repo = _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())
    user_id = uuid4()
    repo.portfolios[uuid4()] = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Core",
        base_currency=Currency.USD,
    )
    repo.portfolios[uuid4()] = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Other",
        base_currency=Currency.USD,
    )

    result = await interactor.list_portfolios(user_id)

    assert len(result) == 1
    assert result[0]["name"] == "Core"


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_update_portfolio_mutates_existing_record(monkeypatch):
    repo = _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Growth",
        base_currency=Currency.USD,
    )
    repo.portfolios[portfolio.id] = portfolio

    await interactor.update_portfolio(
        portfolio.id, name="Growth Plus", description="Updated"
    )

    updated = repo.portfolios[portfolio.id]
    assert updated.name == "Growth Plus"
    assert updated.description == "Updated"
    assert repo.updated[0].id == portfolio.id


@pytest.mark.asyncio
@pytest.mark.happy_path
async def test_delete_portfolio_removes_record(monkeypatch):
    repo = _portfolio_repo(monkeypatch)
    interactor = portfolio_module.PortfolioInteractor(session=object())
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="To Remove",
        base_currency=Currency.USD,
    )
    repo.portfolios[portfolio.id] = portfolio

    await interactor.delete_portfolio(portfolio.id)

    assert portfolio.id not in repo.portfolios
    assert repo.deleted == [portfolio.id]
