import { idbGet, idbSet } from '$lib/stores/idb';
import { CACHE_TTL } from './ttl';
import type { GetBatchPriceHistoryResponse } from '$lib/api/types';

export async function getCachedBatchPriceHistory(
  key: string,
): Promise<GetBatchPriceHistoryResponse | null> {
  return idbGet<GetBatchPriceHistoryResponse>('price_history', key);
}

export async function setCachedBatchPriceHistory(
  key: string,
  data: GetBatchPriceHistoryResponse,
): Promise<void> {
  return idbSet('price_history', key, data, CACHE_TTL.PRICE_HISTORY);
}

export function buildBatchPriceHistoryKey(
  tickers: string[],
  startDate: string,
  endDate: string,
): string {
  return `batch_${[...tickers].sort().join(',')}_${startDate}_${endDate}`;
}
