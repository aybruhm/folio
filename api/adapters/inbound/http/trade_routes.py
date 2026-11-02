import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.inbound.http.dependencies import get_current_user
from application.portfolio.portfolio_interactor import PortfolioInteractor
from application.trades.csv_import_interactor import CsvImportInteractor
from application.trades.trade_interactor import BulkTradeError, TradeInteractor
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import QUANTITY_SCALE, AssetClass, Currency, TradeType
from infrastructure.db.session import get_session

router = APIRouter(prefix="/trades", tags=["trades"])


# Each row may look up market data for its ticker, so keep one request bounded.
MAX_BULK_TRADES = 50


class TradeFields(BaseModel):
    ticker: str
    trade_type: str
    trade_date: datetime
    quantity: Decimal
    price: Decimal
    trade_currency: str
    fees: Decimal = Decimal(0)
    notes: str | None = None
    asset_class: str | None = None
    market_data_provider: str = "yfinance"


class TradeBody(TradeFields):
    portfolio_id: UUID


class BulkTradeBody(BaseModel):
    portfolio_id: UUID
    trades: list[TradeFields] = Field(min_length=1, max_length=MAX_BULK_TRADES)


class BulkDeleteRequest(BaseModel):
    trade_ids: list[UUID]


def _body_to_request(body: TradeBody) -> CreateTradeRequest:
    return _fields_to_request(body, body.portfolio_id)


def _fields_to_request(body: TradeFields, portfolio_id: UUID) -> CreateTradeRequest:
    return CreateTradeRequest(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        trade_type=TradeType(body.trade_type),
        trade_date=body.trade_date,
        quantity=round(body.quantity * QUANTITY_SCALE),
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
    ticker: str | None = None,
    trade_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
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


async def _require_portfolio_access(
    session: AsyncSession, portfolio_id: UUID, user: User
) -> None:
    try:
        portfolio = await PortfolioInteractor(session).get_portfolio(portfolio_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.get("user_id") != str(user.id):
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def create_trades_bulk(
    body: BulkTradeBody,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create several trades in one portfolio, all or none.

    If any row is rejected nothing is saved, and the 422 response lists every
    rejected row as details.errors = [{"index": <row position>, "message": ...}].
    """
    try:
        await _require_portfolio_access(session, body.portfolio_id, current_user)

        requests: list[CreateTradeRequest] = []
        errors: list[dict] = []
        for index, row in enumerate(body.trades):
            try:
                requests.append(_fields_to_request(row, body.portfolio_id))
            except ValueError as e:
                errors.append({"index": index, "message": str(e)})
        if errors:
            raise BulkTradeError(errors)

        interactor = TradeInteractor(session)
        trade_ids = await interactor.create_trades(requests)
        await session.commit()

        trades = [await interactor.get_trade(trade_id) for trade_id in trade_ids]
        return {"created": len(trades), "trades": trades}
    except HTTPException:
        await session.rollback()
        raise
    except BulkTradeError as e:
        await session.rollback()
        return JSONResponse(
            status_code=422,
            content={
                "message": "No trades were saved. Fix the rows listed and try again.",
                "code": "bulk_trade_invalid",
                "details": {"errors": e.errors},
            },
        )
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
    profile_name: str | None = Form(None),
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
