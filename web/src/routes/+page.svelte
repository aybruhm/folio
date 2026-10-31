<script lang="ts">
    import Card from "#lib/components/Card.svelte";
    import Skeleton from "#lib/components/Skeleton.svelte";
    import LineChart from "#lib/components/LineChart.svelte";
    import BarChart from "#lib/components/BarChart.svelte";
    import DonutChart from "#lib/components/DonutChart.svelte";
    import Amount from "#lib/components/Amount.svelte";
    import Button from "#lib/components/Button.svelte";
    import Select from "#lib/components/Select.svelte";
    import StatCard from "#lib/components/StatCard.svelte";
    import ErrorState from "#lib/components/ErrorState.svelte";
    import { formatCurrency, formatPercent } from "#lib/utils/format.js";
    import { api } from "#lib/api/client.js";
    import { PortfolioController, AssetController } from "#lib/api/controllers/index.js";
    import type { PortfolioStats } from "#lib/api/types/index.js";
    import {
        getCachedAnalytics,
        setCachedAnalytics,
        getCachedAnalyticsSummary,
        setCachedAnalyticsSummary,
        getCachedBatchPriceHistory,
        setCachedBatchPriceHistory,
        buildBatchPriceHistoryKey,
    } from "#lib/cache/index.js";
    import { CURRENCIES } from "#lib/constants/currencies.js";
    import { cacheRefreshCounter } from "#lib/stores/cacheRefresh.js";
    import { currentPortfolio, displayCurrency } from "#lib/stores/index.js";
    import { onMount } from "svelte";

    interface PerformanceHolding {
        ticker: string;
        name: string;
        value: number;
        percent: number;
        currentPrice: number | null;
        dayChange: number | null;
        weekChange: number | null;
        monthChange: number | null;
    }

    const EMPTY_STATS: PortfolioStats = {
        id: "",
        current_value: 0,
        cost_basis: 0,
        gain_loss: 0,
        return_percent: 0,
        allocation: [],
        performance_history: [],
        contribution_history: [],
        top_holdings: [],
    };

    const currencyOptions = CURRENCIES.map((c) => ({
        label: c.value,
        value: c.value,
    }));

    let loading = true;
    let loadError: string | null = null;
    let fabOpen = false;
    let portfolioController: PortfolioController;
    let assetController: AssetController;
    let stats: PortfolioStats = EMPTY_STATS;
    // Currency the loaded figures are in; holdings prices are always USD.
    let currency = "USD";
    let portfolioCount = 0;
    let excludedCount = 0;

    let performanceLoading = false;
    let performanceError = false;
    let performanceHoldings: PerformanceHolding[] = [];
    let pricesAsOf: string | null = null;
    // Guard against an older response overwriting a newer one.
    let dashboardRequestId = 0;
    let performanceRequestId = 0;

    let lastLoadKey = "";
    let lastRefreshCount = 0;

    let currencyChoice = $displayCurrency;
    $: if (currencyChoice !== $displayCurrency) displayCurrency.set(currencyChoice);

    $: isAggregated = !$currentPortfolio?.id;
    $: isPositive = Number(stats.gain_loss) >= 0;
    $: hasActivity =
        Number(stats.current_value) > 0 ||
        (stats.performance_history?.length ?? 0) > 0 ||
        (stats.contribution_history?.length ?? 0) > 0;

    // Top positions, plus an "Other" slice so each slice keeps its real share.
    $: topHoldingsChart = (() => {
        const slices = (stats.top_holdings ?? []).map((h) => ({
            label: h.ticker,
            value: Number(h.percent),
        }));
        const rest = 100 - slices.reduce((sum, s) => sum + s.value, 0);
        if (slices.length > 0 && rest >= 0.1) {
            slices.push({ label: "Other", value: Math.round(rest * 100) / 100 });
        }
        return slices;
    })();

    $: contributionChart = (stats.contribution_history ?? []).map((d) => ({
        label: d.name,
        value: d.value,
    }));

    onMount(() => {
        portfolioController = new PortfolioController(api.getInstance());
        assetController = new AssetController(api.getInstance());
    });

    // Reload when the selected portfolio, display currency or refresh changes.
    $: loadKey = portfolioController
        ? `${$cacheRefreshCounter}:${$currentPortfolio?.id || "all"}:${$displayCurrency}`
        : "";

    $: if (loadKey && loadKey !== lastLoadKey) {
        lastLoadKey = loadKey;
        const force = $cacheRefreshCounter > lastRefreshCount;
        lastRefreshCount = $cacheRefreshCounter;
        void loadDashboardData(force);
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

    async function loadDashboardData(force = false) {
        const requestId = ++dashboardRequestId;
        loading = true;
        loadError = null;
        try {
            const portfolio = $currentPortfolio;
            let next: PortfolioStats;
            let nextCurrency: string;

            if (portfolio?.id) {
                const data = await cached(
                    force,
                    () => getCachedAnalytics(portfolio.id, "all"),
                    () =>
                        portfolioController.getPortfolioAnalytics({
                            portfolio_id: portfolio.id,
                            timeframe: "all",
                        }),
                    (d) => setCachedAnalytics(portfolio.id, "all", d),
                );
                if (requestId !== dashboardRequestId) return;
                nextCurrency = portfolio.base_currency || "USD";
                portfolioCount = 1;
                excludedCount = 0;
                next = toStats(data);
            } else {
                const target = $displayCurrency;
                const data = await cached(
                    force,
                    () => getCachedAnalyticsSummary("all", target),
                    () =>
                        portfolioController.getAnalyticsSummary({
                            timeframe: "all",
                            in_currency: target,
                        }),
                    (d) => setCachedAnalyticsSummary("all", target, d),
                );
                if (requestId !== dashboardRequestId) return;
                nextCurrency = data.currency;
                portfolioCount = data.portfolio_count;
                excludedCount = data.excluded_portfolio_ids?.length ?? 0;
                next = toStats(data);
            }

            stats = next;
            currency = nextCurrency;
            // Price history comes from external providers and can be slow;
            // the table has its own skeleton, so don't hold the page for it.
            void loadPerformanceData(
                (next.top_holdings ?? []).map((h) => ({
                    ticker: h.ticker,
                    name: h.name || h.ticker,
                    value: Number(h.value),
                    percent: Number(h.percent),
                })),
                force,
            );
        } catch (e) {
            if (requestId !== dashboardRequestId) return;
            console.error("Failed to load dashboard data:", e);
            loadError =
                e instanceof Error && e.message
                    ? e.message
                    : "The server didn't respond.";
        } finally {
            if (requestId === dashboardRequestId) loading = false;
        }
    }

    function toStats(data: {
        current_value: number;
        total_invested: number;
        total_gain_loss: number;
        total_gain_loss_percent: number;
        allocation: PortfolioStats["allocation"];
        performance_history: PortfolioStats["performance_history"];
        contribution_history: PortfolioStats["contribution_history"];
        top_holdings: PortfolioStats["top_holdings"];
    }): PortfolioStats {
        return {
            id: "dashboard",
            current_value: data.current_value,
            cost_basis: data.total_invested,
            gain_loss: data.total_gain_loss,
            return_percent: data.total_gain_loss_percent,
            allocation: data.allocation ?? [],
            performance_history: data.performance_history ?? [],
            contribution_history: data.contribution_history ?? [],
            top_holdings: data.top_holdings ?? [],
        };
    }

    // Percent change from the last close on or before `daysBack` days before
    // the latest close; null when the history doesn't reach that far.
    function changeSince(
        points: { date: string; close: number }[],
        daysBack: number,
    ): number | null {
        if (points.length < 2) return null;
        const latest = points[points.length - 1];
        const cutoff = new Date(latest.date);
        cutoff.setDate(cutoff.getDate() - daysBack);
        const cutoffIso = cutoff.toISOString().slice(0, 10);
        const reference = [...points].reverse().find((p) => p.date <= cutoffIso);
        if (!reference || reference.close <= 0) return null;
        return ((latest.close - reference.close) / reference.close) * 100;
    }

    async function loadPerformanceData(
        holdings: {
            ticker: string;
            name: string;
            value: number;
            percent: number;
        }[],
        force = false,
    ) {
        const requestId = ++performanceRequestId;
        performanceError = false;
        if (!holdings.length) {
            performanceHoldings = [];
            pricesAsOf = null;
            return;
        }
        performanceLoading = true;
        try {
            // A little over a month, so 30D still has a reference after weekends.
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 35);
            const startStr = start.toISOString().slice(0, 10);
            const endStr = end.toISOString().slice(0, 10);
            const tickers = holdings.map((h) => h.ticker);
            const batchKey = buildBatchPriceHistoryKey(tickers, startStr, endStr);

            const batch = await cached(
                force,
                () => getCachedBatchPriceHistory(batchKey),
                () =>
                    assetController.getBatchPriceHistory({
                        tickers,
                        start_date: startStr,
                        end_date: endStr,
                    }),
                (d) => setCachedBatchPriceHistory(batchKey, d),
            );

            const holdingByTicker = Object.fromEntries(
                holdings.map((h) => [h.ticker, h]),
            );
            let latestDate: string | null = null;

            const results: PerformanceHolding[] = batch.results.map(
                (history) => {
                    const h = holdingByTicker[history.ticker];
                    const points = (history.data || [])
                        .map((d) => ({ date: d.date, close: Number(d.close) }))
                        .filter((p) => p.close > 0 && Number.isFinite(p.close))
                        .sort((a, b) => a.date.localeCompare(b.date));
                    const latest = points[points.length - 1];
                    if (latest && (!latestDate || latest.date > latestDate)) {
                        latestDate = latest.date;
                    }

                    return {
                        ticker: history.ticker,
                        name: h?.name ?? history.ticker,
                        value: h?.value ?? 0,
                        percent: h?.percent ?? 0,
                        currentPrice: latest?.close ?? null,
                        dayChange: changeSince(points, 1),
                        weekChange: changeSince(points, 7),
                        monthChange: changeSince(points, 30),
                    };
                },
            );

            if (requestId === performanceRequestId) {
                performanceHoldings = results;
                pricesAsOf = latestDate;
            }
        } catch (e) {
            console.error("Failed to load holdings performance:", e);
            if (requestId === performanceRequestId) performanceError = true;
        } finally {
            if (requestId === performanceRequestId) {
                performanceLoading = false;
            }
        }
    }

    function retry() {
        void loadDashboardData(true);
    }

    function formatAsOf(isoDate: string): string {
        return new Date(`${isoDate}T00:00:00`).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
        });
    }

    const today = new Date().toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
    });
</script>

<svelte:head>
    <title>Dashboard — Folio</title>
</svelte:head>

<div class="min-h-screen p-4 md:p-6 lg:p-8">
    <div class="mx-auto max-w-7xl space-y-6">
        <!-- Header -->
        <div
            class="animate-in flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
        >
            <div class="space-y-1">
                <p
                    class="text-xs font-medium uppercase tracking-widest text-muted-foreground"
                >
                    {today}
                </p>
                <h1
                    class="font-serif text-3xl md:text-4xl text-foreground leading-tight"
                >
                    Dashboard
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    {#if isAggregated}
                        All portfolios · {currency}
                    {:else}
                        {$currentPortfolio?.name} · {currency}
                    {/if}
                </p>
            </div>
            {#if isAggregated}
                <div class="w-full md:w-40">
                    <Select
                        label="Display currency"
                        bind:value={currencyChoice}
                        options={currencyOptions}
                    />
                </div>
            {/if}
        </div>

        {#if loading}
            <div class="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
                {#each Array(4) as _}
                    <Card>
                        <Skeleton className="h-4 w-16 mb-3" />
                        <Skeleton className="h-9 w-3/4" />
                        <Skeleton className="h-3 w-1/2 mt-2" />
                    </Card>
                {/each}
            </div>
            {#each Array(2) as _}
                <Card><Skeleton className="h-48 md:h-72 w-full" /></Card>
            {/each}
            <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
                {#each Array(2) as _}
                    <Card><Skeleton className="h-48 w-full" /></Card>
                {/each}
            </div>
        {:else if loadError}
            <ErrorState
                title="Couldn't load your dashboard"
                message="Folio couldn't fetch your portfolio data ({loadError}). Your data is safe; check your connection and try again."
                onRetry={retry}
            />
        {:else if isAggregated && portfolioCount === 0}
            <Card>
                <div
                    class="flex flex-col items-center justify-center py-16 text-center"
                >
                    <p class="font-medium text-foreground mb-1">
                        Welcome to Folio
                    </p>
                    <p class="text-sm text-muted-foreground mb-6 max-w-md">
                        Create a portfolio to start tracking your investments.
                        Your dashboard fills in as you add trades.
                    </p>
                    <Button variant="default" href="/portfolios?new=true">
                        Create a portfolio
                    </Button>
                </div>
            </Card>
        {:else if !hasActivity}
            <Card>
                <div
                    class="flex flex-col items-center justify-center py-16 text-center"
                >
                    <p class="font-medium text-foreground mb-1">No trades yet</p>
                    <p class="text-sm text-muted-foreground mb-6 max-w-md">
                        {#if isAggregated}
                            Choose a portfolio in the switcher, then add a
                            trade or import a CSV from your broker.
                        {:else}
                            Add your first trade or import a CSV from your
                            broker to see performance here.
                        {/if}
                    </p>
                    <div class="flex flex-wrap justify-center gap-2">
                        <Button
                            variant="default"
                            href={isAggregated ? undefined : "/trades?new=true"}
                            disabled={isAggregated}
                        >
                            Add a trade
                        </Button>
                        <Button
                            variant="outline"
                            href={isAggregated ? undefined : "/trades/import"}
                            disabled={isAggregated}
                        >
                            Import CSV
                        </Button>
                    </div>
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
                        : `${excludedCount} portfolios are`} left out of these
                    totals: its exchange rate to {currency} is unavailable right
                    now.
                </div>
            {/if}

            <!-- Stat Cards -->
            <div
                class="animate-in animate-in-delay-1 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
            >
                <StatCard
                    label="Total Value"
                    value={stats.current_value}
                    {currency}
                    description="Current market value"
                />
                <StatCard
                    label="Cost Basis"
                    value={stats.cost_basis}
                    {currency}
                    description="Cost of current holdings"
                />
                <StatCard
                    label="Gain / Loss"
                    value={stats.gain_loss}
                    {currency}
                    tone={isPositive ? "positive" : "negative"}
                    description="Unrealized P&L"
                />
                <StatCard
                    label="Total Return"
                    value={stats.return_percent}
                    format="percent"
                    tone={isPositive ? "positive" : "negative"}
                    description="On current holdings' cost"
                />
            </div>

            <!-- Performance Chart -->
            <div class="animate-in animate-in-delay-2">
                <Card
                    title="Performance"
                    subtitle="Portfolio value over time"
                    className="md:px-4"
                >
                    <LineChart
                        data={stats.performance_history}
                        title=""
                        height="h-72 md:h-96"
                        {currency}
                    />
                </Card>
            </div>

            <!-- Contributions Chart -->
            <div class="animate-in animate-in-delay-2">
                <Card
                    title="Net Contributions"
                    subtitle="Buys minus sells each month"
                    className="md:px-4"
                >
                    <BarChart
                        data={contributionChart}
                        title=""
                        height="h-72 md:h-96"
                    />
                </Card>
            </div>

            <!-- Allocation + Top Holdings Donuts -->
            <div
                class="animate-in animate-in-delay-3 grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2"
            >
                <Card title="Allocation" subtitle="Asset class breakdown">
                    <DonutChart data={stats.allocation} title="" />
                </Card>

                <Card
                    title="Top Positions by Weight"
                    subtitle="10 largest positions, with the rest as Other"
                >
                    <DonutChart data={topHoldingsChart} title="" />
                </Card>
            </div>

            <!-- Top Holdings Performance -->
            <div class="animate-in animate-in-delay-4">
                <Card
                    title="Top Holdings Performance"
                    subtitle={pricesAsOf
                        ? `10 largest positions · prices in USD as of ${formatAsOf(pricesAsOf)}`
                        : "10 largest positions · prices in USD"}
                >
                    {#if performanceLoading}
                        <div class="space-y-3">
                            {#each Array(10) as _}
                                <div class="flex items-center justify-between">
                                    <div class="space-y-1.5 flex-1">
                                        <Skeleton className="h-4 w-20" />
                                        <Skeleton className="h-3 w-32" />
                                    </div>
                                    <Skeleton className="h-4 w-24" />
                                </div>
                            {/each}
                        </div>
                    {:else if performanceError}
                        <p class="py-8 text-center text-sm text-muted-foreground">
                            Couldn't load price history right now.
                            <button
                                class="underline underline-offset-2 hover:text-foreground"
                                on:click={retry}>Try again</button
                            >
                        </p>
                    {:else if performanceHoldings.length > 0}
                        <div class="overflow-x-auto -mx-4 md:mx-0">
                            <table class="w-full text-sm">
                                <thead class="border-b border-border">
                                    <tr>
                                        {#each ["Ticker", "Price", "Value", "1D", "7D", "30D"] as heading, i}
                                            <th
                                                class="h-9 px-3 align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                                class:text-left={i === 0}
                                                class:text-right={i > 0}
                                            >
                                                {heading}
                                            </th>
                                        {/each}
                                    </tr>
                                </thead>
                                <tbody class="[&_tr:last-child]:border-0">
                                    {#each performanceHoldings as h (h.ticker)}
                                        <tr
                                            class="border-b border-border/60 transition-colors"
                                        >
                                            <td class="px-3 py-3 align-middle">
                                                <div class="flex items-center gap-2">
                                                    <span
                                                        class="inline-block h-1 w-1 rounded-full flex-shrink-0
                                                        {h.monthChange == null
                                                            ? 'bg-muted-foreground'
                                                            : h.monthChange >= 0
                                                              ? 'bg-positive'
                                                              : 'bg-negative'}"
                                                    ></span>
                                                    <div>
                                                        <span
                                                            class="font-semibold text-foreground font-mono text-xs tracking-wide"
                                                        >
                                                            {h.ticker}
                                                        </span>
                                                        {#if h.name && h.name !== h.ticker}
                                                            <span
                                                                class="block text-xs text-muted-foreground leading-tight"
                                                            >
                                                                {h.name}
                                                            </span>
                                                        {/if}
                                                        <span
                                                            class="block text-xs text-muted-foreground"
                                                        >
                                                            <Amount
                                                                value={formatPercent(
                                                                    h.percent,
                                                                    2,
                                                                    false,
                                                                )}
                                                            /> of portfolio
                                                        </span>
                                                    </div>
                                                </div>
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right font-mono text-xs"
                                            >
                                                {#if h.currentPrice != null}
                                                    <Amount
                                                        value={formatCurrency(
                                                            h.currentPrice,
                                                            "USD",
                                                        )}
                                                    />
                                                {:else}
                                                    <span class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right font-mono text-xs"
                                            >
                                                {#if h.value > 0}
                                                    <Amount
                                                        value={formatCurrency(
                                                            h.value,
                                                            currency,
                                                        )}
                                                    />
                                                {:else}
                                                    <span class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            {#each [h.dayChange, h.weekChange, h.monthChange] as change}
                                                <td
                                                    class="px-3 py-3 align-middle text-right font-mono text-xs"
                                                >
                                                    {#if change != null}
                                                        <span
                                                            class:text-positive={change >= 0}
                                                            class:text-negative={change < 0}
                                                        >
                                                            <Amount
                                                                value={formatPercent(change)}
                                                            />
                                                        </span>
                                                    {:else}
                                                        <span class="text-muted-foreground"
                                                            >—</span
                                                        >
                                                    {/if}
                                                </td>
                                            {/each}
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {:else}
                        <p class="py-8 text-center text-sm text-muted-foreground">
                            No price history available for your holdings.
                        </p>
                    {/if}
                </Card>
            </div>
        {/if}
    </div>
</div>

<!-- Floating Action Button -->
<div class="fixed bottom-6 right-6 z-30 flex flex-col-reverse gap-2">
    {#if fabOpen}
        <!-- A trade needs a portfolio, so this is disabled in the aggregated view. -->
        <a
            href={$currentPortfolio?.id ? "/trades?new=true" : undefined}
            aria-disabled={!$currentPortfolio?.id}
            class="h-10 w-10 rounded-full bg-card border border-border text-foreground flex items-center justify-center transition-all shadow-lg {$currentPortfolio?.id
                ? 'hover:bg-muted'
                : 'opacity-50 cursor-not-allowed'}"
            title={$currentPortfolio?.id
                ? "New Trade"
                : "Select a portfolio to add a trade"}
        >
            <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                />
            </svg>
        </a>
        <a
            href="/portfolios"
            class="h-10 w-10 rounded-full bg-card border border-border text-foreground flex items-center justify-center hover:bg-muted transition-all shadow-lg"
            title="Manage Portfolios"
        >
            <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
            </svg>
        </a>
        <a
            href="/analytics"
            class="h-10 w-10 rounded-full bg-card border border-border text-foreground flex items-center justify-center hover:bg-muted transition-all shadow-lg"
            title="View Analytics"
        >
            <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
            </svg>
        </a>
    {/if}

    <button
        on:click={() => (fabOpen = !fabOpen)}
        class="h-11 w-11 rounded-full bg-accent text-accent-foreground flex items-center justify-center hover:bg-accent/90 transition-all shadow-lg shadow-accent/25 {fabOpen
            ? 'rotate-45'
            : ''}"
        title="Actions"
    >
        <svg
            class="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 4v16m8-8H4"
            />
        </svg>
    </button>
</div>
