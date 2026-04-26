<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import LineChart from "$lib/components/LineChart.svelte";
    import DonutChart from "$lib/components/DonutChart.svelte";
    import { formatCurrency, formatPercent } from "$lib/utils/format";
    import { currentPortfolio } from "$lib/stores";
    import { api } from "$lib/api/client";
    import { PortfolioController } from "$lib/api/controllers";
    import type { PortfolioStats } from "$lib/api/types";
    import { onMount } from "svelte";

    let loading = true;
    let fabOpen = false;
    let portfolioController: PortfolioController;
    let stats: PortfolioStats = {
        id: "",
        current_value: 0,
        cost_basis: 0,
        gain_loss: 0,
        return_percent: 0,
        allocation: [],
        performance_history: [],
        top_holdings: [],
    };

    $: topHoldingsChart =
        stats.top_holdings?.map((h) => ({
            label: h.ticker,
            value: parseFloat(h.percent),
        })) ?? [];

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        if ($currentPortfolio) await loadDashboardData();
    });

    $: if ($currentPortfolio && portfolioController) loadDashboardData();

    async function loadDashboardData() {
        try {
            loading = true;
            const [analyticsData, holdingsResponse] = await Promise.all([
                portfolioController.getPortfolioAnalytics({
                    portfolio_id: $currentPortfolio?.id,
                    timeframe: "1y",
                }),
                portfolioController.getHoldings({
                    portfolio_id: $currentPortfolio?.id,
                }),
            ]);

            const holdings = holdingsResponse.data ?? [];

            const currentValue = holdings.reduce(
                (s, h) => s + parseFloat(h.total_value),
                0,
            );
            const costBasis = holdings.reduce(
                (s, h) => s + parseFloat(h.avg_price) * parseFloat(h.quantity),
                0,
            );
            const gainLoss = holdings.reduce(
                (s, h) => s + parseFloat(h.gain_loss),
                0,
            );

            stats = {
                id: $currentPortfolio?.id,
                current_value: currentValue,
                cost_basis: costBasis,
                gain_loss: gainLoss,
                return_percent: costBasis > 0 ? (gainLoss / costBasis) * 100 : 0,
                allocation: analyticsData.allocation ?? [],
                performance_history: analyticsData.performance_history ?? [],
                top_holdings: holdings.slice(0, 5).map((h) => ({
                    ticker: h.ticker,
                    value: h.total_value,
                    percent: h.gain_loss_percent,
                })),
            };
        } catch (e) {
            console.error("Failed to load dashboard data:", e);
        } finally {
            loading = false;
        }
    }

    $: isPositive = Number(stats.gain_loss) >= 0;
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
    <div class="mx-auto max-w-7xl space-y-6">
        <!-- Header -->
        <div class="space-y-2">
            <h1 class="text-2xl md:text-3xl font-bold text-foreground">
                Dashboard
            </h1>
            <p class="text-xs md:text-sm text-muted-foreground">
                {#if $currentPortfolio}
                    <span>{$currentPortfolio.name}</span>
                    {#if $currentPortfolio.description}
                        <span class="text-xs"
                            >· {$currentPortfolio.description}</span
                        >
                    {/if}
                {/if}
            </p>
        </div>

        {#if loading}
            <div class="flex justify-center py-12">
                <div class="text-muted-foreground">
                    Loading portfolio data...
                </div>
            </div>
        {:else}
            <!-- Stats Cards -->
            <div class="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
                <Card title="Total Value" subtitle="Current portfolio value">
                    <div class="text-xl sm:text-2xl md:text-3xl font-bold text-foreground leading-tight break-all">
                        {formatCurrency(stats.current_value)}
                    </div>
                </Card>

                <Card title="Cost Basis" subtitle="Total amount invested">
                    <div class="text-xl sm:text-2xl md:text-3xl font-bold text-foreground leading-tight break-all">
                        {formatCurrency(stats.cost_basis)}
                    </div>
                </Card>

                <Card title="Gain/Loss" subtitle="Unrealized P&L">
                    <div
                        class="text-xl sm:text-2xl md:text-3xl font-bold leading-tight break-all"
                        class:text-positive={isPositive}
                        class:text-negative={!isPositive}
                    >
                        {formatCurrency(stats.gain_loss)}
                    </div>
                </Card>

                <Card title="Return" subtitle="Total return %">
                    <div
                        class="text-xl sm:text-2xl md:text-3xl font-bold leading-tight"
                        class:text-positive={isPositive}
                        class:text-negative={!isPositive}
                    >
                        {formatPercent(stats.return_percent)}
                    </div>
                </Card>
            </div>

            <!-- Performance Chart -->
            <Card title="Performance" subtitle="Portfolio value over time">
                <LineChart
                    data={stats.performance_history}
                    title=""
                    height="h-72 md:h-96"
                />
            </Card>

            <!-- Allocation + Top Holdings Donuts -->
            <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
                <Card title="Allocation" subtitle="Asset class breakdown">
                    <DonutChart data={stats.allocation} title="" />
                </Card>

                <Card
                    title="Top Holdings"
                    subtitle="5 largest positions by weight"
                >
                    <DonutChart data={topHoldingsChart} title="" />
                </Card>
            </div>

            <!-- Top Holdings List -->
            <Card title="Top Holdings" subtitle="5 largest positions">
                <div class="space-y-2">
                    {#each stats.top_holdings ?? [] as holding}
                        <div class="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 md:px-4 md:py-3">
                            <div class="flex flex-col gap-0.5 min-w-0">
                                <span class="text-sm md:text-base font-semibold text-foreground truncate">
                                    {holding.ticker}
                                </span>
                                <span class="text-xs text-muted-foreground">
                                    {formatPercent(holding.percent)} of portfolio
                                </span>
                            </div>
                            <div class="text-right ml-2 shrink-0">
                                <div class="text-sm md:text-base font-semibold text-foreground">
                                    {formatCurrency(holding.value)}
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            </Card>
        {/if}
    </div>
</div>

<!-- Floating Action Button -->
<div class="fixed bottom-6 right-6 z-30 flex flex-col-reverse gap-2">
    {#if fabOpen}
        <a
            href="/trades/new"
            class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
            title="New Trade"
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
        </a>
        <a
            href="/portfolios"
            class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
            title="Manage Portfolios"
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
            class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
            title="View Analytics"
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
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
            </svg>
        </a>
    {/if}

    <button
        on:click={() => (fabOpen = !fabOpen)}
        class="h-10 w-10 rounded-full bg-accent text-accent-foreground flex items-center justify-center hover:bg-accent/90 transition-all {fabOpen
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
