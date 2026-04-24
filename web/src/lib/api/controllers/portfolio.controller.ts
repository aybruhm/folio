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
} from "../types";

export class PortfolioController {
    constructor(private client: AxiosInstance) {}

    async listPortfolios(): Promise<Portfolio[]> {
        const response = await this.client.get<Portfolio[]>("/portfolios/");
        return response.data as Portfolio[];
    }

    async createPortfolio(
        data: CreatePortfolioRequest,
    ): Promise<Portfolio> {
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
