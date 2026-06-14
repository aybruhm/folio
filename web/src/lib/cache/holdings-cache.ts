import { idbGet, idbSet, idbInvalidate, idbClearStore } from '$lib/stores/idb';
import { CACHE_TTL } from './ttl';
import type { GetHoldingsResponse } from '$lib/api/types';

export async function getCachedHoldings(portfolioId: string): Promise<GetHoldingsResponse | null> {
  return idbGet<GetHoldingsResponse>('holdings', portfolioId);
}

export async function setCachedHoldings(portfolioId: string, data: GetHoldingsResponse): Promise<void> {
  return idbSet('holdings', portfolioId, data, CACHE_TTL.MARKET_DATA);
}

export async function invalidatePortfolioHoldings(portfolioId: string): Promise<void> {
  return idbInvalidate('holdings', portfolioId);
}

export async function invalidateAllHoldings(): Promise<void> {
  return idbClearStore('holdings');
}
