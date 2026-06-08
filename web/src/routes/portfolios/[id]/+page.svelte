<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import Skeleton from "$lib/components/Skeleton.svelte";
    import Button from "$lib/components/Button.svelte";
    import HoldingsTable from "$lib/components/HoldingsTable.svelte";
    import Amount from "$lib/components/Amount.svelte";
    import { api } from "$lib/api/client";
    import { PortfolioController } from "$lib/api/controllers";
    import { currentPortfolio, baseCurrency } from "$lib/stores";
    import { page } from "$app/stores";
    import { onMount } from "svelte";
    import { formatCurrency, formatPercent } from "$lib/utils/format";

    let loading = true;
    let portfolio: any = null;
    let holdings: any[] = [];
    let analytics: any = null;
    let portfolioController: PortfolioController;

    const portfolioId = $page.params.id;

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        await loadData();
    });

    async function loadData() {
        try {
            loading = true;
            const [portfolioData, holdingsData, analyticsData] =
                await Promise.all([
                    portfolioController.getPortfolio(portfolioId),
                    portfolioController
                        .getHoldings({ portfolio_id: portfolioId })
                        .catch(() => ({
                            data: [],
                            currency: "",
                            total_value: 0,
                        })),
                    portfolioController
                        .getPortfolioAnalytics({
                            portfolio_id: portfolioId,
                            timeframe: "1y",
                        })
                        .catch(() => null),
                ]);

            portfolio = portfolioData;
            currentPortfolio.set(portfolioData);
            holdings = (holdingsData.data || []).map((h: any) => ({
                ...h,
                average_cost: h.avg_price,
                current_value: h.total_value,
                return_pct: h.gain_loss_percent,
                currency: holdingsData.currency,
            }));
            analytics = analyticsData;
        } catch (e) {
            console.error("Failed to load portfolio:", e);
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title
        >{portfolio ? `${portfolio.name} — Folio` : "Portfolio — Folio"}</title
    >
</svelte:head>

<div class="min-h-screen p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
            <div class="flex items-center gap-4">
                <Button variant="ghost" size="sm" href="/portfolios">
                    <svg
                        class="mr-2 h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 19l-7-7 7-7"
                        />
                    </svg>
                    Portfolios
                </Button>
                {#if portfolio}
                    <div>
                        <h1
                            class="font-serif text-3xl md:text-4xl text-foreground"
                        >
                            {portfolio.name}
                        </h1>
                        <p class="text-xs md:text-sm text-muted-foreground">
                            {portfolio.base_currency}
                        </p>
                    </div>
                {/if}
            </div>
            {#if portfolio}
                <Button
                    variant="outline"
                    size="sm"
                    href="/trades?portfolio_id={portfolioId}"
                >
                    Add Trade
                </Button>
            {/if}
        </div>

        {#if loading}
            <div class="flex items-center gap-4 mb-6">
                <Skeleton className="h-8 w-24 rounded-md" />
                <div class="space-y-2">
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-4 w-24" />
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {#each Array(4) as _}
                    <Card>
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-6 w-32 mt-2" />
                    </Card>
                {/each}
            </div>
            <Card>
                <div class="space-y-3">
                    <div class="flex gap-4 border-b border-border pb-3">
                        {#each Array(4) as _}
                            <Skeleton className="h-4 flex-1" />
                        {/each}
                    </div>
                    {#each Array(4) as _}
                        <div class="flex gap-4">
                            {#each Array(4) as _}
                                <Skeleton className="h-4 flex-1" />
                            {/each}
                        </div>
                    {/each}
                </div>
            </Card>
        {:else if !portfolio}
            <Card
                title="Portfolio not found"
                subtitle="This portfolio does not exist or could not be loaded."
            >
                <div class="text-center py-8">
                    <Button variant="default" href="/portfolios"
                        >Back to Portfolios</Button
                    >
                </div>
            </Card>
        {:else}
            <!-- Stats -->
            {#if analytics}
                <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <Card title="Current Value">
                        <p class="text-xl font-bold text-foreground">
                            <Amount
                                value={formatCurrency(
                                    analytics.current_value,
                                    $baseCurrency,
                                )}
                            />
                        </p>
                    </Card>
                    <Card title="Total Gain/Loss">
                        <p
                            class="text-xl font-bold"
                            class:text-positive={analytics.total_gain_loss >= 0}
                            class:text-negative={analytics.total_gain_loss < 0}
                        >
                            <Amount
                                value={formatCurrency(
                                    analytics.total_gain_loss,
                                    $baseCurrency,
                                )}
                            />
                        </p>
                    </Card>
                    <Card title="TWR">
                        <p
                            class="text-xl font-bold"
                            class:text-positive={parseFloat(analytics.twr) >= 0}
                            class:text-negative={parseFloat(analytics.twr) < 0}
                        >
                            {analytics.twr}%
                        </p>
                    </Card>
                    <Card title="MWR">
                        <p
                            class="text-xl font-bold"
                            class:text-positive={parseFloat(analytics.mwr) >= 0}
                            class:text-negative={parseFloat(analytics.mwr) < 0}
                        >
                            {analytics.mwr}%
                        </p>
                    </Card>
                </div>
            {/if}

            {#if portfolio.description}
                <Card title="Description">
                    <p class="text-sm text-muted-foreground">
                        {portfolio.description}
                    </p>
                </Card>
            {/if}

            <!-- Holdings -->
            <Card
                title="Holdings"
                subtitle="Current positions in this portfolio"
            >
                <HoldingsTable {holdings} />
            </Card>
        {/if}
    </div>
</div>
