<script lang="ts">
    import Card from "#lib/components/Card.svelte";
    import Skeleton from "#lib/components/Skeleton.svelte";
    import LineChart from "#lib/components/LineChart.svelte";
    import BarChart from "#lib/components/BarChart.svelte";
    import DonutChart from "#lib/components/DonutChart.svelte";
    import Select from "#lib/components/Select.svelte";
    import Button from "#lib/components/Button.svelte";
    import Amount from "#lib/components/Amount.svelte";
    import Tooltip from "#lib/components/Tooltip.svelte";
    import StatCard from "#lib/components/StatCard.svelte";
    import ErrorState from "#lib/components/ErrorState.svelte";
    import { currentPortfolio, portfolios, displayCurrency } from "#lib/stores/index.js";
    import { api } from "#lib/api/client.js";
    import { PortfolioController } from "#lib/api/controllers/index.js";
    import type { GetPortfolioAnalyticsResponse } from "#lib/api/types/index.js";
    import { formatPercent } from "#lib/utils/format.js";
    import {
        getCachedAnalytics,
        setCachedAnalytics,
        getCachedAnalyticsSummary,
        setCachedAnalyticsSummary,
    } from "#lib/cache/index.js";
    import { CURRENCIES } from "#lib/constants/currencies.js";
    import { cacheRefreshCounter } from "#lib/stores/cacheRefresh.js";
    import { onMount } from "svelte";

    type Analytics = Omit<GetPortfolioAnalyticsResponse, "portfolio_id">;

    const timeframeOptions = [
        { label: "YTD", value: "ytd", description: "Year to date" },
        { label: "3M", value: "3m", description: "Last 3 months" },
        { label: "1Y", value: "1y", description: "Last 12 months" },
        { label: "3Y", value: "3y", description: "Last 3 years" },
        { label: "5Y", value: "5y", description: "Last 5 years" },
        { label: "All", value: "all", description: "Since your first trade" },
    ];

    const currencyOptions = CURRENCIES.map((c) => ({
        label: c.value,
        value: c.value,
    }));

    let loading = true;
    let loadError: string | null = null;
    let timeframe = "1y";
    let portfolioController: PortfolioController;
    let analyticsData: Analytics | null = null;
    // Currency the loaded figures are in.
    let currency = "USD";
    let portfolioCount = 0;
    let excludedCount = 0;

    let lastLoadKey = "";
    let lastRefreshCount = 0;
    // Guards against an older response overwriting a newer one.
    let requestCounter = 0;

    let currencyChoice = $displayCurrency;
    $: if (currencyChoice !== $displayCurrency) displayCurrency.set(currencyChoice);

    $: isAggregated = !$currentPortfolio?.id;
    $: periodLabel =
        timeframeOptions.find((o) => o.value === timeframe)?.description ?? "";
    $: hasActivity =
        !!analyticsData &&
        (Number(analyticsData.current_value) > 0 ||
            analyticsData.performance_history.length > 0 ||
            analyticsData.contribution_history.length > 0);
    $: gainPositive = Number(analyticsData?.total_gain_loss ?? 0) >= 0;
    $: contribChart = (analyticsData?.contribution_history ?? []).map((d) => ({
        label: d.name,
        value: d.value,
    }));

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        // Load portfolios if not already loaded
        if ($portfolios.length === 0) {
            try {
                const data = await portfolioController.listPortfolios();
                portfolios.set((data || []) as any);
            } catch (e) {
                console.error("Failed to load portfolios:", e);
            }
        }
    });

    $: loadKey = portfolioController
        ? `${$cacheRefreshCounter}:${$currentPortfolio?.id || "all"}:${timeframe}:${$displayCurrency}:${$portfolios.map((p) => p.id).join(",")}`
        : "";

    $: if (loadKey && loadKey !== lastLoadKey) {
        lastLoadKey = loadKey;
        const force = $cacheRefreshCounter > lastRefreshCount;
        lastRefreshCount = $cacheRefreshCounter;
        void loadAnalytics(force);
    }

    // Cache first, then the API; a forced refresh falls back to the cache.
    async function cached<T>(
        force: boolean,
        read: () => Promise<T | null>,
        fetch: () => Promise<T>,
        write: (data: T) => Promise<void>,
    ): Promise<T> {
        const hit = force ? null : await read();
        if (hit) return hit;
        try {
            const data = await fetch();
            await write(data);
            return data;
        } catch (e) {
            const fallback = force ? await read() : null;
            if (fallback) return fallback;
            throw e;
        }
    }

    async function loadAnalytics(force = false) {
        const requestId = ++requestCounter;
        const selectedTimeframe = timeframe;
        loading = true;
        loadError = null;
        try {
            const portfolio = $currentPortfolio;
            if (portfolio?.id) {
                const data = await cached(
                    force,
                    () => getCachedAnalytics(portfolio.id, selectedTimeframe),
                    () =>
                        portfolioController.getPortfolioAnalytics({
                            portfolio_id: portfolio.id,
                            timeframe: selectedTimeframe,
                        }),
                    (d) => setCachedAnalytics(portfolio.id, selectedTimeframe, d),
                );
                if (requestId !== requestCounter) return;
                analyticsData = data;
                currency = portfolio.base_currency || "USD";
                portfolioCount = 1;
                excludedCount = 0;
            } else {
                // All portfolios, merged and converted server-side
                const target = $displayCurrency;
                const data = await cached(
                    force,
                    () => getCachedAnalyticsSummary(selectedTimeframe, target),
                    () =>
                        portfolioController.getAnalyticsSummary({
                            timeframe: selectedTimeframe,
                            in_currency: target,
                        }),
                    (d) => setCachedAnalyticsSummary(selectedTimeframe, target, d),
                );
                if (requestId !== requestCounter) return;
                analyticsData = data;
                currency = data.currency;
                portfolioCount = data.portfolio_count;
                excludedCount = data.excluded_portfolio_ids?.length ?? 0;
            }
        } catch (e) {
            if (requestId !== requestCounter) return;
            console.error("Failed to load analytics:", e);
            loadError =
                e instanceof Error && e.message
                    ? e.message
                    : "The server didn't respond.";
        } finally {
            if (requestId === requestCounter) loading = false;
        }
    }

    function returnTone(value: string | undefined) {
        return parseFloat(value ?? "0") >= 0 ? "text-positive" : "text-negative";
    }
</script>

<svelte:head>
    <title>Analytics — Folio</title>
</svelte:head>

<div class="min-h-screen p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
        >
            <div class="space-y-2">
                <h1 class="font-serif text-3xl md:text-4xl text-foreground">
                    Analytics
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    {#if isAggregated}
                        All portfolios · {currency}
                    {:else}
                        {$currentPortfolio?.name} · {currency}
                    {/if}
                </p>
            </div>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
                {#if isAggregated}
                    <div class="w-full sm:w-32">
                        <Select
                            label="Currency"
                            bind:value={currencyChoice}
                            options={currencyOptions}
                        />
                    </div>
                {/if}
                <div
                    class="inline-flex h-10 items-center rounded-md border border-input bg-background p-1"
                    role="group"
                    aria-label="Timeframe"
                >
                    {#each timeframeOptions as option}
                        <button
                            type="button"
                            class="h-full rounded px-2.5 text-xs font-medium transition-colors {timeframe ===
                            option.value
                                ? 'bg-muted text-foreground'
                                : 'text-muted-foreground hover:text-foreground'}"
                            aria-pressed={timeframe === option.value}
                            title={option.description}
                            on:click={() => (timeframe = option.value)}
                        >
                            {option.label}
                        </button>
                    {/each}
                </div>
            </div>
        </div>

        {#if loading}
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {#each Array(3) as _}
                    <Card>
                        <Skeleton className="h-4 w-16 mb-3" />
                        <Skeleton className="h-9 w-3/4" />
                    </Card>
                {/each}
            </div>
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                {#each Array(2) as _}
                    <Card>
                        <Skeleton className="h-4 w-1/3" />
                        <Skeleton className="h-8 w-40 mt-2" />
                    </Card>
                {/each}
            </div>
            <Card><Skeleton className="h-48 md:h-96 w-full" /></Card>
            <Card><Skeleton className="h-48 md:h-96 w-full" /></Card>
        {:else if loadError}
            <ErrorState
                title="Couldn't load analytics"
                message="Folio couldn't fetch your analytics ({loadError}). Check your connection and try again."
                onRetry={() => loadAnalytics(true)}
            />
        {:else if isAggregated && portfolioCount === 0}
            <Card>
                <div
                    class="flex flex-col items-center justify-center py-16 text-center"
                >
                    <p class="font-medium text-foreground mb-1">
                        No portfolios yet
                    </p>
                    <p class="text-sm text-muted-foreground mb-6 max-w-md">
                        Create a portfolio and add trades to see returns,
                        allocation and history here.
                    </p>
                    <Button variant="default" href="/portfolios?new=true">
                        Create a portfolio
                    </Button>
                </div>
            </Card>
        {:else if !hasActivity || !analyticsData}
            <Card>
                <div
                    class="flex flex-col items-center justify-center py-16 text-center"
                >
                    <p class="font-medium text-foreground mb-1">
                        Nothing to analyse yet
                    </p>
                    <p class="text-sm text-muted-foreground max-w-md">
                        Analytics appear once {isAggregated
                            ? "your portfolios have"
                            : "this portfolio has"} trades.
                    </p>
                </div>
            </Card>
        {:else}
            {#if excludedCount > 0}
                <div
                    class="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"
                    role="status"
                >
                    {excludedCount === 1
                        ? "1 portfolio is"
                        : `${excludedCount} portfolios are`} left out: its exchange
                    rate to {currency} is unavailable right now.
                </div>
            {/if}

            <!-- Current position (independent of the timeframe) -->
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatCard
                    label="Current Value"
                    value={analyticsData.current_value}
                    {currency}
                    description="Market value today"
                />
                <StatCard
                    label="Cost Basis"
                    value={analyticsData.total_invested}
                    {currency}
                    description="Cost of current holdings"
                />
                <StatCard
                    label="Unrealized Gain / Loss"
                    value={analyticsData.total_gain_loss}
                    {currency}
                    tone={gainPositive ? "positive" : "negative"}
                    description="Today, on current holdings"
                />
            </div>

            <!-- Returns for the selected timeframe -->
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                {#each [{ key: "twr", title: "Time-Weighted Return", short: "TWR", help: "How your investments performed, ignoring when and how much money you added or withdrew. Use it to compare against a benchmark or fund." }, { key: "mwr", title: "Money-Weighted Return", short: "MWR", help: "Your actual return including the timing and size of your deposits and withdrawals (an IRR). Adding money before a rise lifts it; before a fall lowers it." }] as metric}
                    {@const value = metric.key === "twr" ? analyticsData.twr : analyticsData.mwr}
                    <Card>
                        <div class="mb-3 md:mb-4 flex items-start justify-between gap-2">
                            <div>
                                <h3
                                    class="text-sm font-semibold tracking-tight text-card-foreground"
                                >
                                    {metric.title} ({metric.short})
                                </h3>
                                <p class="mt-0.5 text-xs text-muted-foreground">
                                    {periodLabel}
                                </p>
                            </div>
                            <Tooltip text={metric.help} position="left" wrap>
                                <button
                                    type="button"
                                    class="flex h-6 w-6 items-center justify-center rounded-full border border-border text-xs text-muted-foreground hover:text-foreground"
                                    aria-label="What is {metric.short}? {metric.help}"
                                >
                                    ?
                                </button>
                            </Tooltip>
                        </div>
                        <div class="font-serif text-4xl {returnTone(value)}">
                            <Amount value={formatPercent(value)} />
                        </div>
                    </Card>
                {/each}
            </div>

            <!-- Performance History -->
            <Card title="Performance History" subtitle={periodLabel}>
                <LineChart
                    data={analyticsData.performance_history}
                    title=""
                    height="h-72 md:h-96"
                    {currency}
                />
            </Card>

            <!-- Contributions -->
            <Card
                title="Net Contributions"
                subtitle="Buys minus sells each month · {periodLabel}"
            >
                <BarChart data={contribChart} title="" height="h-72 md:h-96" />
            </Card>

            <!-- Asset Allocation and Sector Breakdown -->
            <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
                <Card title="Asset Allocation" subtitle="Current holdings">
                    <DonutChart data={analyticsData.allocation} title="" />
                </Card>

                <Card title="Sector Breakdown" subtitle="Current holdings">
                    <DonutChart
                        data={analyticsData.sector_breakdown}
                        title=""
                    />
                </Card>
            </div>
        {/if}
    </div>
</div>
