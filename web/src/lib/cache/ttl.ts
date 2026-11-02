import { envUtils } from '#utils/env.js';

// Benchmark comparisons: 35 minutes, matching the API's BENCHMARK_CACHE_TTL.
const BENCHMARK_TTL_SECONDS = 35 * 60;

export const CACHE_TTL = {
  BENCHMARK: BENCHMARK_TTL_SECONDS,
  get MARKET_DATA() { return envUtils.getMarketDataCacheTtl(); },
  get PRICE_HISTORY() { return envUtils.getPriceHistoryCacheTtl(); },
  get YFINANCE() { return envUtils.getYfinanceCacheTtl(); },
  get FX_RATES() { return envUtils.getFxRatesCacheTtl(); },
};
