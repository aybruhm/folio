import { writable, derived } from "svelte/store";

export interface AuthUser {
    id: string;
    email: string;
}

export interface Portfolio {
    id: string;
    name: string;
    base_currency: string;
    description?: string;
    created_at: string;
    updated_at: string;
}

export interface Trade {
    id: string;
    portfolio_id: string;
    ticker: string;
    trade_type: string;
    trade_date: string;
    quantity: string;
    price: string;
    trade_currency: string;
    fees: string;
}

export interface UserPreferences {
    displayCurrency: string;
    dateFormat: string;
    theme: "dark" | "light";
}

export const portfolios = writable<Portfolio[]>([]);
export const currentPortfolio = writable<Portfolio>({
    id: "",
    name: "",
    base_currency: "USD",
    created_at: "",
    updated_at: "",
});
export const trades = writable<Trade[]>([]);

export const userPreferences = writable<UserPreferences>({
    displayCurrency: "USD",
    dateFormat: "YYYY-MM-DD",
    theme: "dark",
});

export const isLoading = writable(false);
export const error = writable<string | null>(null);

export const portfolioCount = derived(
    portfolios,
    ($portfolios) => $portfolios.length,
);

export const authUser = writable<AuthUser | null>(null);
export const isAuthenticated = derived(authUser, ($user) => $user !== null);
