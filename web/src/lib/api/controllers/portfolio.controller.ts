import type { AxiosInstance } from "axios";
import type {
    Portfolio,
    CreatePortfolioRequest,
    UpdatePortfolioRequest,
    GetHoldingsQuery,
    GetHoldingsResponse,
    GetPortfolioAnalyticsQuery,
    GetPortfolioAnalyticsResponse,
    GetPerformanceQuery,
    GetPerformanceResponse,
    GetAllocationQuery,
    GetAllocationResponse,
    ListPortfolioAnalyticsQuery,
    ListPortfolioAnalyticsResponse,
    AnalyticsSummaryQuery,
    AnalyticsSummaryResponse,
} from "../types";

export class PortfolioController {
    constructor(private client: AxiosInstance) {}

    // Archived portfolios are left out unless includeArchived is true.
    async listPortfolios(includeArchived = false): Promise<Portfolio[]> {
        const response = await this.client.get<Portfolio[]>("/portfolios/", {
            params: includeArchived ? { include_archived: true } : undefined,
        });
        return response.data as Portfolio[];
    }

    async createPortfolio(data: CreatePortfolioRequest): Promise<Portfolio> {
        const response = await this.client.post("/portfolios/", data);
        return response.data;
    }

    async getPortfolio(portfolioId: string): Promise<Portfolio> {
        const response = await this.client.get<Portfolio>(
            `/portfolios/${portfolioId}`,
        );
        return response.data as Portfolio;
    }

    async updatePortfolio(
        portfolioId: string,
        data: UpdatePortfolioRequest,
    ): Promise<Portfolio> {
        const response = await this.client.put(
            `/portfolios/${portfolioId}`,
            null,
            {
                params: data,
            },
        );
        return response.data;
    }

    async deletePortfolio(portfolioId: string): Promise<void> {
        await this.client.delete(`/portfolios/${portfolioId}`);
    }

    async archivePortfolio(portfolioId: string): Promise<Portfolio> {
        const response = await this.client.post(
            `/portfolios/${portfolioId}/archive`,
        );
        return response.data;
    }

    async unarchivePortfolio(portfolioId: string): Promise<Portfolio> {
        const response = await this.client.post(
            `/portfolios/${portfolioId}/unarchive`,
        );
        return response.data;
    }

    async getHoldings(params: GetHoldingsQuery): Promise<GetHoldingsResponse> {
        const response = await this.client.get(
            `/portfolios/${params.portfolio_id}/holdings`,
            {
                params: {
                    in_currency: params.in_currency,
                },
            },
        );
        return response.data;
    }

    async getPortfolioAnalytics(
        params: GetPortfolioAnalyticsQuery,
    ): Promise<GetPortfolioAnalyticsResponse> {
        const response = await this.client.get(
            `/portfolios/${params.portfolio_id}/analytics`,
            {
                params: {
                    timeframe: params.timeframe || "1y",
                },
            },
        );
        return response.data;
    }

    async listPortfolioAnalytics(
        params: ListPortfolioAnalyticsQuery = {},
    ): Promise<ListPortfolioAnalyticsResponse> {
        const response = await this.client.get(`/portfolios/analytics`, {
            params: {
                timeframe: params.timeframe || "1y",
                ...(params.in_currency && { in_currency: params.in_currency }),
                ...(params.include_archived && { include_archived: true }),
            },
        });
        return response.data;
    }

    async getAnalyticsSummary(
        params: AnalyticsSummaryQuery = {},
    ): Promise<AnalyticsSummaryResponse> {
        const response = await this.client.get(`/portfolios/analytics/summary`, {
            params: {
                timeframe: params.timeframe || "1y",
                in_currency: params.in_currency || "USD",
            },
        });
        return response.data;
    }

    async getPerformance(
        params: GetPerformanceQuery,
    ): Promise<GetPerformanceResponse> {
        const response = await this.client.get(
            `/portfolios/${params.portfolio_id}/performance`,
        );
        return response.data;
    }

    async getAllocation(
        params: GetAllocationQuery,
    ): Promise<GetAllocationResponse> {
        const response = await this.client.get(
            `/portfolios/${params.portfolio_id}/allocation`,
            {
                params: {
                    group_by: params.group_by || "asset_class",
                },
            },
        );
        return response.data;
    }
}
