from uuid import UUID, uuid4
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from domain.entities.models import Goal
from domain.value_objects.money import Money, Currency
from domain.ports.inbound.use_cases import IGoalUseCase, CreateGoalRequest
from domain.ports.outbound.repositories import IGoalRepository
from domain.services.performance import FIREService
from adapters.outbound.persistence.goal_repository import GoalRepository
from sqlalchemy.ext.asyncio import AsyncSession

class GoalInteractor(IGoalUseCase):
    def __init__(self, session: AsyncSession):
        self.repository: IGoalRepository = GoalRepository(session)
    
    async def create_goal(self, request: CreateGoalRequest) -> UUID:
        target_net_worth = Money(request.target_net_worth, request.target_net_worth_currency)
        monthly_savings = Money(request.monthly_savings, request.monthly_savings_currency)
        
        if target_net_worth.currency != monthly_savings.currency:
            raise ValueError("Target net worth and monthly savings must use the same currency")
        
        goal = Goal(
            id=uuid4(),
            portfolio_id=request.portfolio_id,
            name=request.name,
            target_net_worth=target_net_worth,
            target_date=request.target_date,
            monthly_savings=monthly_savings,
            expected_annual_return=request.expected_annual_return,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
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
        
        goal.name = request.name
        goal.target_net_worth = Money(request.target_net_worth, request.target_net_worth_currency)
        goal.target_date = request.target_date
        goal.monthly_savings = Money(request.monthly_savings, request.monthly_savings_currency)
        goal.expected_annual_return = request.expected_annual_return
        goal.updated_at = datetime.utcnow()
        
        await self.repository.update(goal)
    
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
        
        projection = FIREService.calculate_projection(
            current_value=goal.monthly_savings.amount,
            target_value=goal.target_net_worth.amount,
            monthly_savings=goal.monthly_savings.amount,
            annual_return=goal.expected_annual_return,
            target_months=months_to_target,
        )
        
        required_return = await self._calculate_required_return(
            current_value=goal.monthly_savings.amount,
            target_value=goal.target_net_worth.amount,
            monthly_savings=goal.monthly_savings.amount,
            months=months_to_target,
        )
        
        return {
            'goal_id': str(goal.id),
            'name': goal.name,
            'current_value': str(goal.monthly_savings.amount),
            'target_value': str(goal.target_net_worth.amount),
            'target_date': goal.target_date.isoformat(),
            'days_remaining': max(0, days_to_target),
            'projected_value': str(projection['projected_value']),
            'shortfall': str(projection['shortfall']),
            'progress_percent': str(projection['progress_percent']),
            'will_reach_target': projection['will_reach_target'],
            'required_annual_return': str(required_return) if required_return else None,
            'expected_annual_return': str(goal.expected_annual_return),
        }
    
    @staticmethod
    def _goal_to_dict(goal: Goal) -> dict:
        return {
            'id': str(goal.id),
            'portfolio_id': str(goal.portfolio_id),
            'name': goal.name,
            'target_net_worth': str(goal.target_net_worth.amount),
            'target_net_worth_currency': goal.target_net_worth.currency.value,
            'target_date': goal.target_date.isoformat(),
            'monthly_savings': str(goal.monthly_savings.amount),
            'monthly_savings_currency': goal.monthly_savings.currency.value,
            'expected_annual_return': str(goal.expected_annual_return),
            'created_at': goal.created_at.isoformat(),
            'updated_at': goal.updated_at.isoformat(),
        }
    
    @staticmethod
    async def _calculate_required_return(
        current_value: Decimal,
        target_value: Decimal,
        monthly_savings: Decimal,
        months: int,
    ) -> Optional[Decimal]:
        return FIREService.calculate_required_return(
            current_value, target_value, monthly_savings, months
        )
