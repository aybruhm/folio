import { env } from "$env/dynamic/public";

class EnvUtils {
    private static instance: EnvUtils;
    private env: {
        API_BASE_URL: string;
        MARKET_DATA_CACHE_TTL: number;
        PRICE_HISTORY_CACHE_TTL: number;
        YFINANCE_CACHE_TTL: number;
        FX_RATES_CACHE_TTL: number;
    };

    private constructor() {
        const rawBaseUrl = env.PUBLIC_API_BASE_URL?.trim();
        this.env = {
            API_BASE_URL: rawBaseUrl || "/api/v1/",
            MARKET_DATA_CACHE_TTL: parseInt(env.PUBLIC_MARKET_DATA_CACHE_TTL || "10800"),
            PRICE_HISTORY_CACHE_TTL: parseInt(env.PUBLIC_PRICE_HISTORY_CACHE_TTL || "86400"),
            YFINANCE_CACHE_TTL: parseInt(env.PUBLIC_YFINANCE_CACHE_TTL || "3600"),
            FX_RATES_CACHE_TTL: parseInt(env.PUBLIC_FX_RATES_CACHE_TTL || "10800"),
        };
    }

    public static getInstance(): EnvUtils {
        if (!EnvUtils.instance) {
            EnvUtils.instance = new EnvUtils();
        }
        return EnvUtils.instance;
    }

    public getBaseUrl(): string {
        return this.env.API_BASE_URL;
    }

    public getMarketDataCacheTtl(): number {
        return this.env.MARKET_DATA_CACHE_TTL;
    }

    public getPriceHistoryCacheTtl(): number {
        return this.env.PRICE_HISTORY_CACHE_TTL;
    }

    public getYfinanceCacheTtl(): number {
        return this.env.YFINANCE_CACHE_TTL;
    }

    public getFxRatesCacheTtl(): number {
        return this.env.FX_RATES_CACHE_TTL;
    }
}

export const envUtils = EnvUtils.getInstance();
