from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from uuid import UUID
from typing import List, Optional
from datetime import date

from domain.value_objects.money import TradeType, Currency
from domain.ports.inbound.use_cases import CreateTradeRequest
from application.trades.trade_interactor import TradeInteractor
from application.trades.csv_import_interactor import CsvImportInteractor
from infrastructure.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])

@router.get("/")
async def list_trades(
    portfolio_id: UUID,
    ticker: Optional[str] = None,
    trade_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = TradeInteractor(session)
        trade_type_enum = TradeType(trade_type) if trade_type else None
        trades, total = await interactor.list_trades(
            portfolio_id, ticker, trade_type_enum, start_date, end_date, skip, limit
        )
        return {'data': trades, 'total': total, 'skip': skip, 'limit': limit}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_trade(
    request: CreateTradeRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = TradeInteractor(session)
        trade_id = await interactor.create_trade(request)
        await session.commit()
        
        trade = await interactor.get_trade(trade_id)
        return trade
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{trade_id}")
async def get_trade(
    trade_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = TradeInteractor(session)
        trade = await interactor.get_trade(trade_id)
        return trade
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{trade_id}")
async def update_trade(
    trade_id: UUID,
    request: CreateTradeRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = TradeInteractor(session)
        await interactor.update_trade(trade_id, request)
        await session.commit()
        
        trade = await interactor.get_trade(trade_id)
        return trade
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        interactor = TradeInteractor(session)
        await interactor.delete_trade(trade_id)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/preview")
async def preview_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        content = await file.read()
        interactor = CsvImportInteractor(session)
        preview = await interactor.preview_csv(content, file.filename)
        return preview
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/validate")
async def validate_csv(
    mapping: dict,
    date_format: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        content = await file.read()
        interactor = CsvImportInteractor(session)
        validation = await interactor.validate_mapping(content, file.filename, mapping, date_format)
        return validation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import/confirm")
async def confirm_import(
    portfolio_id: UUID,
    mapping: dict,
    date_format: str,
    profile_name: Optional[str] = None,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        content = await file.read()
        interactor = CsvImportInteractor(session)
        result = await interactor.confirm_import(
            content, file.filename, mapping, date_format, portfolio_id, profile_name
        )
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
