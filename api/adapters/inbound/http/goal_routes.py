from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import get_current_user
from application.goals.goal_interactor import GoalInteractor
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreateGoalRequest
from domain.value_objects.money import Currency
from infrastructure.db.session import get_session

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalBody(BaseModel):
    name: str
    target_net_worth: float
    target_net_worth_currency: str
    target_date: date
    monthly_savings: float
    monthly_savings_currency: str
    expected_annual_return: float


def _body_to_request(body: GoalBody, user_id: UUID) -> CreateGoalRequest:
    return CreateGoalRequest(
        user_id=user_id,
        name=body.name,
        target_net_worth=round(body.target_net_worth * 100),
        target_net_worth_currency=Currency(body.target_net_worth_currency),
        target_date=body.target_date,
        monthly_savings=round(body.monthly_savings * 100),
        monthly_savings_currency=Currency(body.monthly_savings_currency),
        expected_annual_return=round(body.expected_annual_return * 100),
    )


@router.get("/")
async def list_goals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        goals = await interactor.list_goals(current_user.id)
        return goals
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: GoalBody,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        goal_id = await interactor.create_goal(_body_to_request(body, current_user.id))
        await session.commit()

        goal = await interactor.get_goal(goal_id)
        return goal
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{goal_id}")
async def get_goal(
    goal_id: UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        goal = await interactor.get_goal(goal_id)
        return goal
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{goal_id}")
async def update_goal(
    goal_id: UUID,
    body: GoalBody,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        await interactor.update_goal(goal_id, _body_to_request(body, current_user.id))
        await session.commit()

        goal = await interactor.get_goal(goal_id)
        return goal
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        await interactor.delete_goal(goal_id)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{goal_id}/projection")
async def get_projection(
    goal_id: UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = GoalInteractor(session)
        projection = await interactor.get_projection(goal_id)
        return projection
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
