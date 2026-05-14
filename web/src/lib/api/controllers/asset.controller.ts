import type { AxiosInstance } from "axios";
import type {
    SearchAssetsQuery,
    SearchAssetsResponse,
    GetPriceHistoryQuery,
    GetPriceHistoryResponse,
    ListBenchmarksResponse,
    AddBenchmarkResponse,
    GetFxRatesResponse,
    ValidateTickerResponse,
} from "../types";

export class AssetController {
    constructor(private client: AxiosInstance) {}

    async searchAssets(query: string): Promise<SearchAssetsResponse> {
        const response = await this.client.get("/assets/search", {
            params: {
                q: query,
            },
        });
        return response.data;
    }

    async validateTicker(
        ticker: string,
        provider: "yfinance" | "tiingo" | "ngnmarket" = "yfinance",
        currency: string = "USD",
    ): Promise<ValidateTickerResponse> {
        const response = await this.client.get("/assets/validate", {
            params: {
                ticker,
                provider,
                currency,
            },
        });
        return response.data;
    }

    async getPriceHistory(
        params: GetPriceHistoryQuery,
    ): Promise<GetPriceHistoryResponse> {
        const response = await this.client.get(
            `/assets/${params.ticker}/history`,
            {
                params: {
                    start_date: params.start_date,
                    end_date: params.end_date,
                },
            },
        );
        return response.data;
    }

    async listBenchmarks(): Promise<ListBenchmarksResponse> {
        const response = await this.client.get("/benchmarks/");
        return response.data;
    }

    async addBenchmark(
        ticker: string,
        name: string,
    ): Promise<AddBenchmarkResponse> {
        const response = await this.client.post("/benchmarks/", null, {
            params: {
                ticker,
                name,
            },
        });
        return response.data;
    }

    async deleteBenchmark(benchmarkId: string): Promise<void> {
        await this.client.delete(`/benchmarks/${benchmarkId}`);
    }

    async getFxRates(currencies: string[]): Promise<GetFxRatesResponse> {
        const response = await this.client.get("/fx/rates", {
            data: currencies,
        });
        return response.data;
    }
}
