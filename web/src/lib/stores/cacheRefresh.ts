import { writable } from 'svelte/store';

export const cacheRefreshCounter = writable(0);

export function triggerCacheRefresh(): void {
  cacheRefreshCounter.update((n) => n + 1);
}
