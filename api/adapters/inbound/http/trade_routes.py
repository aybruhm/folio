import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from adapters.inbound.http.dependencies import (
    get_csv_import_service,
    get_trade_service,
    get_current_user,
    invalidate_benchmark_cache,
)
from application.trades.csv_import_interactor import CsvImportInteractor
from application.trades.csv_import_service import CsvImportService
from application.trades.trade_interactor import TradeInteractor
from application.trades.trade_service import TradeService
from domain.entities.models import User
from domain.ports.inbound.use_cases import CreateTradeRequest
from domain.value_objects.money import QUANTITY_SCALE, AssetClass, Currency, TradeType

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
    service: TradeService = Depends(get_trade_service),
):
    try:
        trade_type_enum = TradeType(trade_type) if trade_type else None
        trades, total = await service.list_trades(
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


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(invalidate_benchmark_cache)])
async def create_trade(
    body: TradeBody,
    _: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        return await service.create(_body_to_request(body))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk", status_code=status.HTTP_201_CREATED, dependencies=[Depends(invalidate_benchmark_cache)])
async def create_trades_bulk(
    body: BulkTradeBody,
    current_user: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        await service.ensure_portfolio_access(body.portfolio_id, current_user.id)

        requests: list[tuple[int, CreateTradeRequest]] = []
        errors: list[dict] = []
        for index, row in enumerate(body.trades):
            try:
                requests.append(
                    (index, _fields_to_request(row, body.portfolio_id))
                )
            except ValueError as e:
                errors.append({"index": index, "message": str(e)})

        result = await service.create_bulk(requests)
        errors.extend(result["errors"])
        return {
            "created": len(result["trades"]),
            "trades": result["trades"],
            "failed": len(errors),
            "errors": errors,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trade_id}")
async def get_trade(
    trade_id: UUID,
    _: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        return await service.get(trade_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{trade_id}", dependencies=[Depends(invalidate_benchmark_cache)])
async def update_trade(
    trade_id: UUID,
    body: TradeBody,
    _: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        return await service.update(trade_id, _body_to_request(body))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(invalidate_benchmark_cache)])
async def delete_trade(
    trade_id: UUID,
    _: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        await service.delete(trade_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk/delete", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(invalidate_benchmark_cache)])
async def bulk_delete_trades(
    request: BulkDeleteRequest,
    _: User = Depends(get_current_user),
    service: TradeService = Depends(get_trade_service),
):
    try:
        await service.delete_batch(request.trade_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/validate")
async def validate_csv(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    date_format: str = Form(...),
    _: User = Depends(get_current_user),
    service: CsvImportService = Depends(get_csv_import_service),
):
    try:
        content = await file.read()
        mapping_dict = json.loads(mapping)
        validation = await service.validate_mapping(
            content, file.filename or "upload.csv", mapping_dict, date_format
        )
        return validation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/confirm", dependencies=[Depends(invalidate_benchmark_cache)])
async def confirm_import(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    portfolio_id: UUID = Form(...),
    date_format: str = Form(...),
    profile_name: str | None = Form(None),
    market_data_provider: str = Form("yfinance"),
    _: User = Depends(get_current_user),
    service: CsvImportService = Depends(get_csv_import_service),
):
    try:
        content = await file.read()
        mapping_dict = json.loads(mapping)
        result = await service.confirm_import(
            content,
            file.filename or "upload.csv",
            mapping_dict,
            date_format,
            portfolio_id,
            profile_name,
            market_data_provider,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
