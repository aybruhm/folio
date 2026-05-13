from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.entities.models import Goal
from domain.ports.outbound.repositories import IGoalRepository
from domain.value_objects.money import Currency
from infrastructure.db.models import GoalModel


class GoalRepository(IGoalRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, goal: Goal) -> None:
        model = GoalModel(
            id=goal.id,
            user_id=goal.user_id,
            name=goal.name,
            target_net_worth=goal.target_net_worth,
            target_net_worth_currency=goal.target_net_worth_currency.value,
            target_date=goal.target_date,
            monthly_savings=goal.monthly_savings,
            monthly_savings_currency=goal.monthly_savings_currency.value,
            expected_annual_return=goal.expected_annual_return,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )
        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, goal_id: UUID) -> Optional[Goal]:
        model = await self.session.get(GoalModel, goal_id)
        return self._to_domain(model) if model else None

    async def list_by_user(self, user_id: UUID) -> List[Goal]:
        result = await self.session.execute(
            select(GoalModel)
            .where(GoalModel.user_id == user_id)
            .order_by(GoalModel.target_date.asc())
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def update(self, goal: Goal) -> None:
        model = await self.session.get(GoalModel, goal.id)
        if model:
            model.name = goal.name
            model.target_net_worth = goal.target_net_worth
            model.target_net_worth_currency = goal.target_net_worth_currency.value
            model.target_date = goal.target_date
            model.monthly_savings = goal.monthly_savings
            model.monthly_savings_currency = goal.monthly_savings_currency.value
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
            user_id=model.user_id,
            name=model.name,
            target_net_worth=int(model.target_net_worth),
            target_net_worth_currency=Currency(model.target_net_worth_currency),
            target_date=model.target_date,
            monthly_savings=int(model.monthly_savings),
            monthly_savings_currency=Currency(model.monthly_savings_currency),
            expected_annual_return=int(model.expected_annual_return),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
