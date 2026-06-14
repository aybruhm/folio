export type StoreName = 'analytics' | 'holdings' | 'price_history' | 'fx_rates';

interface CacheRecord {
  key: string;
  data: unknown;
  timestamp: number;
  ttl: number;
}

const DB_NAME = 'folio-cache';
const DB_VERSION = 1;
const STORES: StoreName[] = ['analytics', 'holdings', 'price_history', 'fx_rates'];

let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      for (const name of STORES) {
        if (!db.objectStoreNames.contains(name)) {
          db.createObjectStore(name, { keyPath: 'key' });
        }
      }
    };
  });
  return dbPromise;
}

function isClient(): boolean {
  return typeof window !== 'undefined' && 'indexedDB' in window;
}

export async function idbGet<T>(store: StoreName, key: string): Promise<T | null> {
  if (!isClient()) return null;
  try {
    const db = await openDB();
    const record = await new Promise<CacheRecord | undefined>((resolve, reject) => {
      const tx = db.transaction(store, 'readonly');
      const req = tx.objectStore(store).get(key);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve(req.result as CacheRecord | undefined);
    });
    if (!record) return null;
    if (Date.now() - record.timestamp > record.ttl * 1000) {
      await idbInvalidate(store, key);
      return null;
    }
    return record.data as T;
  } catch {
    return null;
  }
}

export async function idbSet(store: StoreName, key: string, data: unknown, ttl: number): Promise<void> {
  if (!isClient()) return;
  try {
    const db = await openDB();
    const record: CacheRecord = { key, data, timestamp: Date.now(), ttl };
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).put(record);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve();
    });
  } catch {
    // non-critical
  }
}

export async function idbInvalidate(store: StoreName, key: string): Promise<void> {
  if (!isClient()) return;
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).delete(key);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve();
    });
  } catch {
    // non-critical
  }
}

export async function idbInvalidateByPrefix(store: StoreName, prefix: string): Promise<void> {
  if (!isClient()) return;
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const objectStore = tx.objectStore(store);
      const range = IDBKeyRange.bound(prefix, prefix + '￿');
      const req = objectStore.openCursor(range);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => {
        const cursor = req.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };
    });
  } catch {
    // non-critical
  }
}

export async function idbClearStore(store: StoreName): Promise<void> {
  if (!isClient()) return;
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).clear();
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve();
    });
  } catch {
    // non-critical
  }
}
