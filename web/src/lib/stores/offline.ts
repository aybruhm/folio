import { writable } from 'svelte/store';
import type { Readable } from 'svelte/store';
import { invalidateAllAnalytics, invalidateAllHoldings } from '$lib/cache';

export interface SyncQueueItem {
  id: string;
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers: Record<string, string>;
  body?: unknown;
  timestamp: number;
  retries: number;
  maxRetries: number;
}

interface OfflineState {
  isOnline: boolean;
  syncQueue: SyncQueueItem[];
  syncInProgress: boolean;
  lastSyncTime: number | null;
  pendingChanges: number;
}

const initialState: OfflineState = {
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  syncQueue: [],
  syncInProgress: false,
  lastSyncTime: null,
  pendingChanges: 0
};

export const offlineStore = writable<OfflineState>(initialState);

// Initialize IndexedDB for persistent sync queue
async function initDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('folio-db', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        const store = db.createObjectStore('syncQueue', { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

let db: IDBDatabase | null = null;

if (typeof window !== 'undefined' && 'indexedDB' in window) {
  initDB().then((database) => {
    db = database;
  });
}

// Listen to online/offline events
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    offlineStore.update((state) => ({ ...state, isOnline: true }));
    syncQueuedData();
  });

  window.addEventListener('offline', () => {
    offlineStore.update((state) => ({ ...state, isOnline: false }));
  });
}

/**
 * Add a request to the sync queue
 */
export async function queueRequest(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  body?: unknown,
  headers?: Record<string, string>
): Promise<string> {
  const id = `${Date.now()}-${Math.random()}`;
  const item: SyncQueueItem = {
    id,
    url,
    method,
    headers: headers || { 'Content-Type': 'application/json' },
    body,
    timestamp: Date.now(),
    retries: 0,
    maxRetries: 3
  };

  if (db) {
    await new Promise<void>((resolve, reject) => {
      const transaction = db!.transaction(['syncQueue'], 'readwrite');
      const store = transaction.objectStore('syncQueue');
      const request = store.add(item);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  offlineStore.update((state) => ({
    ...state,
    syncQueue: [...state.syncQueue, item],
    pendingChanges: state.pendingChanges + 1
  }));

  return id;
}

/**
 * Remove an item from the sync queue
 */
export async function removeFromQueue(id: string): Promise<void> {
  if (db) {
    await new Promise<void>((resolve, reject) => {
      const transaction = db!.transaction(['syncQueue'], 'readwrite');
      const store = transaction.objectStore('syncQueue');
      const request = store.delete(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  offlineStore.update((state) => ({
    ...state,
    syncQueue: state.syncQueue.filter((item) => item.id !== id),
    pendingChanges: Math.max(0, state.pendingChanges - 1)
  }));
}

/**
 * Get all queued items
 */
export async function getQueuedItems(): Promise<SyncQueueItem[]> {
  if (!db) return [];

  return new Promise((resolve, reject) => {
    const transaction = db!.transaction(['syncQueue'], 'readonly');
    const store = transaction.objectStore('syncQueue');
    const request = store.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

/**
 * Sync all queued data
 */
export async function syncQueuedData(): Promise<void> {
  offlineStore.update((state) => ({ ...state, syncInProgress: true }));

  try {
    const items = await getQueuedItems();

    for (const item of items) {
      if (item.retries >= item.maxRetries) {
        console.warn(`Max retries reached for ${item.url}`, item);
        continue;
      }

      try {
        const response = await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: item.body ? JSON.stringify(item.body) : undefined
        });

        if (response.ok) {
          await removeFromQueue(item.id);
        } else if (response.status >= 400 && response.status < 500) {
          // Client error - don't retry
          await removeFromQueue(item.id);
        } else {
          // Server error - retry
          item.retries++;
          if (db) {
            await new Promise<void>((resolve, reject) => {
              const transaction = db!.transaction(['syncQueue'], 'readwrite');
              const store = transaction.objectStore('syncQueue');
              const request = store.put(item);

              request.onerror = () => reject(request.error);
              request.onsuccess = () => resolve();
            });
          }
        }
      } catch (error) {
        console.error(`Error syncing ${item.url}:`, error);
        item.retries++;
        if (db && item.retries < item.maxRetries) {
          await new Promise<void>((resolve, reject) => {
            const transaction = db!.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const request = store.put(item);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
          });
        }
      }
    }

    offlineStore.update((state) => ({
      ...state,
      syncInProgress: false,
      lastSyncTime: Date.now()
    }));
    await invalidateAllAnalytics();
    await invalidateAllHoldings();
  } catch (error) {
    console.error('Error during sync:', error);
    offlineStore.update((state) => ({ ...state, syncInProgress: false }));
  }
}

/**
 * Clear all queued items
 */
export async function clearQueue(): Promise<void> {
  if (db) {
    await new Promise<void>((resolve, reject) => {
      const transaction = db!.transaction(['syncQueue'], 'readwrite');
      const store = transaction.objectStore('syncQueue');
      const request = store.clear();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  offlineStore.update((state) => ({
    ...state,
    syncQueue: [],
    pendingChanges: 0
  }));
}

/**
 * Get a readable store for offline state
 */
export function getOfflineState(): Readable<OfflineState> {
  return offlineStore;
}
