<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import Skeleton from "$lib/components/Skeleton.svelte";
    import HoldingsTable from "$lib/components/HoldingsTable.svelte";
    import Button from "$lib/components/Button.svelte";
    import Input from "$lib/components/Input.svelte";
    import Modal from "$lib/components/Modal.svelte";
    import TradeForm from "$lib/components/TradeForm.svelte";
    import { currentPortfolio, portfolios } from "$lib/stores";
    import { api } from "$lib/api/client";
    import { PortfolioController, TradeController } from "$lib/api/controllers";
    import type { CreateTradeRequest, Holding } from "$lib/api/types";
    import { onMount } from "svelte";

    let loading = true;
    let holdings: Holding[] = [];
    let searchTerm = "";
    let filteredHoldings: Holding[] = [];
    let portfolioController: PortfolioController;
    let tradeController: TradeController;
    let showNewModal = false;
    let tradeFormLoading = false;

    let lastLoadKey = "";
    let loadInProgress = false;

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        tradeController = new TradeController(api.getInstance());
        // Load portfolios if not already loaded
        if ($portfolios.length === 0) {
            try {
                const data = await portfolioController.listPortfolios();
                portfolios.set(data || []);
            } catch (e) {
                console.error("Failed to load portfolios:", e);
            }
        }
    });

    $: loadKey = portfolioController
        ? `${$currentPortfolio?.id || "all"}:${$portfolios.map((p) => p.id).join(",")}`
        : "";

    $: if (loadKey && loadKey !== lastLoadKey) {
        lastLoadKey = loadKey;
        void loadHoldings();
    }

    async function loadHoldings() {
        if (loadInProgress) return;
        loadInProgress = true;
        try {
            loading = true;
            let allHoldings: any[] = [];

            if (!$currentPortfolio?.id) {
                // Load holdings from all portfolios
                for (const p of $portfolios) {
                    try {
                        const response = await portfolioController.getHoldings({
                            portfolio_id: p.id,
                        });
                        const holdingsData = (response.data || []).map(
                            (h: any) => ({
                                ticker: h.ticker,
                                name: h.name || h.ticker,
                                quantity: h.quantity,
                                average_cost: h.avg_price,
                                current_price: h.current_price,
                                current_value: h.total_value,
                                total_invested: h.total_invested,
                                gain_loss: h.gain_loss,
                                return_pct: h.gain_loss_percent,
                                currency: response.currency ?? "USD",
                            }),
                        );
                        allHoldings = [...allHoldings, ...holdingsData];
                    } catch (e) {
                        console.error(
                            `Failed to load holdings for portfolio ${p.id}:`,
                            e,
                        );
                    }
                }
            } else {
                // Load holdings for current portfolio
                const response = await portfolioController.getHoldings({
                    portfolio_id: $currentPortfolio.id,
                });
                allHoldings = (response.data || []).map((h: any) => ({
                    ticker: h.ticker,
                    name: h.name || h.ticker,
                    quantity: h.quantity,
                    average_cost: h.avg_price,
                    current_price: h.current_price,
                    current_value: h.total_value,
                    total_invested: h.total_invested,
                    gain_loss: h.gain_loss,
                    return_pct: h.gain_loss_percent,
                    currency: response.currency ?? "USD",
                }));
            }

            // Group and aggregate by ticker if in aggregated view
            if (!$currentPortfolio?.id && allHoldings.length > 0) {
                const holdingsByTicker: Record<string, any> = {};
                for (const holding of allHoldings) {
                    const ticker = holding.ticker;
                    if (!holdingsByTicker[ticker]) {
                        holdingsByTicker[ticker] = {
                            ticker,
                            name: holding.name,
                            quantity: 0,
                            average_cost: 0,
                            current_price: holding.current_price,
                            current_value: 0,
                            total_invested: 0,
                            gain_loss: 0,
                            return_pct: 0,
                            currency: holding.currency,
                        };
                    }
                    holdingsByTicker[ticker].quantity += parseFloat(
                        holding.quantity,
                    );
                    holdingsByTicker[ticker].current_value += parseFloat(
                        holding.current_value,
                    );
                    holdingsByTicker[ticker].total_invested += parseFloat(
                        holding.total_invested || 0,
                    );
                    holdingsByTicker[ticker].gain_loss += parseFloat(
                        holding.gain_loss,
                    );
                }
                holdings = Object.values(holdingsByTicker);
            } else {
                holdings = allHoldings;
            }

            filterHoldings();
        } catch (e) {
            console.error("Failed to load holdings:", e);
        } finally {
            loading = false;
            loadInProgress = false;
        }
    }

    function filterHoldings() {
        if (!searchTerm) {
            filteredHoldings = holdings;
        } else {
            const term = searchTerm.toLowerCase();
            filteredHoldings = holdings.filter(
                (h) =>
                    h.ticker.toLowerCase().includes(term) ||
                    (h.name && h.name.toLowerCase().includes(term)),
            );
        }
    }

    async function handleCreateTrade(trade: any) {
        tradeFormLoading = true;
        try {
            const tradeRequest: CreateTradeRequest = {
                portfolio_id: $currentPortfolio.id,
                ticker: trade.ticker,
                trade_type: trade.trade_type,
                trade_date: trade.trade_date,
                quantity: parseFloat(trade.quantity),
                price: parseFloat(trade.price),
                trade_currency: trade.trade_currency,
                fees: parseFloat(trade.fees) || 0,
                asset_class: trade.asset_class || undefined,
                market_data_provider: trade.market_data_provider || "yfinance",
            };
            await tradeController.createTrade(tradeRequest);
            await loadHoldings();
            showNewModal = false;
        } catch (e) {
            console.error("Failed to create trade:", e);
        } finally {
            tradeFormLoading = false;
        }
    }

    async function handleDeleteHolding(ticker: string) {
        if (!confirm(`Delete all trades for ${ticker}? This cannot be undone.`))
            return;
        try {
            const portfolioId = $currentPortfolio?.id;
            if (!portfolioId) {
                console.error("Cannot delete holdings from aggregated view");
                return;
            }
            const response = await tradeController.listTrades({
                portfolio_id: portfolioId,
                ticker,
                limit: 1000,
            });
            const tradesForTicker = (response.data as any[]) || [];
            await Promise.all(
                tradesForTicker.map((t: any) =>
                    tradeController.deleteTrade(t.id),
                ),
            );
            await loadHoldings();
        } catch (e) {
            console.error("Failed to delete holding:", e);
        }
    }

    $: searchTerm, filterHoldings();
</script>

<svelte:head>
    <title>Holdings — Folio</title>
</svelte:head>

<div class="min-h-screen bg-background p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center"
        >
            <div class="space-y-2">
                <h1 class="text-2xl md:text-3xl font-bold text-foreground">
                    Holdings
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    {#if $currentPortfolio?.id}
                        Current positions in {$currentPortfolio?.name}
                    {:else}
                        All holdings (Aggregated)
                    {/if}
                </p>
            </div>
            <Button
                variant="default"
                on:click={() => (showNewModal = true)}
                class="w-full sm:w-auto {!$currentPortfolio?.id
                    ? 'opacity-50 cursor-not-allowed'
                    : ''}"
                disabled={!$currentPortfolio?.id}
            >
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
                        d="M12 4v16m8-8H4"
                    />
                </svg>
                Add Trade
            </Button>
        </div>

        <!-- Search -->
        <Card>
            <Input
                label="Search holdings"
                placeholder="Search by ticker or name (e.g., AAPL or Apple)"
                bind:value={searchTerm}
            />
        </Card>

        <!-- Holdings Table -->
        {#if loading}
            <Card><Skeleton className="h-10 w-full" /></Card>
            <Card>
                <div class="space-y-3">
                    <div class="flex gap-4 border-b border-border pb-3">
                        {#each Array(5) as _}
                            <Skeleton className="h-4 flex-1" />
                        {/each}
                    </div>
                    {#each Array(6) as _}
                        <div class="flex gap-4">
                            {#each Array(5) as _}
                                <Skeleton className="h-4 flex-1" />
                            {/each}
                        </div>
                    {/each}
                </div>
            </Card>
        {:else if filteredHoldings.length === 0}
            <Card
                title="No holdings"
                subtitle="Create a trade to add holdings to your portfolio"
            >
                <div class="py-8 text-center">
                    <p class="mb-4 text-muted-foreground">
                        You don't have any positions yet.
                    </p>
                    <Button
                        variant="default"
                        on:click={() => (showNewModal = true)}
                    >
                        Create First Trade
                    </Button>
                </div>
            </Card>
        {:else}
            <Card title="Portfolio Holdings">
                <div class="overflow-x-auto -mx-4 md:mx-0">
                    <HoldingsTable
                        holdings={filteredHoldings}
                        on:deleteHolding={(e) => handleDeleteHolding(e.detail)}
                    />
                </div>
            </Card>
        {/if}
    </div>
</div>

<!-- Add Trade Modal -->
<Modal
    open={showNewModal}
    title="Add Trade"
    onClose={() => (showNewModal = false)}
>
    <TradeForm
        isLoading={tradeFormLoading}
        on:submit={(e) => handleCreateTrade(e.detail)}
        trade={{
            ticker: "",
            trade_type: "buy",
            trade_date: new Date().toISOString().slice(0, 16),
            quantity: "",
            price: "",
            trade_currency: "USD",
            fees: "0",
            market_data_provider: "yfinance",
        }}
    />
    <svelte:fragment slot="footer">
        <Button variant="outline" on:click={() => (showNewModal = false)}>
            Cancel
        </Button>
    </svelte:fragment>
</Modal>
