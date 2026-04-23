from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import csv
import io

from domain.entities.models import Trade
from domain.value_objects.money import TradeType, Currency
from domain.ports.inbound.use_cases import ICsvImportUseCase
from domain.ports.outbound.repositories import ITradeRepository, IAssetRepository
from adapters.outbound.persistence.trade_repository import TradeRepository
from adapters.outbound.persistence.asset_repository import AssetRepository
from adapters.outbound.market_data.yfinance_adapter import YFinanceAdapter
from sqlalchemy.ext.asyncio import AsyncSession

class CsvImportInteractor(ICsvImportUseCase):
    def __init__(self, session: AsyncSession):
        self.trade_repo: ITradeRepository = TradeRepository(session)
        self.asset_repo: IAssetRepository = AssetRepository(session)
        self.yfinance = YFinanceAdapter()
    
    async def preview_csv(self, file_content: bytes, filename: str) -> dict:
        try:
            text_content = file_content.decode('utf-8')
            lines = text_content.strip().split('\n')
            
            reader = csv.DictReader(io.StringIO('\n'.join(lines[:6])))
            headers = reader.fieldnames or []
            
            sample_rows = []
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                sample_rows.append(row)
            
            return {
                'headers': headers,
                'sample_rows': sample_rows,
                'total_lines': len(lines),
            }
        except Exception as e:
            return {'error': str(e), 'headers': [], 'sample_rows': []}
    
    async def validate_mapping(
        self, file_content: bytes, filename: str, mapping: dict, date_format: str
    ) -> dict:
        try:
            text_content = file_content.decode('utf-8')
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
                    errors.append({'row': i + 2, 'error': str(e)})
            
            return {
                'valid_count': len(valid_rows),
                'error_count': len(errors),
                'errors': errors,
                'sample_valid_rows': valid_rows[:5],
            }
        except Exception as e:
            return {'error': str(e), 'valid_count': 0, 'error_count': 0, 'errors': []}
    
    async def confirm_import(
        self, file_content: bytes, filename: str, mapping: dict, date_format: str,
        portfolio_id: UUID, profile_name: Optional[str] = None
    ) -> dict:
        import_batch_id = uuid4()
        
        try:
            text_content = file_content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text_content))
            
            imported = 0
            rejected = 0
            rejection_details = []
            
            for i, row in enumerate(reader):
                try:
                    trade_data = self._map_row(row, mapping, date_format)
                    
                    trade = Trade(
                        id=uuid4(),
                        portfolio_id=portfolio_id,
                        asset_id=uuid4(),
                        ticker=trade_data['ticker'],
                        trade_type=trade_data['trade_type'],
                        trade_date=trade_data['trade_date'],
                        quantity=trade_data['quantity'],
                        price=trade_data['price'],
                        trade_currency=trade_data['currency'],
                        fees=trade_data.get('fees', Decimal('0')),
                        notes=trade_data.get('notes'),
                        source='csv_import',
                        import_batch_id=import_batch_id,
                        created_at=datetime.utcnow(),
                    )
                    
                    await self.trade_repo.add(trade)
                    imported += 1
                except Exception as e:
                    rejected += 1
                    rejection_details.append({
                        'row': i + 2,
                        'error': str(e),
                    })
            
            return {
                'import_batch_id': str(import_batch_id),
                'imported_count': imported,
                'rejected_count': rejected,
                'rejection_details': rejection_details,
            }
        except Exception as e:
            return {
                'error': str(e),
                'imported_count': 0,
                'rejected_count': 0,
                'rejection_details': [],
            }
    
    @staticmethod
    def _map_row(row: dict, mapping: dict, date_format: str) -> dict:
        from datetime import datetime as dt
        
        ticker = row.get(mapping.get('ticker', 'Ticker'), '').strip()
        if not ticker:
            raise ValueError("Missing ticker")
        
        try:
            trade_type_str = row.get(mapping.get('trade_type', 'Type'), 'buy').lower()
            trade_type = TradeType(trade_type_str)
        except (KeyError, ValueError):
            raise ValueError(f"Invalid trade type: {trade_type_str}")
        
        try:
            date_str = row.get(mapping.get('trade_date', 'Date'), '')
            trade_date = dt.strptime(date_str, date_format)
        except ValueError:
            raise ValueError(f"Cannot parse date: {date_str} with format {date_format}")
        
        try:
            quantity = Decimal(row.get(mapping.get('quantity', 'Quantity'), '0'))
            if quantity < 0:
                raise ValueError("Quantity cannot be negative")
        except:
            raise ValueError("Invalid quantity")
        
        try:
            price = Decimal(row.get(mapping.get('price', 'Price'), '0'))
            if price <= 0:
                raise ValueError("Price must be positive")
        except:
            raise ValueError("Invalid price")
        
        currency_str = row.get(mapping.get('trade_currency', 'Currency'), 'USD')
        try:
            currency = Currency(currency_str)
        except ValueError:
            raise ValueError(f"Invalid currency: {currency_str}")
        
        return {
            'ticker': ticker,
            'trade_type': trade_type,
            'trade_date': trade_date,
            'quantity': quantity,
            'price': price,
            'currency': currency,
            'fees': Decimal(row.get(mapping.get('fees', 'Fees'), '0') or '0'),
            'notes': row.get(mapping.get('notes', 'Notes')),
        }
