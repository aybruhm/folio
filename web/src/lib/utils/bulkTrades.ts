import type { BulkCreateTradeRequest } from '#lib/api/types/index.js';
import type { PendingTrade, PendingTradeInput } from '#lib/stores/pendingTrades.js';

// One editable row of the bulk trade form. Values are form strings, like TradeForm.
export interface BulkRow {
  // Stable identity for the {#each} block and error mapping; not sent to the API.
  key: number;
  // Set when the row came from a pending (session-expired) trade.
  pendingId?: string;
  ticker: string;
  trade_type: string;
  trade_date: string;
  quantity: string;
  price: string;
  fees: string;
  trade_currency: string;
  asset_class: string;
  market_data_provider: string;
}

export const MAX_BULK_ROWS = 50;

export const TRADE_TYPES = [
  { label: 'Buy', value: 'buy' },
  { label: 'Sell', value: 'sell' },
  { label: 'Dividend', value: 'dividend' },
  { label: 'Fee', value: 'fee' },
];

export const ASSET_CLASSES = [
  { label: 'Auto-detect', value: '' },
  { label: 'Stock', value: 'stock' },
  { label: 'ETF', value: 'etf' },
  { label: 'Crypto', value: 'crypto' },
  { label: 'Cash', value: 'cash' },
];

export const MARKET_DATA_PROVIDERS = [
  { label: 'Yahoo Finance', value: 'yfinance' },
  { label: 'Tiingo', value: 'tiingo' },
  { label: 'NGNMarket', value: 'ngnmarket' },
  { label: 'NGXPulse', value: 'ngxpulse' },
  { label: 'TradingView', value: 'tradingview' },
];

let nextKey = 1;

// A new row. `base` carries the fields that tend to repeat from row to row
// (type, date, currency, provider); the ticker, quantity and price start empty.
export function newBulkRow(base?: Partial<BulkRow>): BulkRow {
  return {
    ticker: '',
    trade_type: 'buy',
    trade_date: new Date().toISOString().slice(0, 16),
    quantity: '',
    price: '',
    fees: '0',
    trade_currency: 'USD',
    asset_class: '',
    market_data_provider: 'yfinance',
    ...base,
    key: nextKey++,
    pendingId: undefined,
  };
}

// A row the user hasn't started filling in, which is ignored on submit.
export function isBlankRow(row: BulkRow): boolean {
  return !row.ticker.trim() && !row.quantity && !row.price;
}

export function rowsFromPending(pending: PendingTrade[]): BulkRow[] {
  return pending.map((t) => ({ ...newBulkRow(t), pendingId: t.id }));
}

export function rowToPendingInput(portfolioId: string, row: BulkRow): PendingTradeInput {
  return {
    portfolio_id: portfolioId,
    ticker: row.ticker.trim(),
    trade_type: row.trade_type,
    trade_date: row.trade_date,
    quantity: row.quantity,
    price: row.price,
    trade_currency: row.trade_currency,
    fees: row.fees || '0',
    asset_class: row.asset_class,
    market_data_provider: row.market_data_provider,
  };
}

// The request body for POST /trades/bulk.
export function toBulkPayload(portfolioId: string, rows: BulkRow[]): BulkCreateTradeRequest {
  return {
    portfolio_id: portfolioId,
    trades: rows.map((r) => ({
      ticker: r.ticker.trim(),
      trade_type: r.trade_type,
      trade_date: r.trade_date,
      quantity: parseFloat(r.quantity),
      price: parseFloat(r.price),
      trade_currency: r.trade_currency,
      fees: parseFloat(r.fees) || 0,
      asset_class: r.asset_class || undefined,
      market_data_provider: r.market_data_provider || 'yfinance',
    })),
  } as BulkCreateTradeRequest;
}
