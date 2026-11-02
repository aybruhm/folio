import { writable } from 'svelte/store';
import { PENDING_TRADES_STORE, isClient, openFolioDb } from '#lib/stores/folioDb.js';

// A trade the user submitted that the server rejected because the session had
// expired. Kept in the folio-db IndexedDB so it survives the redirect to /login.
// Form-shaped (numbers as strings) so it can be put straight back into TradeForm.
export interface PendingTrade {
  id: string;
  portfolio_id: string;
  ticker: string;
  trade_type: string;
  trade_date: string;
  quantity: string;
  price: string;
  trade_currency: string;
  fees: string;
  asset_class: string;
  market_data_provider: string;
  saved_at: number;
}

export type PendingTradeInput = Omit<PendingTrade, 'id' | 'saved_at'>;

export const pendingTrades = writable<PendingTrade[]>([]);

// Decimal string without exponent notation (1e-8 becomes "0.00000001").
function plain(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  return n.toLocaleString('en-US', { useGrouping: false, maximumFractionDigits: 8 });
}

// Same trade content gives the same fingerprint, so saving a trade again
// (for example a second 401 on re-submit) doesn't create a duplicate entry.
function fingerprint(t: PendingTradeInput): string {
  return JSON.stringify([
    t.portfolio_id,
    t.ticker.trim().toUpperCase(),
    t.trade_type,
    t.trade_date,
    plain(t.quantity),
    plain(t.price),
    plain(t.fees),
    t.trade_currency,
    t.asset_class,
    t.market_data_provider,
  ]);
}

// crypto.randomUUID() only exists in secure contexts (HTTPS or localhost), and
// Folio is also served over plain HTTP on a LAN; getRandomValues works everywhere.
function newId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function request<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
  });
}

export async function listPendingTrades(portfolioId: string): Promise<PendingTrade[]> {
  if (!isClient()) return [];
  try {
    const db = await openFolioDb();
    const index = db
      .transaction(PENDING_TRADES_STORE, 'readonly')
      .objectStore(PENDING_TRADES_STORE)
      .index('portfolio_id');
    const rows = await request(index.getAll(portfolioId) as IDBRequest<PendingTrade[]>);
    return rows.sort((a, b) => a.saved_at - b.saved_at);
  } catch {
    return [];
  }
}

export async function addPendingTrade(input: PendingTradeInput): Promise<PendingTrade> {
  const existing = (await listPendingTrades(input.portfolio_id)).find(
    (t) => fingerprint(t) === fingerprint(input),
  );
  if (existing) return existing;

  const record: PendingTrade = {
    ...input,
    id: newId(),
    saved_at: Date.now(),
  };
  const db = await openFolioDb();
  await request(
    db
      .transaction(PENDING_TRADES_STORE, 'readwrite')
      .objectStore(PENDING_TRADES_STORE)
      .put(record),
  );
  return record;
}

export async function updatePendingTrade(
  id: string,
  input: PendingTradeInput,
): Promise<void> {
  const db = await openFolioDb();
  const store = db
    .transaction(PENDING_TRADES_STORE, 'readwrite')
    .objectStore(PENDING_TRADES_STORE);
  const current = await request(store.get(id) as IDBRequest<PendingTrade | undefined>);
  if (!current) return;
  await request(store.put({ ...current, ...input }));
}

export async function removePendingTrade(id: string): Promise<void> {
  const db = await openFolioDb();
  await request(
    db
      .transaction(PENDING_TRADES_STORE, 'readwrite')
      .objectStore(PENDING_TRADES_STORE)
      .delete(id),
  );
}

export async function refreshPendingTrades(portfolioId: string | undefined): Promise<void> {
  pendingTrades.set(portfolioId ? await listPendingTrades(portfolioId) : []);
}

function toPendingInput(row: any, portfolioId: unknown): PendingTradeInput | null {
  if (!row || typeof row !== 'object' || !portfolioId || !row.ticker) return null;
  return {
    portfolio_id: String(portfolioId),
    ticker: String(row.ticker),
    trade_type: String(row.trade_type ?? 'buy'),
    trade_date: String(row.trade_date ?? ''),
    quantity: plain(row.quantity),
    price: plain(row.price),
    trade_currency: String(row.trade_currency ?? 'USD'),
    fees: plain(row.fees ?? 0) || '0',
    asset_class: String(row.asset_class ?? ''),
    market_data_provider: String(row.market_data_provider ?? 'yfinance'),
  };
}

// The trades a failed create request carried: POST /trades/ (one trade) or
// POST /trades/bulk (several, sharing the body's portfolio_id). Empty for any
// other request.
export function pendingTradesFromRequest(config: {
  method?: string;
  url?: string;
  data?: unknown;
}): PendingTradeInput[] {
  if ((config.method ?? '').toUpperCase() !== 'POST') return [];
  const path = (config.url ?? '').split('?')[0].replace(/\/+$/, '');
  const isBulk = path.endsWith('/trades/bulk');
  if (!isBulk && !path.endsWith('/trades')) return [];

  let body: any = config.data;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch {
      return [];
    }
  }
  if (!body || typeof body !== 'object') return [];

  const rows = isBulk ? (Array.isArray(body.trades) ? body.trades : []) : [body];
  return rows
    .map((row: any) => toPendingInput(row, body.portfolio_id))
    .filter((t: PendingTradeInput | null): t is PendingTradeInput => t !== null);
}

// Returns how many trades were saved. Never throws: saving is best effort and
// must not block the redirect.
export async function savePendingTradesFromRequest(config: {
  method?: string;
  url?: string;
  data?: unknown;
}): Promise<number> {
  let saved = 0;
  try {
    for (const input of pendingTradesFromRequest(config)) {
      await addPendingTrade(input);
      saved++;
    }
  } catch (e) {
    console.error('Could not save the pending trade(s):', e);
  }
  return saved;
}
