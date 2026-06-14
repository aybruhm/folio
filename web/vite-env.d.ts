/// <reference types="vite/client" />

declare module "$env/dynamic/public" {
    export const env: {
        PUBLIC_API_BASE_URL: string;
        PUBLIC_ENABLE_REGISTRATION: string;
        PUBLIC_MARKET_DATA_CACHE_TTL: string;
        PUBLIC_PRICE_HISTORY_CACHE_TTL: string;
        PUBLIC_YFINANCE_CACHE_TTL: string;
        PUBLIC_FX_RATES_CACHE_TTL: string;
        [key: string]: string | undefined;
    };
}

declare module "$env/dynamic/private" {
    export const env: {
        SECRET_KEY: string;
        [key: string]: string | undefined;
    };
}
