<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import Skeleton from "$lib/components/Skeleton.svelte";
    import LineChart from "$lib/components/LineChart.svelte";
    import DonutChart from "$lib/components/DonutChart.svelte";
    import Amount from "$lib/components/Amount.svelte";
    import { formatCurrency, formatPercent } from "$lib/utils/format";
    import { api } from "$lib/api/client";
    import { PortfolioController, AssetController } from "$lib/api/controllers";
    import type { PortfolioStats } from "$lib/api/types";
    import {
        getCachedListAnalytics,
        setCachedListAnalytics,
        getCachedBatchPriceHistory,
        setCachedBatchPriceHistory,
        buildBatchPriceHistoryKey,
    } from "$lib/cache";
    import { cacheRefreshCounter } from "$lib/stores/cacheRefresh";
    import { onMount } from "svelte";

    let loading = true;
    let fabOpen = false;
    let portfolioController: PortfolioController;
    let assetController: AssetController;
    let performanceLoading = false;
    let performanceHoldings: PerformanceHolding[] = [];

    interface PerformanceHolding {
        ticker: string;
        name: string;
        value: number;
        percent: number;
        currentPrice: number | null;
        dayChange: number | null;
        weekAvg: number | null;
        monthAvg: number | null;
        monthChange: number | null;
    }
    let stats: PortfolioStats = {
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

    $: topHoldingsChart =
        stats.top_holdings?.map((h) => ({
            label: h.ticker,
            value: Number(h.percent),
        })) ?? [];

    const monthOrder = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ];

    const getTimeFromLabel = (label: string) => {
        const trimmed = label.trim();
        const isoTime = Date.parse(trimmed);
        if (!Number.isNaN(isoTime)) return isoTime;

        const parts = trimmed.split(" ");
        if (parts.length >= 2) {
            const monthIndex = monthOrder.indexOf(parts[0]);
            const year = Number(parts[1]);
            if (monthIndex >= 0 && !Number.isNaN(year)) {
                return new Date(year, monthIndex, 1).getTime();
            }
        }

        return 0;
    };

    let lastRefreshCount = 0;

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        assetController = new AssetController(api.getInstance());
        await loadDashboardData(false);
    });

    $: if ($cacheRefreshCounter > lastRefreshCount && portfolioController) {
        lastRefreshCount = $cacheRefreshCounter;
        void loadDashboardData(true);
    }

    async function loadDashboardData(force = false) {
        try {
            loading = true;
            let analyticsList = force
                ? null
                : await getCachedListAnalytics("1y", "USD");
            if (!analyticsList) {
                try {
                    analyticsList =
                        await portfolioController.listPortfolioAnalytics({
                            timeframe: "1y",
                            in_currency: "USD",
                        });
                    await setCachedListAnalytics("1y", "USD", analyticsList);
                } catch (apiError) {
                    if (force) {
                        analyticsList = await getCachedListAnalytics(
                            "1y",
                            "USD",
                        );
                    }
                    if (!analyticsList) throw apiError;
                }
            }

            const analyticsData = (analyticsList || []).reduce(
                (acc, item) => {
                    acc.total_invested += Number(item.total_invested || 0);
                    acc.current_value += Number(item.current_value || 0);
                    acc.total_gain_loss += Number(item.total_gain_loss || 0);
                    acc.allocation.push(...(item.allocation || []));
                    acc.performance_history.push(
                        ...(item.performance_history || []),
                    );
                    acc.contribution_history.push(
                        ...(item.contribution_history || []),
                    );
                    acc.top_holdings.push(...(item.top_holdings || []));
                    return acc;
                },
                {
                    total_invested: 0,
                    current_value: 0,
                    total_gain_loss: 0,
                    allocation: [] as { label: string; value: number }[],
                    performance_history: [] as {
                        name: string;
                        value: number;
                    }[],
                    contribution_history: [] as {
                        name: string;
                        value: number;
                    }[],
                    top_holdings: [] as {
                        ticker: string;
                        name?: string;
                        value: number;
                        percent: number;
                    }[],
                },
            );

            const allocationMap = new Map<string, number>();
            for (const item of analyticsData.allocation) {
                allocationMap.set(
                    item.label,
                    (allocationMap.get(item.label) || 0) +
                        Number(item.value || 0),
                );
            }
            const allocation = Array.from(allocationMap.entries()).map(
                ([label, value]) => ({ label, value }),
            );

            const performanceMap = new Map<string, number>();
            for (const point of analyticsData.performance_history) {
                performanceMap.set(
                    point.name,
                    (performanceMap.get(point.name) || 0) +
                        Number(point.value || 0),
                );
            }
            const performance_history = Array.from(performanceMap.entries())
                .map(([name, value]) => ({ name, value }))
                .sort(
                    (a, b) =>
                        getTimeFromLabel(a.name) - getTimeFromLabel(b.name),
                );

            const contributionMap = new Map<string, number>();
            for (const point of analyticsData.contribution_history) {
                contributionMap.set(
                    point.name,
                    (contributionMap.get(point.name) || 0) +
                        Number(point.value || 0),
                );
            }
            const contribution_history = Array.from(contributionMap.entries())
                .map(([name, value]) => ({ name, value }))
                .sort(
                    (a, b) =>
                        getTimeFromLabel(a.name) - getTimeFromLabel(b.name),
                );

            const topHoldingsByWeightMap = new Map<
                string,
                { value: number; name: string }
            >();
            for (const item of analyticsData.top_holdings) {
                const prev = topHoldingsByWeightMap.get(item.ticker);
                topHoldingsByWeightMap.set(item.ticker, {
                    value: (prev?.value || 0) + Number(item.value || 0),
                    name: item.name || prev?.name || item.ticker,
                });
            }
            const totalValue = analyticsData.current_value || 0;
            const topHoldingsByWeight = Array.from(
                topHoldingsByWeightMap.entries(),
            )
                .map(([ticker, { value, name }]) => ({
                    ticker,
                    name,
                    value,
                    percent: totalValue > 0 ? (value / totalValue) * 100 : 0,
                }))
                .sort((a, b) => b.percent - a.percent)
                .slice(0, 10);

            const costBasis = analyticsData.total_invested;
            const gainLoss = analyticsData.total_gain_loss;
            const currentValue = analyticsData.current_value;

            stats = {
                id: "aggregated",
                current_value: currentValue,
                cost_basis: costBasis,
                gain_loss: gainLoss,
                return_percent:
                    costBasis > 0 ? (gainLoss / costBasis) * 100 : 0,
                allocation,
                performance_history,
                contribution_history,
                top_holdings: topHoldingsByWeight,
            };

            await loadPerformanceData(topHoldingsByWeight, force);
        } catch (e) {
            console.error("Failed to load dashboard data:", e);
        } finally {
            loading = false;
        }
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
        if (!holdings.length) return;
        performanceLoading = true;
        try {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 30);
            const startStr = start.toISOString().slice(0, 10);
            const endStr = end.toISOString().slice(0, 10);

            const holdingByTicker = Object.fromEntries(
                holdings.map((h) => [h.ticker, h]),
            );

            const tickers = holdings.map((h) => h.ticker);
            const batchKey = buildBatchPriceHistoryKey(
                tickers,
                startStr,
                endStr,
            );
            let batch = force
                ? null
                : await getCachedBatchPriceHistory(batchKey);
            if (!batch) {
                try {
                    batch = await assetController.getBatchPriceHistory({
                        tickers,
                        start_date: startStr,
                        end_date: endStr,
                    });
                    await setCachedBatchPriceHistory(batchKey, batch);
                } catch (apiError) {
                    if (force) {
                        batch = await getCachedBatchPriceHistory(batchKey);
                    }
                    if (!batch) throw apiError;
                }
            }

            const results: PerformanceHolding[] = batch.results.map(
                (history) => {
                    const h = holdingByTicker[history.ticker];
                    const prices = (history.data || [])
                        .map((d) => Number(d.close))
                        .filter((p) => p > 0 && Number.isFinite(p));

                    if (prices.length < 2) {
                        const fallback = prices[prices.length - 1] || null;
                        return {
                            ticker: history.ticker,
                            name: h?.name ?? history.ticker,
                            value: h?.value ?? 0,
                            percent: h?.percent ?? 0,
                            currentPrice: fallback,
                            dayChange: null,
                            weekAvg: fallback,
                            monthAvg: fallback,
                            monthChange: null,
                        };
                    }

                    const currentPrice = prices[prices.length - 1];
                    const prevPrice = prices[prices.length - 2];
                    const dayChange =
                        prevPrice > 0
                            ? ((currentPrice - prevPrice) / prevPrice) * 100
                            : 0;

                    const weekPrices = prices.slice(-7);
                    const weekAvg =
                        weekPrices.reduce((a, b) => a + b, 0) /
                        weekPrices.length;

                    const monthAvg =
                        prices.reduce((a, b) => a + b, 0) / prices.length;

                    const oldestPrice = prices[0];
                    const monthChange =
                        oldestPrice > 0
                            ? ((currentPrice - oldestPrice) / oldestPrice) * 100
                            : 0;

                    return {
                        ticker: history.ticker,
                        name: h?.name ?? history.ticker,
                        value: h?.value ?? 0,
                        percent: h?.percent ?? 0,
                        currentPrice,
                        dayChange,
                        weekAvg,
                        monthAvg,
                        monthChange,
                    };
                },
            );

            performanceHoldings = results;
        } finally {
            performanceLoading = false;
        }
    }

    $: isPositive = Number(stats.gain_loss) >= 0;

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
        <div class="animate-in space-y-1">
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
            <Card>
                <div class="space-y-3">
                    <div class="flex gap-4 border-b border-border pb-2">
                        {#each Array(6) as _}
                            <Skeleton className="h-4 flex-1" />
                        {/each}
                    </div>
                    {#each Array(10) as _}
                        <div class="flex gap-4">
                            {#each Array(6) as _}
                                <Skeleton className="h-4 flex-1" />
                            {/each}
                        </div>
                    {/each}
                </div>
            </Card>
        {:else}
            <!-- Stat Cards -->
            <div
                class="animate-in animate-in-delay-1 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
            >
                <!-- Total Value -->
                <div
                    class="rounded-xl border border-border bg-card p-4 md:p-5 shadow-sm transition-shadow hover:shadow-md"
                >
                    <p
                        class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2"
                    >
                        Total Value
                    </p>
                    <div
                        class="font-serif text-2xl sm:text-3xl md:text-4xl text-foreground leading-none break-all"
                    >
                        <Amount
                            value={formatCurrency(stats.current_value, "USD")}
                        />
                    </div>
                    <p class="mt-2 text-xs text-muted-foreground">
                        Current portfolio value
                    </p>
                </div>

                <!-- Cost Basis -->
                <div
                    class="rounded-xl border border-border bg-card p-4 md:p-5 shadow-sm transition-shadow hover:shadow-md"
                >
                    <p
                        class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2"
                    >
                        Cost Basis
                    </p>
                    <div
                        class="font-serif text-2xl sm:text-3xl md:text-4xl text-foreground leading-none break-all"
                    >
                        <Amount
                            value={formatCurrency(stats.cost_basis, "USD")}
                        />
                    </div>
                    <p class="mt-2 text-xs text-muted-foreground">
                        Total amount invested
                    </p>
                </div>

                <!-- Gain / Loss -->
                <div
                    class="rounded-xl border shadow-sm transition-shadow hover:shadow-md p-4 md:p-5
                    {isPositive
                        ? 'border-[#34D399]/20 bg-[#34D399]/5'
                        : 'border-[#F87171]/20 bg-[#F87171]/5'}"
                >
                    <p
                        class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2"
                    >
                        Gain / Loss
                    </p>
                    <div
                        class="font-serif text-2xl sm:text-3xl md:text-4xl leading-none break-all"
                        class:text-positive={isPositive}
                        class:text-negative={!isPositive}
                    >
                        <Amount
                            value={formatCurrency(stats.gain_loss, "USD")}
                        />
                    </div>
                    <p class="mt-2 text-xs text-muted-foreground">
                        Unrealized P&L
                    </p>
                </div>

                <!-- Return -->
                <div
                    class="rounded-xl border shadow-sm transition-shadow hover:shadow-md p-4 md:p-5
                    {isPositive
                        ? 'border-[#34D399]/20 bg-[#34D399]/5'
                        : 'border-[#F87171]/20 bg-[#F87171]/5'}"
                >
                    <p
                        class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2"
                    >
                        Total Return
                    </p>
                    <div
                        class="font-serif text-2xl sm:text-3xl md:text-4xl leading-none"
                        class:text-positive={isPositive}
                        class:text-negative={!isPositive}
                    >
                        <Amount value={formatPercent(stats.return_percent)} />
                    </div>
                    <p class="mt-2 text-xs text-muted-foreground">
                        Return on investment
                    </p>
                </div>
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
                        currency="USD"
                    />
                </Card>
            </div>

            <!-- Contribution History Chart -->
            <div class="animate-in animate-in-delay-2">
                <Card
                    title="Contribution History"
                    subtitle="Net contributions over time"
                    className="md:px-4"
                >
                    <LineChart
                        data={stats.contribution_history}
                        title=""
                        height="h-72 md:h-96"
                        currency="USD"
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
                    subtitle="10 largest positions by weight"
                >
                    <DonutChart data={topHoldingsChart} title="" />
                </Card>
            </div>

            <!-- Top Holdings Performance -->
            <div class="animate-in animate-in-delay-4">
                <Card
                    title="Top Holdings Performance"
                    subtitle="10 largest positions — current value, price, averages & change"
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
                    {:else if performanceHoldings.length > 0}
                        <div class="overflow-x-auto -mx-4 md:mx-0">
                            <table class="w-full text-sm">
                                <thead class="border-b border-border">
                                    <tr>
                                        <th
                                            class="h-9 px-3 text-left align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            Ticker
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            Price
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            Value
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            Day
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            7D Avg
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            30D Avg
                                        </th>
                                        <th
                                            class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                                        >
                                            30D Chg
                                        </th>
                                    </tr>
                                </thead>
                                <tbody class="[&_tr:last-child]:border-0">
                                    {#each performanceHoldings as h}
                                        <tr
                                            class="relative border-b border-border/60 hover:bg-muted/30 transition-colors"
                                        >
                                            <td class="px-3 py-3 align-middle">
                                                <div
                                                    class="flex items-center gap-2"
                                                >
                                                    <span
                                                        class="inline-block h-1 w-1 rounded-full flex-shrink-0
                                                        {h.monthChange != null
                                                            ? h.monthChange >= 0
                                                                ? 'bg-[#34D399]'
                                                                : 'bg-[#F87171]'
                                                            : 'bg-muted-foreground'}"
                                                    >
                                                    </span>
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
                                                    <span
                                                        class="text-muted-foreground"
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
                                                            "USD",
                                                        )}
                                                    />
                                                {:else}
                                                    <span
                                                        class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right font-mono text-xs"
                                            >
                                                {#if h.dayChange != null}
                                                    <span
                                                        class:text-positive={h.dayChange >=
                                                            0}
                                                        class:text-negative={h.dayChange <
                                                            0}
                                                    >
                                                        <Amount
                                                            value={formatPercent(
                                                                h.dayChange,
                                                            )}
                                                        />
                                                    </span>
                                                {:else}
                                                    <span
                                                        class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right font-mono text-xs"
                                            >
                                                {#if h.weekAvg != null}
                                                    <Amount
                                                        value={formatCurrency(
                                                            h.weekAvg,
                                                            "USD",
                                                        )}
                                                    />
                                                {:else}
                                                    <span
                                                        class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right font-mono text-xs"
                                            >
                                                {#if h.monthAvg != null}
                                                    <Amount
                                                        value={formatCurrency(
                                                            h.monthAvg,
                                                            "USD",
                                                        )}
                                                    />
                                                {:else}
                                                    <span
                                                        class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                            <td
                                                class="px-3 py-3 align-middle text-right"
                                            >
                                                {#if h.monthChange != null}
                                                    <span
                                                        class="font-semibold font-mono text-xs"
                                                        class:text-positive={h.monthChange >=
                                                            0}
                                                        class:text-negative={h.monthChange <
                                                            0}
                                                    >
                                                        <Amount
                                                            value={formatPercent(
                                                                h.monthChange,
                                                            )}
                                                        />
                                                    </span>
                                                {:else}
                                                    <span
                                                        class="text-muted-foreground"
                                                        >—</span
                                                    >
                                                {/if}
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {:else}
                        <p
                            class="text-sm text-muted-foreground py-8 text-center"
                        >
                            No holdings data available.
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
        <a
            href="/trades?new=true"
            class="h-10 w-10 rounded-full bg-card border border-border text-foreground flex items-center justify-center hover:bg-muted transition-all shadow-lg"
            title="New Trade"
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
