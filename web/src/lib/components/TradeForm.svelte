<script lang="ts">
    import Input from "./Input.svelte";
    import Select from "./Select.svelte";
    import Button from "./Button.svelte";
    import { createEventDispatcher } from "svelte";
    import { CURRENCIES } from "$lib/constants/currencies";
    import { formatCurrency } from "$lib/utils/format";
    import { api } from "$lib/api/client";
    import { AssetController } from "$lib/api/controllers";

    const dispatch = createEventDispatcher();

    export let trade: {
        ticker: string;
        trade_type: string;
        trade_date: string;
        quantity: string;
        price: string;
        trade_currency: string;
        fees: string;
        asset_class?: string;
        market_data_provider?:
            | "yfinance"
            | "tiingo"
            | "ngnmarket"
            | "ngxpulse"
            | "tradingview";
    } = {
        ticker: "",
        trade_type: "buy",
        trade_date: new Date().toISOString().slice(0, 16),
        quantity: "",
        price: "",
        trade_currency: "USD",
        fees: "0",
        asset_class: "",
        market_data_provider: "yfinance",
    };
    export let isLoading = false;

    const tradeTypes = [
        { label: "Buy", value: "buy" },
        { label: "Sell", value: "sell" },
        { label: "Dividend", value: "dividend" },
        { label: "Fee", value: "fee" },
    ];

    const marketDataProviders = [
        { label: "Yahoo Finance", value: "yfinance" },
        { label: "Tiingo", value: "tiingo" },
        { label: "NGNMarket", value: "ngnmarket" },
        { label: "NGXPulse", value: "ngxpulse" },
        { label: "TradingView", value: "tradingview" },
    ];

    const assetClasses = [
        { label: "Auto-detect", value: "" },
        { label: "Stock", value: "stock" },
        { label: "ETF", value: "etf" },
        { label: "Crypto", value: "crypto" },
        { label: "Cash", value: "cash" },
    ];

    const currencies = CURRENCIES.map((c) => ({
        label: c.label,
        value: c.value,
    }));

    let errors: Record<string, string> = {};
    let isSubmitting = false;
    let validatingTicker = false;
    let validationResult: "supported" | "unsupported" | null = null;
    let validationMessage = "";

    const assetController = new AssetController(api.getInstance());

    $: if (!trade.market_data_provider) {
        trade.market_data_provider = "yfinance";
    }

    $: canValidate =
        Boolean(trade.ticker?.trim()) && Boolean(trade.market_data_provider);

    $: totalAmount = (
        (parseFloat(trade.quantity || "0") || 0) *
            (parseFloat(trade.price || "0") || 0) +
        (parseFloat(trade.fees || "0") || 0)
    ).toFixed(2);

    $: showTotal =
        parseFloat(trade.quantity || "0") > 0 &&
        parseFloat(trade.price || "0") > 0;

    async function validateTicker() {
        if (!canValidate) return;

        validatingTicker = true;
        validationResult = null;
        validationMessage = "";

        try {
            const result = await assetController.validateTicker(
                trade.ticker.trim(),
                trade.market_data_provider || "yfinance",
                trade.trade_currency || "USD",
                trade.asset_class || "",
            );

            validationResult = result.supported ? "supported" : "unsupported";
            validationMessage = result.supported
                ? `Ticker is supported by ${result.provider}.`
                : `Ticker is not supported by ${result.provider}.`;
        } catch (e: unknown) {
            validationResult = "unsupported";
            validationMessage =
                e instanceof Error
                    ? e.message
                    : "Unable to validate ticker right now.";
        } finally {
            validatingTicker = false;
        }
    }

    async function handleSubmit() {
        errors = {};

        if (!trade.ticker) errors.ticker = "Ticker is required";
        if (!trade.quantity) errors.quantity = "Quantity is required";
        if (!trade.price) errors.price = "Price is required";

        if (Object.keys(errors).length > 0) return;

        isSubmitting = true;
        try {
            dispatch("submit", trade);
        } catch (e: unknown) {
            const message =
                e instanceof Error ? e.message : "An error occurred";
            errors.submit = message;
        } finally {
            isSubmitting = false;
        }
    }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div class="space-y-2">
            <Input
                label="Ticker"
                placeholder="AAPL"
                bind:value={trade.ticker}
                required
                error={errors.ticker}
            />

            <div class="flex items-center gap-2">
                <button
                    type="button"
                    class="text-xs text-muted-foreground underline-offset-2 hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                    on:click={validateTicker}
                    disabled={!canValidate || validatingTicker}
                    title="Check if the ticker is supported by the selected data platform"
                >
                    {validatingTicker ? "Validating..." : "Validate"}
                </button>

                {#if validationResult === "supported"}
                    <span class="text-xs text-green-600 dark:text-green-400"
                        >Supported</span
                    >
                {:else if validationResult === "unsupported"}
                    <span class="text-xs text-amber-600 dark:text-amber-400"
                        >Not supported</span
                    >
                {/if}
            </div>

            {#if validationMessage}
                <div class="text-xs text-muted-foreground">
                    {validationMessage}
                </div>
            {/if}
        </div>

        <Select
            label="Asset Class"
            bind:value={trade.asset_class}
            options={assetClasses}
        />
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
            label="Trade Type"
            bind:value={trade.trade_type}
            options={tradeTypes}
            required
        />

        <Select
            label="Market Data"
            bind:value={trade.market_data_provider}
            options={marketDataProviders}
            required
        />
    </div>

    <Input
        label="Trade Date & Time"
        type="datetime-local"
        bind:value={trade.trade_date}
        required
        error={errors.trade_date}
    />

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
            label="Quantity"
            type="number"
            step="0.0001"
            placeholder="0.0001"
            bind:value={trade.quantity}
            required
            error={errors.quantity}
        />

        <Input
            label="Price"
            type="number"
            step="0.01"
            placeholder="150.00"
            bind:value={trade.price}
            required
            error={errors.price}
        />
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
            label="Currency"
            bind:value={trade.trade_currency}
            options={currencies}
        />

        <Input
            label="Fees"
            type="number"
            step="0.01"
            placeholder="0.00"
            bind:value={trade.fees}
        />
    </div>

    {#if showTotal}
        <div class="rounded-md border border-border bg-muted/50 p-3">
            <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-muted-foreground"
                    >Total</span
                >
                <span class="text-lg font-semibold text-foreground">
                    {formatCurrency(totalAmount, trade.trade_currency)}
                </span>
            </div>
            <div class="mt-1 text-xs text-muted-foreground">
                (Quantity × Price){#if parseFloat(trade.fees || "0") > 0}
                    + Fees
                {/if}
            </div>
        </div>
    {/if}

    {#if errors.submit}
        <div class="text-red-600 dark:text-red-400 text-sm">
            {errors.submit}
        </div>
    {/if}

    <div class="flex gap-3">
        <Button
            type="submit"
            variant="default"
            disabled={isSubmitting || isLoading}
        >
            {isSubmitting || isLoading ? "Saving..." : "Save Trade"}
        </Button>
    </div>
</form>
