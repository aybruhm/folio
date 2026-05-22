import { writable, derived } from "svelte/store";
import { browser } from "$app/environment";

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

const CURRENT_PORTFOLIO_STORAGE_KEY = "folio.currentPortfolioId";

export const AGGREGATED_PORTFOLIO: Portfolio = {
    id: "",
    name: "",
    base_currency: "USD",
    created_at: "",
    updated_at: "",
};

function persistCurrentPortfolioSelection(id: string) {
    if (!browser) return;

    if (!id) {
        localStorage.removeItem(CURRENT_PORTFOLIO_STORAGE_KEY);
        return;
    }

    localStorage.setItem(CURRENT_PORTFOLIO_STORAGE_KEY, id);
}

function getSavedPortfolioId(): string {
    if (!browser) return "";
    return localStorage.getItem(CURRENT_PORTFOLIO_STORAGE_KEY) || "";
}

function createCurrentPortfolioStore() {
    const { subscribe, set: baseSet, update: baseUpdate } =
        writable<Portfolio>(AGGREGATED_PORTFOLIO);

    return {
        subscribe,
        set: (portfolio: Portfolio) => {
            baseSet(portfolio);
            persistCurrentPortfolioSelection(portfolio?.id || "");
        },
        update: (updater: (value: Portfolio) => Portfolio) => {
            baseUpdate((current) => {
                const next = updater(current);
                persistCurrentPortfolioSelection(next?.id || "");
                return next;
            });
        },
    };
}

export const currentPortfolio = createCurrentPortfolioStore();

export function selectInitialPortfolio(availablePortfolios: Portfolio[]) {
    const savedId = getSavedPortfolioId();

    if (!savedId) {
        currentPortfolio.set(availablePortfolios[0] || AGGREGATED_PORTFOLIO);
        return;
    }

    const matched = availablePortfolios.find((p) => p.id === savedId);
    currentPortfolio.set(
        matched || availablePortfolios[0] || AGGREGATED_PORTFOLIO,
    );
}

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

export const baseCurrency = derived(
    [currentPortfolio, portfolios],
    ([$cp, $portfolios]) => {
        if ($cp?.id && $cp?.base_currency) return $cp.base_currency;
        // Aggregated view: use the first portfolio's base currency if available
        if ($portfolios.length > 0)
            return $portfolios[0].base_currency || "USD";
        return "USD";
    },
);

function createHideAmountsStore() {
    const HIDE_AMOUNTS_STORAGE_KEY = "folio.hideAmounts";

    const stored = browser ? localStorage.getItem(HIDE_AMOUNTS_STORAGE_KEY) : null;
    const initial = stored === "true";

    const { subscribe, set, update } = writable<boolean>(initial);

    return {
        subscribe,
        set: (value: boolean) => {
            if (browser) {
                localStorage.setItem(HIDE_AMOUNTS_STORAGE_KEY, String(value));
            }
            set(value);
        },
        toggle: () => {
            update((current) => {
                const next = !current;
                if (browser) {
                    localStorage.setItem(HIDE_AMOUNTS_STORAGE_KEY, String(next));
                }
                return next;
            });
        },
        update,
    };
}

export const hideAmounts = createHideAmountsStore();

export const authUser = writable<AuthUser | null>(null);
export const isAuthenticated = derived(authUser, ($user) => $user !== null);
