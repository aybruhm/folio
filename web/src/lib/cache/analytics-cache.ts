import { idbGet, idbSet, idbInvalidateByPrefix, idbClearStore } from '$lib/stores/idb';
import { CACHE_TTL } from './ttl';
import type { GetPortfolioAnalyticsResponse, ListPortfolioAnalyticsResponse } from '$lib/api/types';

export async function getCachedAnalytics(
  portfolioId: string,
  timeframe: string,
): Promise<GetPortfolioAnalyticsResponse | null> {
  return idbGet<GetPortfolioAnalyticsResponse>('analytics', `${portfolioId}_${timeframe}`);
}

export async function setCachedAnalytics(
  portfolioId: string,
  timeframe: string,
  data: GetPortfolioAnalyticsResponse,
): Promise<void> {
  return idbSet('analytics', `${portfolioId}_${timeframe}`, data, CACHE_TTL.MARKET_DATA);
}

export async function getCachedListAnalytics(
  timeframe: string,
  currency: string,
): Promise<ListPortfolioAnalyticsResponse | null> {
  return idbGet<ListPortfolioAnalyticsResponse>('analytics', `list_${timeframe}_${currency}`);
}

export async function setCachedListAnalytics(
  timeframe: string,
  currency: string,
  data: ListPortfolioAnalyticsResponse,
): Promise<void> {
  return idbSet('analytics', `list_${timeframe}_${currency}`, data, CACHE_TTL.MARKET_DATA);
}

export async function invalidatePortfolioAnalytics(portfolioId: string): Promise<void> {
  return idbInvalidateByPrefix('analytics', `${portfolioId}_`);
}

export async function invalidateAllAnalytics(): Promise<void> {
  return idbClearStore('analytics');
}
