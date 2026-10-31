import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PRIVATE_API_URL: { schema: (input) => input ?? '' },
	SECRET_KEY: { schema: (input) => input ?? '' },
	PUBLIC_API_BASE_URL: { public: true, schema: (input) => input ?? '' },
	PUBLIC_MARKET_DATA_CACHE_TTL: { public: true, schema: (input) => input ?? '' },
	PUBLIC_PRICE_HISTORY_CACHE_TTL: { public: true, schema: (input) => input ?? '' },
	PUBLIC_YFINANCE_CACHE_TTL: { public: true, schema: (input) => input ?? '' },
	PUBLIC_FX_RATES_CACHE_TTL: { public: true, schema: (input) => input ?? '' },
	PUBLIC_ENABLE_REGISTRATION: { public: true, schema: (input) => input ?? '' }
});
