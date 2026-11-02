// The `folio-db` IndexedDB: user data that must survive until it is dealt with,
// as opposed to `folio-cache` (idb.ts), which only holds disposable cached API data.
//   syncQueue      requests made while offline, replayed automatically (offline.ts)
//   pendingTrades  trades rejected by an expired session, kept for the user to
//                  review and re-submit (pendingTrades.ts). Never replayed
//                  automatically, so it must not live in syncQueue.

const DB_NAME = 'folio-db';
// v2 adds pendingTrades.
const DB_VERSION = 2;

export const SYNC_QUEUE_STORE = 'syncQueue';
export const PENDING_TRADES_STORE = 'pendingTrades';

let dbPromise: Promise<IDBDatabase> | null = null;

export function isClient(): boolean {
  return typeof window !== 'undefined' && 'indexedDB' in window;
}

export function openFolioDb(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => {
      dbPromise = null;
      reject(request.error);
    };
    request.onsuccess = () => {
      const db = request.result;
      // Let another tab upgrade the schema instead of blocking it forever.
      db.onversionchange = () => {
        db.close();
        dbPromise = null;
      };
      resolve(db);
    };
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
        const queue = db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: 'id' });
        queue.createIndex('timestamp', 'timestamp', { unique: false });
      }
      if (!db.objectStoreNames.contains(PENDING_TRADES_STORE)) {
        const pending = db.createObjectStore(PENDING_TRADES_STORE, { keyPath: 'id' });
        pending.createIndex('portfolio_id', 'portfolio_id', { unique: false });
      }
    };
  });
  return dbPromise;
}
