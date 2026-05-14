import type { Currency, TradeType } from "./common";

export interface CreatePortfolioRequest {
    name: string;
    base_currency: Currency;
    description?: string | null;
}

export interface UpdatePortfolioRequest {
    name?: string | null;
    description?: string | null;
}

export type MarketDataProvider = "yfinance" | "tiingo" | "ngnmarket";

export interface CreateTradeRequest {
    portfolio_id: string;
    ticker: string;
    trade_type: TradeType;
    trade_date: string;
    quantity: number | string;
    price: number | string;
    trade_currency: Currency;
    fees?: number | string;
    notes?: string | null;
    asset_class?: string;
    market_data_provider?: MarketDataProvider;
}

export interface ListTradesQuery {
    portfolio_id: string;
    ticker?: string | null;
    trade_type?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    skip?: number;
    limit?: number;
}

export interface CreateGoalRequest {
    name: string;
    target_net_worth: number | string;
    target_net_worth_currency: Currency;
    target_date: string;
    monthly_savings: number | string;
    monthly_savings_currency: Currency;
    expected_annual_return: number | string;
}

export interface ValidateCsvRequest {
    file: File;
    mapping: Record<string, unknown>;
    date_format: string;
}

export interface ConfirmImportRequest {
    file: File;
    mapping: Record<string, unknown>;
    portfolio_id: string;
    date_format: string;
    profile_name?: string | null;
}

export interface SearchAssetsQuery {
    q: string;
}

export interface GetPriceHistoryQuery {
    ticker: string;
    start_date?: string | null;
    end_date?: string | null;
}

export interface GetHoldingsQuery {
    portfolio_id: string;
    in_currency?: string | null;
}

export interface GetPortfolioAnalyticsQuery {
    portfolio_id: string;
    timeframe?: string;
}

export interface GetPerformanceQuery {
    portfolio_id: string;
}

export interface GetAllocationQuery {
    portfolio_id: string;
    group_by?: string;
}

export interface ListPortfolioAnalyticsQuery {
    timeframe?: string;
}

export interface AddBenchmarkQuery {
    ticker: string;
    name: string;
}

export interface GetFxRatesRequest {
    currencies: string[];
}
