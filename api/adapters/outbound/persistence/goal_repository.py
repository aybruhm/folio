from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from decimal import Decimal

from domain.entities.models import Goal
from domain.value_objects.money import Currency, Money
from domain.ports.outbound.repositories import IGoalRepository
from infrastructure.db.models import GoalModel

class GoalRepository(IGoalRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, goal: Goal) -> None:
        model = GoalModel(
            id=goal.id,
            portfolio_id=goal.portfolio_id,
            name=goal.name,
            target_net_worth=goal.target_net_worth.amount,
            target_net_worth_currency=goal.target_net_worth.currency.value,
            target_date=goal.target_date,
            monthly_savings=goal.monthly_savings.amount,
            monthly_savings_currency=goal.monthly_savings.currency.value,
            expected_annual_return=goal.expected_annual_return,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
    
    async def get_by_id(self, goal_id: UUID) -> Optional[Goal]:
        model = await self.session.get(GoalModel, goal_id)
        return self._to_domain(model) if model else None
    
    async def list_by_portfolio(self, portfolio_id: UUID) -> List[Goal]:
        result = await self.session.execute(
            select(GoalModel)
            .where(GoalModel.portfolio_id == portfolio_id)
            .order_by(GoalModel.target_date.asc())
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]
    
    async def update(self, goal: Goal) -> None:
        model = await self.session.get(GoalModel, goal.id)
        if model:
            model.name = goal.name
            model.target_net_worth = goal.target_net_worth.amount
            model.target_date = goal.target_date
            model.monthly_savings = goal.monthly_savings.amount
            model.expected_annual_return = goal.expected_annual_return
            model.updated_at = goal.updated_at
            await self.session.flush()
    
    async def delete(self, goal_id: UUID) -> None:
        model = await self.session.get(GoalModel, goal_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()
    
    @staticmethod
    def _to_domain(model: GoalModel) -> Goal:
        return Goal(
            id=model.id,
            portfolio_id=model.portfolio_id,
            name=model.name,
            target_net_worth=Money(
                Decimal(str(model.target_net_worth)),
                Currency(model.target_net_worth_currency)
            ),
            target_date=model.target_date,
            monthly_savings=Money(
                Decimal(str(model.monthly_savings)),
                Currency(model.monthly_savings_currency)
            ),
            expected_annual_return=Decimal(str(model.expected_annual_return)),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
