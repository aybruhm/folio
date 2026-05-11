from uuid import uuid4

import pytest

from adapters.inbound.http import trade_routes
from domain.value_objects.money import Currency, TradeType


class FakeTradeInteractor:
    def __init__(self, mode="happy"):
        self.mode = mode
        self.trade_id = uuid4()
        self.last_create = None
        self.last_update = None

    async def list_trades(
        self,
        portfolio_id=None,
        ticker=None,
        trade_type=None,
        start_date=None,
        end_date=None,
        skip=0,
        limit=100,
    ):
        return (
            [
                {
                    "id": str(self.trade_id),
                    "portfolio_id": str(portfolio_id),
                    "asset_id": str(uuid4()),
                    "ticker": ticker or "AAPL",
                    "trade_type": (trade_type.value if trade_type else "buy"),
                    "trade_date": "2024-01-01T09:30:00",
                    "quantity": 10.0,
                    "price": 185.2,
                    "trade_currency": "USD",
                    "fees": 0.0,
                    "notes": None,
                    "created_at": "2024-01-01T09:30:00",
                }
            ],
            1,
        )

    async def create_trade(self, request):
        if self.mode == "create-error":
            raise RuntimeError("create failed")
        self.last_create = request
        return self.trade_id

    async def get_trade(self, trade_id):
        if self.mode == "missing":
            raise ValueError(f"Trade {trade_id} not found")
        return {
            "id": str(trade_id),
            "portfolio_id": str(uuid4()),
            "asset_id": str(uuid4()),
            "ticker": "AAPL",
            "trade_type": "buy",
            "trade_date": "2024-01-01T09:30:00",
            "quantity": 10.0,
            "price": 185.2,
            "trade_currency": "USD",
            "fees": 4.95,
            "notes": None,
            "created_at": "2024-01-01T09:30:00",
        }

    async def update_trade(self, trade_id, request):
        if self.mode == "missing":
            raise ValueError(f"Trade {trade_id} not found")
        if self.mode == "update-error":
            raise RuntimeError("update failed")
        self.last_update = (trade_id, request)

    async def delete_trade(self, trade_id):
        if self.mode == "missing":
            raise ValueError(f"Trade {trade_id} not found")
        if self.mode == "delete-error":
            raise RuntimeError("delete failed")

    async def delete_batch_trades(self, trade_ids):
        if self.mode == "delete-error":
            raise RuntimeError("delete failed")
        return len(trade_ids)


class FakeCsvImportInteractor:
    def __init__(self, mode="happy"):
        self.mode = mode
        self.validated = None
        self.confirmed = None

    async def validate_mapping(self, content, filename, mapping, date_format):
        self.validated = (content, filename, mapping, date_format)
        return {
            "valid_count": 1,
            "error_count": 0,
            "errors": [],
            "sample_valid_rows": [{"ticker": "AAPL"}],
        }

    async def confirm_import(
        self, content, filename, mapping, date_format, portfolio_id, profile_name=None
    ):
        self.confirmed = (
            content,
            filename,
            mapping,
            date_format,
            portfolio_id,
            profile_name,
        )
        return {
            "import_batch_id": str(uuid4()),
            "imported_count": 1,
            "rejected_count": 0,
            "rejection_details": [],
        }


def _patch_trade_interactor(monkeypatch, interactor):
    monkeypatch.setattr(trade_routes, "TradeInteractor", lambda session: interactor)


def _patch_csv_interactor(monkeypatch, interactor):
    monkeypatch.setattr(trade_routes, "CsvImportInteractor", lambda session: interactor)


@pytest.mark.integration
@pytest.mark.happy_path
@pytest.mark.parametrize(
    "method,path,body,params,expected_status",
    [
        (
            "get",
            "/api/v1/trades/",
            None,
            {"portfolio_id": str(uuid4()), "ticker": "AAPL", "trade_type": "buy"},
            200,
        ),
        (
            "post",
            "/api/v1/trades/",
            {
                "portfolio_id": str(uuid4()),
                "ticker": "AAPL",
                "trade_type": "buy",
                "trade_date": "2024-01-01T09:30:00",
                "quantity": 10,
                "price": 185.2,
                "trade_currency": "USD",
            },
            None,
            201,
        ),
        ("get", "/api/v1/trades/{id}", None, None, 200),
        (
            "put",
            "/api/v1/trades/{id}",
            {
                "portfolio_id": str(uuid4()),
                "ticker": "AAPL",
                "trade_type": "sell",
                "trade_date": "2024-01-02T09:30:00",
                "quantity": 7.5,
                "price": 190.0,
                "trade_currency": "EUR",
                "fees": 2.5,
            },
            None,
            200,
        ),
        ("delete", "/api/v1/trades/{id}", None, None, 204),
    ],
)
def test_trade_crud_routes(
    authed_client, monkeypatch, method, path, body, params, expected_status
):
    interactor = FakeTradeInteractor()
    _patch_trade_interactor(monkeypatch, interactor)
    trade_id = interactor.trade_id
    response = authed_client.request(
        method,
        path.replace("{id}", str(trade_id)),
        json=body,
        params=params,
    )

    assert response.status_code == expected_status
    if method == "post":
        assert interactor.last_create.quantity == 100000
        assert interactor.last_create.trade_currency == Currency.USD
    if method == "put":
        assert interactor.last_update[1].quantity == 75000
        assert interactor.last_update[1].trade_type == TradeType.SELL
        assert interactor.last_update[1].asset_class is None
    if method == "get" and path.endswith("{id}"):
        assert response.json()["ticker"] == "AAPL"


@pytest.mark.integration
@pytest.mark.edge_case
@pytest.mark.parametrize(
    "path,params,expected_key",
    [
        ("/api/v1/trades/import/validate", None, "valid_count"),
        ("/api/v1/trades/import/confirm", None, "imported_count"),
    ],
)
def test_trade_import_routes(authed_client, monkeypatch, path, params, expected_key):
    interactor = FakeCsvImportInteractor()
    _patch_csv_interactor(monkeypatch, interactor)
    files = {
        "file": (
            "trades.csv",
            b"Ticker,Type,Date,Quantity,Price,Currency\nAAPL,buy,2024-01-01,10,185.20,USD\n",
            "text/csv",
        )
    }
    data = {"mapping": "{}", "date_format": "%Y-%m-%d"}
    if path.endswith("confirm"):
        data["portfolio_id"] = str(uuid4())

    response = authed_client.post(path, files=files, data=data)

    assert response.status_code == 200
    assert expected_key in response.json()


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_trade_error_paths(authed_client, monkeypatch):
    interactor = FakeTradeInteractor(mode="missing")
    _patch_trade_interactor(monkeypatch, interactor)

    missing = authed_client.get(f"/api/v1/trades/{uuid4()}")
    assert missing.status_code == 404


@pytest.mark.integration
@pytest.mark.grumpy_path
@pytest.mark.parametrize(
    "method,path", [("put", "/api/v1/trades/{id}"), ("delete", "/api/v1/trades/{id}")]
)
def test_trade_update_delete_missing_paths(authed_client, monkeypatch, method, path):
    interactor = FakeTradeInteractor(mode="missing")
    _patch_trade_interactor(monkeypatch, interactor)
    body = {
        "portfolio_id": str(uuid4()),
        "ticker": "AAPL",
        "trade_type": "sell",
        "trade_date": "2024-01-02T09:30:00",
        "quantity": 7.5,
        "price": 190.0,
        "trade_currency": "EUR",
        "fees": 2.5,
    }
    response = authed_client.request(
        method,
        path.replace("{id}", str(uuid4())),
        json=(body if method == "put" else None),
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_trade_list_rejects_invalid_trade_type_query(authed_client, monkeypatch):
    _patch_trade_interactor(monkeypatch, FakeTradeInteractor())
    response = authed_client.get(
        "/api/v1/trades/",
        params={"portfolio_id": str(uuid4()), "trade_type": "invalid"},
    )
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_trade_import_routes_reject_invalid_mapping_json(authed_client, monkeypatch):
    _patch_csv_interactor(monkeypatch, FakeCsvImportInteractor())
    files = {
        "file": (
            "trades.csv",
            b"Ticker,Type,Date,Quantity,Price,Currency\nAAPL,buy,2024-01-01,10,185.20,USD\n",
            "text/csv",
        )
    }
    validate = authed_client.post(
        "/api/v1/trades/import/validate",
        files=files,
        data={"mapping": "{", "date_format": "%Y-%m-%d"},
    )
    confirm = authed_client.post(
        "/api/v1/trades/import/confirm",
        files=files,
        data={
            "mapping": "{",
            "date_format": "%Y-%m-%d",
            "portfolio_id": str(uuid4()),
        },
    )
    assert validate.status_code == 400
    assert confirm.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_trade_create_update_delete_generic_exception_paths(authed_client, monkeypatch):
    _patch_trade_interactor(monkeypatch, FakeTradeInteractor(mode="create-error"))
    create = authed_client.post(
        "/api/v1/trades/",
        json={
            "portfolio_id": str(uuid4()),
            "ticker": "AAPL",
            "trade_type": "buy",
            "trade_date": "2024-01-01T09:30:00",
            "quantity": 10,
            "price": 185.2,
            "trade_currency": "USD",
        },
    )
    assert create.status_code == 400

    _patch_trade_interactor(monkeypatch, FakeTradeInteractor(mode="update-error"))
    update = authed_client.put(
        f"/api/v1/trades/{uuid4()}",
        json={
            "portfolio_id": str(uuid4()),
            "ticker": "AAPL",
            "trade_type": "sell",
            "trade_date": "2024-01-02T09:30:00",
            "quantity": 7.5,
            "price": 190.0,
            "trade_currency": "EUR",
            "fees": 2.5,
        },
    )
    assert update.status_code == 400

    _patch_trade_interactor(monkeypatch, FakeTradeInteractor(mode="delete-error"))
    delete = authed_client.delete(f"/api/v1/trades/{uuid4()}")
    assert delete.status_code == 400


@pytest.mark.integration
@pytest.mark.happy_path
def test_bulk_delete_trades(authed_client, monkeypatch):
    interactor = FakeTradeInteractor()
    _patch_trade_interactor(monkeypatch, interactor)
    trade_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    
    response = authed_client.post(
        "/api/v1/trades/bulk/delete",
        json={"trade_ids": trade_ids},
    )
    
    assert response.status_code == 204


@pytest.mark.integration
@pytest.mark.edge_case
def test_bulk_delete_trades_empty_list(authed_client, monkeypatch):
    interactor = FakeTradeInteractor()
    _patch_trade_interactor(monkeypatch, interactor)
    
    response = authed_client.post(
        "/api/v1/trades/bulk/delete",
        json={"trade_ids": []},
    )
    
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.grumpy_path
def test_bulk_delete_trades_error(authed_client, monkeypatch):
    interactor = FakeTradeInteractor(mode="delete-error")
    _patch_trade_interactor(monkeypatch, interactor)
    trade_ids = [str(uuid4()), str(uuid4())]
    
    response = authed_client.post(
        "/api/v1/trades/bulk/delete",
        json={"trade_ids": trade_ids},
    )
    
    assert response.status_code == 400
