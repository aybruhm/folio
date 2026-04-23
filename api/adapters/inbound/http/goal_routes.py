from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from application.goals.goal_interactor import GoalInteractor
from domain.ports.inbound.use_cases import CreateGoalRequest
from infrastructure.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

@router.get("/")
async def list_goals(
    portfolio_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = GoalInteractor(session)
        goals = await interactor.list_goals(portfolio_id)
        return goals
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_goal(
    request: CreateGoalRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = GoalInteractor(session)
        goal_id = await interactor.create_goal(request)
        await session.commit()
        
        goal = await interactor.get_goal(goal_id)
        return goal
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{goal_id}")
async def get_goal(
    goal_id: UUID,
    session: AsyncSession = Depends(get_session)
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
    request: CreateGoalRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = GoalInteractor(session)
        await interactor.update_goal(goal_id, request)
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
    session: AsyncSession = Depends(get_session)
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
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = GoalInteractor(session)
        projection = await interactor.get_projection(goal_id)
        return projection
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
