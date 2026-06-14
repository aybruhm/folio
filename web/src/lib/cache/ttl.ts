import { envUtils } from '@/utils/env';

export const CACHE_TTL = {
  get MARKET_DATA() { return envUtils.getMarketDataCacheTtl(); },
  get PRICE_HISTORY() { return envUtils.getPriceHistoryCacheTtl(); },
  get YFINANCE() { return envUtils.getYfinanceCacheTtl(); },
  get FX_RATES() { return envUtils.getFxRatesCacheTtl(); },
};
