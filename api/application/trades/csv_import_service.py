from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from application.trades.csv_import_interactor import CsvImportInteractor


class CsvImportUnitOfWork(Protocol):
    interactor: CsvImportInteractor

    async def __aenter__(self) -> "CsvImportUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...


class CsvImportService:
    def __init__(self, unit_of_work_factory: Callable[[], CsvImportUnitOfWork]):
        self.unit_of_work_factory = unit_of_work_factory

    async def validate_mapping(
        self, content: bytes, filename: str, mapping: dict, date_format: str
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.validate_mapping(
                content, filename, mapping, date_format
            )

    async def confirm_import(
        self,
        content: bytes,
        filename: str,
        mapping: dict,
        date_format: str,
        portfolio_id: UUID,
        profile_name: str | None = None,
        market_data_provider: str = "yfinance",
    ) -> dict:
        async with self.unit_of_work_factory() as unit_of_work:
            return await unit_of_work.interactor.confirm_import(
                content,
                filename,
                mapping,
                date_format,
                portfolio_id,
                profile_name,
                market_data_provider,
            )
