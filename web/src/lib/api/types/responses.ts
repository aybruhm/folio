import type { Portfolio, Trade, Goal, Asset, Benchmark } from "./common";

export type ListPortfoliosResponse = Portfolio[];

export type GetPortfolioResponse = Portfolio;

export type CreatePortfolioResponse = Portfolio;

export type UpdatePortfolioResponse = Portfolio;

export interface ListTradesResponse {
    data: Trade[];
    total: number;
    skip: number;
    limit: number;
}

export type GetTradeResponse = Trade;

export type CreateTradeResponse = Trade;

export type UpdateTradeResponse = Trade;

export type ListGoalsResponse = Goal[];

export type GetGoalResponse = Goal;

export type CreateGoalResponse = Goal;

export type UpdateGoalResponse = Goal;

export interface GetHoldingsResponse {
    data: Array<{
        ticker: string;
        quantity: number;
        avg_price: number;
        current_price: number;
        total_value: number;
        gain_loss: number;
        gain_loss_percent: number;
    }>;
    currency: string;
    total_value: number;
}

export interface GetPortfolioAnalyticsResponse {
    portfolio_id: string;
    total_invested: number;
    current_value: number;
    total_gain_loss: number;
    total_gain_loss_percent: number;
    twr: string;
    mwr: string;
    allocation: { label: string; value: number }[];
    top_holdings: { ticker: string; value: number; percent: number }[];
    performance_history: { name: string; value: number }[];
    contribution_history: { name: string; value: number }[];
    sector_breakdown: { label: string; value: number }[];
    timeframe: string;
}

export type ListPortfolioAnalyticsResponse = GetPortfolioAnalyticsResponse[];

export interface GetPerformanceResponse {
    twr: string;
    mwr: string;
    start_date: string;
    end_date: string;
}

export type GetAllocationResponse = Array<{
    name: string;
    value: string;
    weight_percent: string;
}>;

export interface SearchAssetsResponse {
    data: Asset[];
}

export interface GetPriceHistoryResponse {
    ticker: string;
    data: Array<{
        date: string;
        close: number;
    }>;
}

export interface ListBenchmarksResponse {
    data: Benchmark[];
}

export interface AddBenchmarkResponse {
    data: Benchmark;
}

export interface ValidateCsvResponse {
    valid_count: number;
    error_count: number;
    errors: Array<{ row: number; error: string }>;
    sample_valid_rows: Record<string, unknown>[];
}

export interface ConfirmImportResponse {
    import_batch_id: string;
    imported_count: number;
    rejected_count: number;
    rejection_details: Array<{ row: number; error: string }>;
}

export interface GetProjectionResponse {
    goal_id: string;
    projected_value: number;
    on_track: boolean;
    shortfall: number | null;
    projected_date: string;
}

export interface GetFxRatesResponse {
    rates: Record<string, number>;
    base_currency: string;
    timestamp: string;
}
