import json
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import get_current_user
from application.trades.csv_import_interactor import CsvImportInteractor
from application.trades.trade_interactor import TradeInteractor
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import AssetClass, Currency, TradeType
from infrastructure.db.session import get_session

router = APIRouter(prefix="/trades", tags=["trades"])


class TradeBody(BaseModel):
    portfolio_id: UUID
    ticker: str
    trade_type: str
    trade_date: datetime
    quantity: Decimal
    price: Decimal
    trade_currency: str
    fees: Decimal = Decimal("0")
    notes: Optional[str] = None
    asset_class: Optional[str] = None
    market_data_provider: str = "yfinance"


class BulkDeleteRequest(BaseModel):
    trade_ids: list[UUID]


def _body_to_request(body: TradeBody) -> CreateTradeRequest:
    return CreateTradeRequest(
        portfolio_id=body.portfolio_id,
        ticker=body.ticker,
        trade_type=TradeType(body.trade_type),
        trade_date=body.trade_date,
        quantity=round(body.quantity * 10000),
        price=round(body.price * 100),
        trade_currency=Currency(body.trade_currency),
        fees=round(body.fees * 100),
        notes=body.notes,
        asset_class=AssetClass(body.asset_class) if body.asset_class else None,
        market_data_provider=body.market_data_provider,
    )


@router.get("/")
async def list_trades(
    portfolio_id: UUID,
    ticker: Optional[str] = None,
    trade_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = TradeInteractor(session)
        trade_type_enum = TradeType(trade_type) if trade_type else None
        trades, total = await interactor.list_trades(
            portfolio_id,
            ticker,
            trade_type_enum,
            start_date,
            end_date,
            skip,
            limit,
        )
        return {"data": trades, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_trade(
    body: TradeBody,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = TradeInteractor(session)
        trade_id = await interactor.create_trade(_body_to_request(body))
        await session.commit()

        trade = await interactor.get_trade(trade_id)
        return trade
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trade_id}")
async def get_trade(
    trade_id: UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
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
    body: TradeBody,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = TradeInteractor(session)
        await interactor.update_trade(trade_id, _body_to_request(body))
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
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
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


@router.post("/bulk/delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_trades(
    request: BulkDeleteRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        interactor = TradeInteractor(session)
        await interactor.delete_batch_trades(request.trade_ids)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/validate")
async def validate_csv(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    date_format: str = Form(...),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        content = await file.read()
        mapping_dict = json.loads(mapping)
        interactor = CsvImportInteractor(session)
        validation = await interactor.validate_mapping(
            content, file.filename or "upload.csv", mapping_dict, date_format
        )
        return validation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/confirm")
async def confirm_import(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    portfolio_id: UUID = Form(...),
    date_format: str = Form(...),
    profile_name: Optional[str] = Form(None),
    market_data_provider: str = Form("yfinance"),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        content = await file.read()
        mapping_dict = json.loads(mapping)
        interactor = CsvImportInteractor(session)
        result = await interactor.confirm_import(
            content,
            file.filename or "upload.csv",
            mapping_dict,
            date_format,
            portfolio_id,
            profile_name,
            market_data_provider,
        )
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
