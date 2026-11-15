from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from application.goals.goal_interactor import GoalInteractor
from domain.ports.inbound.use_cases import CreateGoalRequest


class GoalUnitOfWork(Protocol):
    interactor: GoalInteractor

    async def __aenter__(self) -> "GoalUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class GoalService:
    def __init__(self, unit_of_work_factory: Callable[[], GoalUnitOfWork]):
        self.unit_of_work_factory = unit_of_work_factory

    async def list(self, user_id: UUID) -> list[dict]:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.list_goals(user_id)

    async def create(self, request: CreateGoalRequest) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            goal_id = await unit_of_work.interactor.create_goal(request)
            return await unit_of_work.interactor.get_goal(goal_id)

    async def get(self, goal_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.get_goal(goal_id)

    async def update(self, goal_id: UUID, request: CreateGoalRequest) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.update_goal(goal_id, request)
            return await unit_of_work.interactor.get_goal(goal_id)

    async def delete(self, goal_id: UUID) -> None:
        async with self.unit_of_work_factory() as unit_of_work:
            await unit_of_work.interactor.delete_goal(goal_id)

    async def projection(self, goal_id: UUID) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.get_projection(goal_id)
