/// <reference lib="webworker" />

type SyncEvent = ExtendableEvent & { tag: string };

interface QueueItem {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body?: unknown;
  [key: string]: unknown;
}

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE_NAME = 'folio-v1';
const RUNTIME_CACHE = 'folio-runtime-v1';
const API_CACHE = 'folio-api-v1';

const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png'
];

// Install event - cache essential assets
sw.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {
        // Fail gracefully if some assets don't exist
        return Promise.resolve();
      });
    })
  );
  sw.skipWaiting();
});

// Activate event - clean up old caches
sw.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE && cacheName !== API_CACHE) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  sw.clients.claim();
});

// Fetch event - serve from cache with fallback
sw.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin requests
  if (url.origin !== sw.location.origin) {
    return;
  }

  // API requests: stale-while-revalidate strategy
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(API_CACHE).then((cache) => {
        return fetch(request).then((response) => {
          if (response.ok) {
            cache.put(request, response.clone());
          }
          return response;
        }).catch(() => {
          return cache.match(request).then((cachedResponse) => {
            return cachedResponse || new Response(
              JSON.stringify({ error: 'Offline - no cached data available' }),
              { status: 503, headers: { 'Content-Type': 'application/json' } }
            );
          });
        });
      })
    );
    return;
  }

  // Document requests: network-first, fallback to cache
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok) {
          caches.open(RUNTIME_CACHE).then((cache) => {
            cache.put(request, response.clone());
          });
        }
        return response;
      }).catch(() => {
        return caches.match(request).then((cachedResponse) => {
          return cachedResponse || caches.match('/');
        });
      })
    );
    return;
  }

  // Static assets: cache-first strategy
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(request).then((response) => {
        if (response.ok && (request.method === 'GET')) {
          caches.open(RUNTIME_CACHE).then((cache) => {
            cache.put(request, response.clone());
          });
        }
        return response;
      }).catch(() => {
        // Return a default offline page or empty response
        return new Response('Asset not available offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({ 'Content-Type': 'text/plain' })
        });
      });
    })
  );
});

// Handle background sync for queued operations
sw.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncQueuedData());
  }
});

async function syncQueuedData() {
  try {
    const db = await openDB();
    const queue = await getAllQueueItems(db);
    
    for (const item of queue) {
      try {
        const response = await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: item.body ? JSON.stringify(item.body) : undefined
        });
        
        if (response.ok) {
          await deleteQueueItem(db, item.id);
        }
      } catch (error) {
        console.error('Sync failed for item:', item, error);
      }
    }
  } catch (error) {
    console.error('Error syncing data:', error);
  }
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('folio-db', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id' });
      }
    };
  });
}

function getAllQueueItems(db: IDBDatabase): Promise<QueueItem[]> {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['syncQueue'], 'readonly');
    const store = transaction.objectStore('syncQueue');
    const request = store.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result as QueueItem[]);
  });
}

function deleteQueueItem(db: IDBDatabase, id: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['syncQueue'], 'readwrite');
    const store = transaction.objectStore('syncQueue');
    const request = store.delete(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}
