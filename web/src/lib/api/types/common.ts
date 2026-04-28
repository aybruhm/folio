export type Currency =
  // Americas
  | 'USD' | 'CAD' | 'BRL' | 'MXN' | 'ARS' | 'CLP' | 'COP' | 'PEN'
  // Europe
  | 'EUR' | 'GBP' | 'CHF' | 'SEK' | 'NOK' | 'DKK' | 'PLN' | 'CZK' | 'HUF' | 'RON' | 'TRY' | 'RUB'
  // Middle East & Africa
  | 'ILS' | 'AED' | 'SAR' | 'QAR' | 'KWD' | 'EGP' | 'NGN' | 'ZAR' | 'KES' | 'GHS' | 'MAD'
  // Asia Pacific
  | 'JPY' | 'CNY' | 'HKD' | 'KRW' | 'TWD' | 'SGD' | 'INR' | 'AUD' | 'NZD'
  | 'MYR' | 'THB' | 'IDR' | 'PHP' | 'VND' | 'PKR' | 'BDT' | 'LKR';

export type TradeType = 'buy' | 'sell' | 'dividend' | 'fee';

export interface Paginated<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface BaseEntity {
  id: string;
  created_at?: string;
  updated_at?: string;
}

export interface Portfolio extends BaseEntity {
  name: string;
  base_currency: Currency;
  description?: string;
}

export interface PortfolioStats {
  id: string;
  current_value: number | string;
  cost_basis: number | string;
  gain_loss: number | string;
  return_percent: number | string;
  allocation?: { label: string; value: number }[];
  performance_history?: { name: string; value: number }[];
  top_holdings?: { ticker: string; value: number | string; percent: number | string }[];
}

export interface Trade extends BaseEntity {
  portfolio_id: string;
  ticker: string;
  trade_type: TradeType;
  trade_date: string;
  quantity: number | string;
  price: number | string;
  trade_currency: Currency;
  fees: number | string;
  notes?: string;
}

export interface Goal extends BaseEntity {
  portfolio_id: string;
  name: string;
  target_net_worth: number | string;
  target_net_worth_currency: Currency;
  target_date: string;
  monthly_savings: number | string;
  monthly_savings_currency: Currency;
  expected_annual_return: number | string;
}

export interface Holding {
  ticker: string;
  quantity: number;
  average_cost: number;
  current_price: number;
  current_value: number;
  gain_loss: number;
  return_pct: number;
  currency?: string;
}

export interface Asset {
  ticker: string;
  name: string;
  asset_class?: string;
  currency?: Currency;
}

export interface Benchmark extends BaseEntity {
  ticker: string;
  name: string;
}

export interface HealthCheck {
  status: 'ok' | 'error';
  version?: string;
}
