<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import LineChart from "$lib/components/LineChart.svelte";
    import BarChart from "$lib/components/BarChart.svelte";
    import DonutChart from "$lib/components/DonutChart.svelte";
    import Select from "$lib/components/Select.svelte";
    import Badge from "$lib/components/Badge.svelte";
    import { currentPortfolio, portfolios } from "$lib/stores";
    import { api } from "$lib/api/client";
    import { PortfolioController } from "$lib/api/controllers";
    import { formatPercent, formatCurrency } from "$lib/utils/format";
    import { onMount } from "svelte";

    let loading = true;
    let timeframe = "1y";
    let portfolioController: PortfolioController;
    let analyticsData: any = {
        twr: "0",
        mwr: "0",
        allocation: [],
        performance_history: [],
        contribution_history: [],
        sector_breakdown: [],
    };

    const timeframeOptions = [
        { label: "YTD", value: "ytd" },
        { label: "3 Months", value: "3m" },
        { label: "1 Year", value: "1y" },
        { label: "3 Years", value: "3y" },
        { label: "5 Years", value: "5y" },
        { label: "All Time", value: "all" },
    ];

    let lastLoadKey = "";
    let loadInProgress = false;

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

    async function loadAnalytics() {
        if (!$currentPortfolio?.id && $portfolios.length === 0) return;
        if (loadInProgress) return;
        loadInProgress = true;
        try {
            loading = true;

            if (!$currentPortfolio?.id) {
                // Load aggregated analytics from all portfolios
                let totalTwr = 0;
                let totalMwr = 0;
                let portfolioCount = 0;
                const allocationByAssetClass: Record<string, number> = {};
                const performanceByMonth: Record<string, number> = {};
                const contributionByMonth: Record<string, number> = {};
                const sectorByName: Record<string, number> = {};

                for (const p of $portfolios) {
                    try {
                        const response =
                            await portfolioController.getPortfolioAnalytics({
                                portfolio_id: p.id,
                                timeframe,
                            });

                        totalTwr += parseFloat(response.twr || "0");
                        totalMwr += parseFloat(response.mwr || "0");
                        portfolioCount++;

                        // Aggregate allocation
                        if (response.allocation) {
                            for (const item of response.allocation) {
                                const label = item.label;
                                allocationByAssetClass[label] =
                                    (allocationByAssetClass[label] || 0) +
                                    Number(item.value);
                            }
                        }

                        // Aggregate performance history
                        if (response.performance_history) {
                            for (const item of response.performance_history) {
                                const name = item.name;
                                performanceByMonth[name] =
                                    (performanceByMonth[name] || 0) +
                                    Number(item.value);
                            }
                        }

                        // Aggregate contribution history
                        if (response.contribution_history) {
                            for (const item of response.contribution_history) {
                                const name = item.name;
                                contributionByMonth[name] =
                                    (contributionByMonth[name] || 0) +
                                    Number(item.value);
                            }
                        }

                        // Aggregate sector breakdown
                        if (response.sector_breakdown) {
                            for (const item of response.sector_breakdown) {
                                const label = item.label;
                                sectorByName[label] =
                                    (sectorByName[label] || 0) +
                                    Number(item.value);
                            }
                        }
                    } catch (e) {
                        console.error(
                            `Failed to load analytics for portfolio ${p.id}:`,
                            e,
                        );
                    }
                }

                // Convert allocation to array format
                const allocationArray = Object.entries(
                    allocationByAssetClass,
                ).map(([label, value]) => ({
                    label,
                    value,
                }));

                // Convert performance history to sorted array format
                const performanceArray = Object.entries(performanceByMonth)
                    .map(([name, value]) => ({ name, value }))
                    .sort((a, b) => {
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
                        const getMonthNum = (nameStr: string) => {
                            const parts = nameStr.split(" ");
                            return (
                                (parseInt(parts[1]) - 2024) * 12 +
                                monthOrder.indexOf(parts[0])
                            );
                        };
                        return getMonthNum(a.name) - getMonthNum(b.name);
                    });

                // Convert contribution history to array format
                const contributionArray = Object.entries(contributionByMonth)
                    .map(([name, value]) => ({ name, value }))
                    .sort((a, b) => {
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
                        const getMonthNum = (nameStr: string) => {
                            const parts = nameStr.split(" ");
                            return (
                                (parseInt(parts[1]) - 2024) * 12 +
                                monthOrder.indexOf(parts[0])
                            );
                        };
                        return getMonthNum(a.name) - getMonthNum(b.name);
                    });

                // Convert sector breakdown to array format
                const sectorArray = Object.entries(sectorByName).map(
                    ([label, value]) => ({
                        label,
                        value,
                    }),
                );

                analyticsData = {
                    twr:
                        portfolioCount > 0
                            ? (totalTwr / portfolioCount).toString()
                            : "0",
                    mwr:
                        portfolioCount > 0
                            ? (totalMwr / portfolioCount).toString()
                            : "0",
                    allocation: allocationArray,
                    performance_history: performanceArray,
                    contribution_history: contributionArray,
                    sector_breakdown: sectorArray,
                };
            } else {
                // Load single portfolio analytics
                const response =
                    await portfolioController.getPortfolioAnalytics({
                        portfolio_id: $currentPortfolio.id,
                        timeframe,
                    });
                analyticsData = {
                    ...response,
                };
            }
        } catch (e) {
            console.error("Failed to load analytics:", e);
        } finally {
            loading = false;
            loadInProgress = false;
        }
    }

    $: loadKey =
        portfolioController &&
        timeframe &&
        ($currentPortfolio?.id || $portfolios.length > 0)
            ? `${$currentPortfolio?.id || "all"}:${timeframe}:${$portfolios.map((p) => p.id).join(",")}`
            : "";

    $: if (loadKey && loadKey !== lastLoadKey) {
        lastLoadKey = loadKey;
        void loadAnalytics();
    }

    $: contribChart = (analyticsData.contribution_history || []).map(
        (d: any) => ({
            label: d.name,
            value: d.value,
        }),
    );
</script>

<svelte:head>
    <title>Analytics — Folio</title>
</svelte:head>

<div class="min-h-screen bg-background p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 sm:gap-6 sm:items-center sm:justify-between"
        >
            <div class="space-y-2">
                <h1 class="text-2xl md:text-3xl font-bold text-foreground">
                    Analytics
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    {#if $currentPortfolio?.id}
                        Performance analysis for {$currentPortfolio?.name}
                    {:else}
                        Performance analysis (Aggregated)
                    {/if}
                </p>
            </div>
        </div>

        <!-- Timeframe Filter -->
        <Card>
            <Select
                label="Timeframe"
                bind:value={timeframe}
                options={timeframeOptions}
            />
        </Card>

        {#if loading}
            <div class="flex justify-center py-12">
                <div class="text-muted-foreground">Loading analytics...</div>
            </div>
        {:else}
            <!-- Metrics Cards -->
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <Card
                    title="Time-Weighted Return (TWR)"
                    subtitle="Adjusted for cash flows"
                >
                    <div class="flex items-baseline gap-2">
                        <div
                            class="text-4xl font-bold"
                            class:text-positive={parseFloat(
                                analyticsData.twr,
                            ) >= 0}
                            class:text-negative={parseFloat(analyticsData.twr) <
                                0}
                        >
                            {formatPercent(analyticsData.twr)}
                        </div>
                        <Badge variant="default">Standard Measure</Badge>
                    </div>
                </Card>

                <Card
                    title="Money-Weighted Return (MWR)"
                    subtitle="Including cash flow timing"
                >
                    <div class="flex items-baseline gap-2">
                        <div
                            class="text-4xl font-bold"
                            class:text-positive={parseFloat(
                                analyticsData.mwr,
                            ) >= 0}
                            class:text-negative={parseFloat(analyticsData.mwr) <
                                0}
                        >
                            {formatPercent(analyticsData.mwr)}
                        </div>
                        <Badge variant="secondary">IRR Method</Badge>
                    </div>
                </Card>
            </div>

            <!-- Performance History -->
            <Card title="Performance History">
                <LineChart
                    data={analyticsData.performance_history}
                    title=""
                    height="h-72 md:h-96"
                />
            </Card>

            <!-- Contributions Over Time -->
            <Card title="Contributions Over Time">
                <BarChart data={contribChart} title="" height="h-72 md:h-96" />
            </Card>

            <!-- Asset Allocation and Sector Breakdown -->
            <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
                <Card title="Asset Allocation">
                    <DonutChart data={analyticsData.allocation} title="" />
                </Card>

                <Card title="Sector Breakdown">
                    <DonutChart
                        data={analyticsData.sector_breakdown}
                        title=""
                    />
                </Card>
            </div>
        {/if}
    </div>
</div>
