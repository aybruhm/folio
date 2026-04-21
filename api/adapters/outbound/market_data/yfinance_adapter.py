import yfinance as yf
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
import logging

from api.domain.value_objects.money import Currency, AssetMetadata
from api.domain.ports.outbound.repositories import IAssetPricePort, IFxRatePort

logger = logging.getLogger(__name__)

class YFinanceAdapter(IAssetPricePort, IFxRatePort):
    
    async def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> List[Tuple[date, Decimal]]:
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            if data.empty:
                logger.warning(f"No price history found for {ticker}")
                return []
            
            result = []
            for idx, row in data.iterrows():
                result.append((idx.date(), Decimal(str(row['Close']))))
            return result
        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {e}")
            return []
    
    async def get_current_price(self, ticker: str) -> Tuple[date, Decimal]:
        try:
            data = yf.download(ticker, period='1d', progress=False)
            if data.empty:
                logger.warning(f"No current price found for {ticker}")
                return (date.today(), Decimal('0'))
            
            latest = data.iloc[-1]
            return (data.index[-1].date(), Decimal(str(latest['Close'])))
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            return (date.today(), Decimal('0'))
    
    async def get_asset_metadata(self, ticker: str) -> Optional[AssetMetadata]:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            if not info or 'currency' not in info:
                logger.warning(f"Incomplete metadata for {ticker}")
                return None
            
            asset_class = self._determine_asset_class(ticker, info)
            
            return AssetMetadata(
                ticker=ticker,
                name=info.get('longName', info.get('shortName', ticker)),
                asset_class=asset_class,
                currency=Currency(info.get('currency', 'USD')),
                exchange=info.get('exchange'),
                sector=info.get('sector'),
                industry=info.get('industry'),
                country=info.get('country'),
                isin=info.get('isin'),
            )
        except Exception as e:
            logger.error(f"Error fetching metadata for {ticker}: {e}")
            return None
    
    async def get_fx_rate(
        self, from_currency: Currency, to_currency: Currency, date_val: date
    ) -> Optional[Decimal]:
        if from_currency == to_currency:
            return Decimal('1')
        
        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            data = yf.download(ticker, start=date_val, end=date_val + timedelta(days=1), progress=False)
            
            if data.empty:
                logger.warning(f"No FX rate found for {ticker} on {date_val}")
                return None
            
            return Decimal(str(data.iloc[-1]['Close']))
        except Exception as e:
            logger.error(f"Error fetching FX rate {from_currency}/{to_currency}: {e}")
            return None
    
    async def get_current_rate(
        self, from_currency: Currency, to_currency: Currency
    ) -> Optional[Decimal]:
        if from_currency == to_currency:
            return Decimal('1')
        
        try:
            ticker = f"{from_currency.value}{to_currency.value}=X"
            data = yf.download(ticker, period='1d', progress=False)
            
            if data.empty:
                logger.warning(f"No current rate found for {ticker}")
                return None
            
            return Decimal(str(data.iloc[-1]['Close']))
        except Exception as e:
            logger.error(f"Error fetching current FX rate {from_currency}/{to_currency}: {e}")
            return None
    
    @staticmethod
    def _determine_asset_class(ticker: str, info: dict) -> str:
        if ticker.endswith('-USD') or ticker.endswith('-PERP'):
            return 'crypto'
        
        if 'quoteType' in info:
            quote_type = info['quoteType'].lower()
            if quote_type in ['etf', 'fund']:
                return 'etf'
            elif quote_type == 'equity':
                return 'stock'
        
        return 'stock'
