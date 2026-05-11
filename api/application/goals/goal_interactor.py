from dataclasses import replace
from datetime import date, datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.persistence.goal_repository import GoalRepository
from domain.entities.models import Goal
from domain.ports.inbound.use_cases import CreateGoalRequest, IGoalUseCase
from domain.ports.outbound.repositories import IGoalRepository
from domain.services.performance import FIREService


class GoalInteractor(IGoalUseCase):
    def __init__(self, session: AsyncSession):
        self.repository: IGoalRepository = GoalRepository(session)

    async def create_goal(self, request: CreateGoalRequest) -> UUID:
        goal = Goal(
            id=uuid4(),
            portfolio_id=request.portfolio_id,
            name=request.name,
            target_net_worth=request.target_net_worth,
            target_net_worth_currency=request.target_net_worth_currency,
            target_date=request.target_date,
            monthly_savings=request.monthly_savings,
            monthly_savings_currency=request.monthly_savings_currency,
            expected_annual_return=request.expected_annual_return,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await self.repository.add(goal)
        return goal.id

    async def get_goal(self, goal_id: UUID) -> dict:
        goal = await self.repository.get_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        return self._goal_to_dict(goal)

    async def list_goals(self, portfolio_id: UUID) -> List[dict]:
        goals = await self.repository.list_by_portfolio(portfolio_id)
        return [self._goal_to_dict(g) for g in goals]

    async def update_goal(self, goal_id: UUID, request: CreateGoalRequest) -> None:
        goal = await self.repository.get_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        updated_goal = replace(
            goal,
            name=request.name,
            target_net_worth=request.target_net_worth,
            target_net_worth_currency=request.target_net_worth_currency,
            target_date=request.target_date,
            monthly_savings=request.monthly_savings,
            monthly_savings_currency=request.monthly_savings_currency,
            expected_annual_return=request.expected_annual_return,
            updated_at=datetime.now(),
        )

        await self.repository.update(updated_goal)

    async def delete_goal(self, goal_id: UUID) -> None:
        goal = await self.repository.get_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        await self.repository.delete(goal_id)

    async def get_projection(self, goal_id: UUID) -> dict:
        goal = await self.repository.get_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        today = date.today()
        days_to_target = (goal.target_date - today).days
        months_to_target = max(1, days_to_target // 30)

        target_value = goal.target_net_worth / 100
        monthly_savings = goal.monthly_savings / 100
        annual_return = goal.expected_annual_return / 100

        projection = FIREService.calculate_projection(
            current_value=monthly_savings,
            target_value=target_value,
            monthly_savings=monthly_savings,
            annual_return=annual_return,
            target_months=months_to_target,
        )

        required_return = FIREService.calculate_required_return(
            current_value=monthly_savings,
            target_value=target_value,
            monthly_savings=monthly_savings,
            target_months=months_to_target,
        )

        return {
            "goal_id": str(goal.id),
            "name": goal.name,
            "current_value": str(monthly_savings),
            "target_value": str(target_value),
            "target_date": goal.target_date.isoformat(),
            "days_remaining": max(0, days_to_target),
            "projected_value": str(projection["projected_value"]),
            "shortfall": str(projection["shortfall"]),
            "progress_percent": str(projection["progress_percent"]),
            "will_reach_target": projection.get("will_reach_target", False),
            "required_annual_return": str(required_return)
            if required_return is not None
            else None,
            "expected_annual_return": str(annual_return),
        }

    @staticmethod
    def _goal_to_dict(goal: Goal) -> dict:
        return {
            "id": str(goal.id),
            "portfolio_id": str(goal.portfolio_id),
            "name": goal.name,
            "target_net_worth": goal.target_net_worth / 100,
            "target_net_worth_currency": goal.target_net_worth_currency.value,
            "target_date": goal.target_date.isoformat(),
            "monthly_savings": goal.monthly_savings / 100,
            "monthly_savings_currency": goal.monthly_savings_currency.value,
            "expected_annual_return": goal.expected_annual_return / 100,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat(),
        }
