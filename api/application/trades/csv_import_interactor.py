import csv
import io
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from domain.entities.models import Trade
from domain.ports.inbound.use_cases import ICsvImportUseCase
from domain.ports.outbound.repositories import IAssetRepository, ITradeRepository
from domain.services.market_data import normalize_provider
from domain.value_objects.money import QUANTITY_SCALE, AssetClass, Currency, TradeType

TradeRepository = AssetRepository = None
YFinanceAdapter = TiingoAdapter = NgnMarketAdapter = NgxPulseAdapter = TradingviewAdapter = None


class _LegacyCsvMarketDataGateway:
    def __init__(self):
        self.adapters = {
            "yfinance": YFinanceAdapter,
            "tiingo": TiingoAdapter,
            "ngnmarket": NgnMarketAdapter,
            "ngxpulse": NgxPulseAdapter,
            "tradingview": TradingviewAdapter,
        }

    async def get_asset_metadata(self, ticker, currency, provider, asset_class):
        selected = normalize_provider(provider)
        order = {
            "tiingo": ["tiingo", "tradingview", "ngnmarket", "yfinance"],
            "ngnmarket": ["ngnmarket", "tradingview", "tiingo", "yfinance"],
            "tradingview": ["tradingview", "tiingo", "ngnmarket", "yfinance"],
            "ngxpulse": ["ngxpulse", "tiingo", "tradingview", "yfinance"],
            "yfinance": ["yfinance"],
        }[selected]
        for name in order:
            adapter = self.adapters[name]
            if adapter is None:
                continue
            adapter = adapter()
            if name in {"ngnmarket", "ngxpulse"}:
                metadata = await adapter.get_asset_metadata(
                    ticker, currency.value, asset_class
                )
            else:
                metadata = await adapter.get_asset_metadata(ticker, currency.value)
            if metadata:
                return metadata
        return None


class CsvImportInteractor(ICsvImportUseCase):
    def __init__(
        self,
        trade_repo: ITradeRepository | None = None,
        asset_repo: IAssetRepository | None = None,
        market_data=None,
        session=None,
    ):
        self.trade_repo = trade_repo or TradeRepository(session)
        self.asset_repo = asset_repo or AssetRepository(session)
        self.market_data = market_data or _LegacyCsvMarketDataGateway()

    async def _get_asset_metadata(
        self, ticker: str, currency: Currency, provider: str, asset_class: str = ""
    ):
        return await self.market_data.get_asset_metadata(
            ticker, currency, provider, asset_class
        )

    async def preview_csv(self, file_content: bytes, filename: str) -> dict:
        try:
            text_content = file_content.decode("utf-8")
            lines = text_content.strip().split("\n")

            reader = csv.DictReader(io.StringIO("\n".join(lines[:6])))
            headers = reader.fieldnames or []

            sample_rows = []
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                sample_rows.append(row)

            return {
                "headers": headers,
                "sample_rows": sample_rows,
                "total_lines": len(lines),
            }
        except Exception as e:
            return {"error": str(e), "headers": [], "sample_rows": []}

    async def validate_mapping(
        self, file_content: bytes, filename: str, mapping: dict, date_format: str
    ) -> dict:
        try:
            text_content = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text_content))

            errors = []
            valid_rows = []

            for i, row in enumerate(reader):
                if i >= 20:
                    break

                try:
                    trade_data = self._map_row(row, mapping, date_format)
                    valid_rows.append(trade_data)
                except ValueError as e:
                    errors.append({"row": i + 2, "error": str(e)})

            return {
                "valid_count": len(valid_rows),
                "error_count": len(errors),
                "errors": errors,
                "sample_valid_rows": valid_rows[:5],
            }
        except Exception as e:
            return {"error": str(e), "valid_count": 0, "error_count": 0, "errors": []}

    async def confirm_import(
        self,
        file_content: bytes,
        filename: str,
        mapping: dict,
        date_format: str,
        portfolio_id: UUID,
        profile_name: str | None = None,
        market_data_provider: str = "yfinance",
    ) -> dict:
        import_batch_id = uuid4()

        try:
            text_content = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text_content))

            imported = 0
            rejected = 0
            rejection_details = []

            for i, row in enumerate(reader):
                try:
                    trade_data = self._map_row(row, mapping, date_format)

                    ticker = trade_data["ticker"]
                    asset_class_str = trade_data.get("asset_class", "")
                    row_provider = (
                        trade_data.get("market_data_provider") or market_data_provider
                    )
                    selected_provider = normalize_provider(row_provider)
                    asset = await self.asset_repo.get_by_ticker(ticker)
                    if not asset:
                        from domain.entities.models import Asset

                        if asset_class_str == "cash":
                            asset = Asset(
                                id=uuid4(),
                                ticker=ticker,
                                name=ticker,
                                asset_class=AssetClass.CASH,
                                currency=trade_data["currency"],
                                market_data_provider=selected_provider,
                            )
                            await self.asset_repo.add(asset)
                        else:
                            metadata = await self._get_asset_metadata(
                                ticker,
                                trade_data["currency"],
                                row_provider,
                                asset_class_str,
                            )
                            if metadata:
                                asset = Asset.from_metadata(
                                    ticker,
                                    metadata,
                                    market_data_provider=selected_provider,
                                )
                                await self.asset_repo.add(asset)
                            else:
                                raise ValueError(
                                    f"Cannot resolve asset for ticker: {ticker}"
                                )
                    else:
                        if asset_class_str == "cash":
                            if (
                                asset.asset_class.value != "cash"
                                or asset.currency.value != trade_data["currency"].value
                                or asset.market_data_provider != selected_provider
                            ):
                                await self.asset_repo.update_classification(
                                    asset.id,
                                    "cash",
                                    trade_data["currency"].value,
                                    selected_provider,
                                )
                                asset = await self.asset_repo.get_by_ticker(ticker)
                        else:
                            metadata = await self._get_asset_metadata(
                                ticker,
                                trade_data["currency"],
                                row_provider,
                                asset_class_str,
                            )
                            if metadata and (
                                asset.asset_class.value != metadata.asset_class
                                or asset.currency.value != metadata.currency.value
                                or asset.market_data_provider != selected_provider
                            ):
                                await self.asset_repo.update_classification(
                                    asset.id,
                                    metadata.asset_class,
                                    metadata.currency.value,
                                    selected_provider,
                                )
                                asset = await self.asset_repo.get_by_ticker(ticker)
                            elif asset.market_data_provider != selected_provider:
                                await self.asset_repo.update_classification(
                                    asset.id,
                                    asset.asset_class.value,
                                    asset.currency.value,
                                    selected_provider,
                                )
                                asset = await self.asset_repo.get_by_ticker(ticker)
                    trade = Trade(
                        id=uuid4(),
                        portfolio_id=portfolio_id,
                        asset_id=asset.id,
                        ticker=ticker,
                        trade_type=trade_data["trade_type"],
                        trade_date=trade_data["trade_date"],
                        quantity=trade_data["quantity"],
                        price=trade_data["price"],
                        trade_currency=trade_data["currency"],
                        fees=trade_data.get("fees", 0),
                        notes=trade_data.get("notes"),
                        source="csv_import",
                        import_batch_id=import_batch_id,
                        market_data_provider=selected_provider,
                        created_at=datetime.now(),
                    )

                    await self.trade_repo.add(trade)
                    imported += 1
                except Exception as e:
                    rejected += 1
                    rejection_details.append(
                        {
                            "row": i + 2,
                            "error": str(e),
                        }
                    )

            return {
                "import_batch_id": str(import_batch_id),
                "imported_count": imported,
                "rejected_count": rejected,
                "rejection_details": rejection_details,
            }
        except Exception as e:
            return {
                "error": str(e),
                "imported_count": 0,
                "rejected_count": 0,
                "rejection_details": [],
            }

    @staticmethod
    def _map_row(row: dict, mapping: dict, date_format: str) -> dict:
        from datetime import datetime as dt

        ticker = row.get(mapping.get("ticker", "Ticker"), "").strip()
        if not ticker:
            raise ValueError("Missing ticker")

        trade_type_str = row.get(mapping.get("trade_type", "Type"), "buy").lower()
        try:
            trade_type = TradeType(trade_type_str)
        except (KeyError, ValueError):
            raise ValueError(f"Invalid trade type: {trade_type_str}")

        date_str = row.get(mapping.get("trade_date", "Date"), "")
        try:
            trade_date = dt.strptime(date_str, date_format)
        except ValueError:
            raise ValueError(f"Cannot parse date: {date_str} with format {date_format}")

        try:
            quantity = round(
                Decimal(row.get(mapping.get("quantity", "Quantity"), "0").strip())
                * QUANTITY_SCALE
            )
            if quantity < 0:
                raise ValueError("Quantity cannot be negative")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid quantity")

        try:
            price = round(float(row.get(mapping.get("price", "Price"), "0")) * 100)
            if price <= 0:
                raise ValueError("Price must be positive")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid price")

        currency_str = row.get(mapping.get("trade_currency", "Currency"), "USD")
        try:
            currency = Currency(currency_str)
        except ValueError:
            raise ValueError(f"Invalid currency: {currency_str}")

        asset_class_raw = (
            row.get(mapping.get("asset_class", "Asset Class"), "").strip().lower()
        )
        provider_raw = (
            row.get(
                mapping.get("market_data_provider", "Market Data Provider"),
                "yfinance",
            )
            .strip()
            .lower()
        )

        return {
            "ticker": ticker,
            "trade_type": trade_type,
            "trade_date": trade_date,
            "quantity": quantity,
            "price": price,
            "currency": currency,
            "fees": round(
                float(row.get(mapping.get("fees", "Fees"), "0") or "0") * 100
            ),
            "notes": row.get(mapping.get("notes", "Notes")),
            "asset_class": asset_class_raw,
            "market_data_provider": provider_raw,
        }
