import { idbGet, idbSet } from '#lib/stores/idb.js';
import { CACHE_TTL } from './ttl';
import type {
  BenchmarkComparisonQuery,
  BenchmarkComparisonResponse,
} from '#lib/api/types/index.js';

// Lives in the 'analytics' store, so invalidateAllAnalytics() (called whenever
// trades or portfolios change) clears these too. Keyed by user: the store is
// shared by everyone who signs in on this browser.
function key(userId: string, q: BenchmarkComparisonQuery): string {
  const today = new Date().toISOString().slice(0, 10);
  return [
    'benchmark',
    userId,
    q.portfolio_id ?? 'all',
    q.benchmark,
    q.provider ?? 'default',
    q.period,
    q.in_currency ?? 'USD',
    today,
  ].join('_');
}

export async function getCachedBenchmark(
  userId: string,
  query: BenchmarkComparisonQuery,
): Promise<BenchmarkComparisonResponse | null> {
  return idbGet<BenchmarkComparisonResponse>('analytics', key(userId, query));
}

// Counts from when the API computed the result, not from now, so the two
// caches together never keep a comparison longer than 35 minutes.
export async function setCachedBenchmark(
  userId: string,
  query: BenchmarkComparisonQuery,
  data: BenchmarkComparisonResponse,
): Promise<void> {
  const ageSeconds = (Date.now() - Date.parse(data.generated_at)) / 1000;
  const ttl = Math.floor(CACHE_TTL.BENCHMARK - (Number.isFinite(ageSeconds) ? Math.max(ageSeconds, 0) : 0));
  if (ttl <= 0) return;
  return idbSet('analytics', key(userId, query), data, ttl);
}
