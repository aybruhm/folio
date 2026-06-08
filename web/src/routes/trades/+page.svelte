<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import Skeleton from "$lib/components/Skeleton.svelte";
    import TradeTable from "$lib/components/TradeTable.svelte";
    import Button from "$lib/components/Button.svelte";
    import Modal from "$lib/components/Modal.svelte";
    import TradeForm from "$lib/components/TradeForm.svelte";
    import Select from "$lib/components/Select.svelte";
    import SearchPagination from "$lib/components/SearchPagination.svelte";
    import { currentPortfolio, portfolios } from "$lib/stores";
    import { api } from "$lib/api/client";
    import { TradeController, PortfolioController } from "$lib/api/controllers";
    import type { CreateTradeRequest, Trade } from "$lib/api/types";
    import { onMount } from "svelte";
    import { page } from "$app/stores";

    let loading = true;
    let trades: Trade[] = [];
    let showNewModal = false;
    let showEditModal = false;
    let showBulkDeleteModal = false;
    let editingTrade: any = null;
    let tradeTypeFilter = "all";
    let searchTerm = "";
    let currentPage = 1;
    let pageSize = 25;
    let totalTrades = 0;
    let serverTotalTrades = 0;
    let tradeController: TradeController;
    let portfolioController: PortfolioController;
    let selectedTradeIds = new Set<string>();

    const tradeTypeOptions = [
        { label: "All Types", value: "all" },
        { label: "Buy", value: "buy" },
        { label: "Sell", value: "sell" },
        { label: "Dividend", value: "dividend" },
        { label: "Fee", value: "fee" },
    ];

    let lastLoadKey = "";
    let loadInProgress = false;
    let lastSearchTerm = "";
    let lastTradeTypeFilter = tradeTypeFilter;
    let lastPageSize = pageSize;
    let lastPage = currentPage;
    let lastPortfolioKey = "";

    onMount(async () => {
        tradeController = new TradeController(api.getInstance());
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
        if ($page.url.searchParams.get("new") === "true") showNewModal = true;
    });

    $: isAggregated = !$currentPortfolio?.id;

    $: if (
        searchTerm !== lastSearchTerm ||
        tradeTypeFilter !== lastTradeTypeFilter
    ) {
        lastSearchTerm = searchTerm;
        lastTradeTypeFilter = tradeTypeFilter;
        currentPage = 1;
    }

    $: if (pageSize !== lastPageSize) {
        lastPageSize = pageSize;
        currentPage = 1;
    }

    $: if (currentPage !== lastPage) {
        lastPage = currentPage;
        selectedTradeIds = new Set();
    }

    $: {
        const portfolioKey = $currentPortfolio?.id || "all";
        if (portfolioKey !== lastPortfolioKey) {
            lastPortfolioKey = portfolioKey;
            currentPage = 1;
            selectedTradeIds = new Set();
        }
    }

    $: loadKey = tradeController
        ? `${$currentPortfolio?.id || "all"}:${$portfolios.map((p) => p.id).join(",")}:${tradeTypeFilter}:${searchTerm}:${currentPage}:${pageSize}`
        : "";

    $: if (loadKey && loadKey !== lastLoadKey) {
        lastLoadKey = loadKey;
        void loadTrades();
    }

    async function loadTrades() {
        if (loadInProgress) return;
        loadInProgress = true;
        try {
            loading = true;
            let allTrades: Trade[] = [];

            if (isAggregated) {
                // Load trades from all portfolios
                for (const p of $portfolios) {
                    try {
                        const response = await tradeController.listTrades({
                            portfolio_id: p.id,
                            limit: 500,
                            skip: 0,
                            ticker: searchTerm ? searchTerm : undefined,
                            trade_type:
                                tradeTypeFilter === "all"
                                    ? undefined
                                    : tradeTypeFilter,
                        });
                        allTrades = [
                            ...allTrades,
                            ...((response.data as Trade[]) || []),
                        ];
                    } catch (e) {
                        console.error(
                            `Failed to load trades for portfolio ${p.id}:`,
                            e,
                        );
                    }
                }
                allTrades.sort((a, b) => {
                    const aTime = new Date(a.trade_date).getTime();
                    const bTime = new Date(b.trade_date).getTime();
                    return bTime - aTime;
                });
                trades = allTrades;
                serverTotalTrades = allTrades.length;
            } else {
                // Load trades for current portfolio (server-side paging)
                const response = await tradeController.listTrades({
                    portfolio_id: $currentPortfolio.id,
                    limit: pageSize,
                    skip: (currentPage - 1) * pageSize,
                    ticker: searchTerm ? searchTerm : undefined,
                    trade_type:
                        tradeTypeFilter === "all" ? undefined : tradeTypeFilter,
                });
                trades = (response.data as Trade[]) || [];
                serverTotalTrades = response.total || 0;
            }
        } catch (e) {
            console.error("Failed to load trades:", e);
        } finally {
            loading = false;
            loadInProgress = false;
        }
    }

    async function handleCreateTrade(trade: any) {
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
            await loadTrades();
            showNewModal = false;
        } catch (e) {
            console.error("Failed to create trade:", e);
        }
    }

    function handleEditTrade(row: any) {
        editingTrade = {
            id: row.id,
            ticker: row.ticker,
            trade_type: row.trade_type,
            trade_date: row.trade_date.slice(0, 16),
            quantity: String(row.quantity),
            price: String(row.price),
            trade_currency: row.trade_currency,
            fees: String(row.fees ?? 0),
            asset_class: row.asset_class || "",
            market_data_provider: row.market_data_provider,
        };
        showEditModal = true;
    }

    async function handleUpdateTrade(trade: any) {
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
            await tradeController.updateTrade(editingTrade.id, tradeRequest);
            await loadTrades();
            showEditModal = false;
            editingTrade = null;
        } catch (e) {
            console.error("Failed to update trade:", e);
        }
    }

    async function handleDeleteTrade(tradeId: string) {
        if (!confirm("Delete this trade? This cannot be undone.")) return;
        try {
            await tradeController.deleteTrade(tradeId);
            await loadTrades();
        } catch (e) {
            console.error("Failed to delete trade:", e);
        }
    }

    async function handleBulkDelete() {
        if (
            !confirm(
                `Delete ${selectedTradeIds.size} trade(s)? This cannot be undone.`,
            )
        )
            return;
        try {
            await tradeController.deleteBulkTrades(
                Array.from(selectedTradeIds),
            );
            selectedTradeIds = new Set();
            await loadTrades();
            showBulkDeleteModal = false;
        } catch (e) {
            console.error("Failed to delete trades:", e);
        }
    }

    $: filteredTrades = isAggregated
        ? trades.filter((t) => {
              const matchesType =
                  tradeTypeFilter === "all" || t.trade_type === tradeTypeFilter;
              const normalizedSearch = searchTerm.trim().toLowerCase();
              const matchesSearch =
                  !normalizedSearch ||
                  String(t.ticker).toLowerCase().includes(normalizedSearch) ||
                  (t.name &&
                      String(t.name).toLowerCase().includes(normalizedSearch));
              return matchesType && matchesSearch;
          })
        : trades;

    $: totalTrades = isAggregated ? filteredTrades.length : serverTotalTrades;

    $: pagedTrades = isAggregated
        ? filteredTrades.slice(
              (currentPage - 1) * pageSize,
              currentPage * pageSize,
          )
        : trades;
</script>

<svelte:head>
    <title>Trades — Folio</title>
</svelte:head>

<div class="min-h-screen bg-background p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center"
        >
            <div class="space-y-2">
                <h1 class="text-2xl md:text-3xl font-bold text-foreground">
                    Trades
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    {#if $currentPortfolio?.id}
                        Transaction history for {$currentPortfolio?.name}
                    {:else}
                        All trades (Aggregated)
                    {/if}
                </p>
            </div>
            <div class="flex gap-2 w-full sm:w-auto">
                <Button
                    variant="outline"
                    href="/trades/import"
                    class="flex-1 sm:flex-none {!$currentPortfolio?.id
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
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                        />
                    </svg>
                    Import CSV
                </Button>
                <Button
                    variant="default"
                    on:click={() => (showNewModal = true)}
                    class="flex-1 sm:flex-none {!$currentPortfolio?.id
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
                    New Trade
                </Button>
            </div>
        </div>

        <!-- Search + Filters -->
        <Card>
            <SearchPagination
                bind:search={searchTerm}
                searchLabel="Search by ticker or name"
                searchPlaceholder="e.g. AAPL or Apple"
                bind:page={currentPage}
                bind:pageSize
                total={totalTrades}
            >
                <svelte:fragment slot="filters">
                    <div class="min-w-[180px]">
                        <Select
                            label="Filter by type"
                            bind:value={tradeTypeFilter}
                            options={tradeTypeOptions}
                        />
                    </div>
                </svelte:fragment>
            </SearchPagination>
        </Card>

        <!-- Trades Table -->
        {#if loading}
            <Card>
                <div class="flex gap-4">
                    <Skeleton className="h-10 flex-1 rounded-md" />
                    <Skeleton className="h-10 w-40 rounded-md" />
                </div>
            </Card>
            <Card>
                <div class="space-y-3">
                    <div class="flex gap-4 border-b border-border pb-3">
                        {#each Array(6) as _}
                            <Skeleton className="h-4 flex-1" />
                        {/each}
                    </div>
                    {#each Array(8) as _}
                        <div class="flex gap-4">
                            {#each Array(6) as _}
                                <Skeleton className="h-4 flex-1" />
                            {/each}
                        </div>
                    {/each}
                </div>
            </Card>
        {:else if totalTrades === 0}
            <Card
                title="No trades"
                subtitle="Create your first trade to track investments"
            >
                <div class="py-8 text-center">
                    <p class="mb-4 text-muted-foreground">
                        {tradeTypeFilter === "all"
                            ? "You don't have any trades yet."
                            : `No ${tradeTypeFilter} trades found.`}
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
            <Card title="Trade History">
                {#if selectedTradeIds.size > 0}
                    <div
                        class="mb-4 flex items-center justify-between gap-4 bg-blue-50 dark:bg-blue-950 p-3 rounded border border-blue-200 dark:border-blue-800"
                    >
                        <span class="text-sm text-blue-900 dark:text-blue-100">
                            {selectedTradeIds.size} trade{selectedTradeIds.size !==
                            1
                                ? "s"
                                : ""} selected
                        </span>
                        <Button
                            variant="destructive"
                            on:click={() => (showBulkDeleteModal = true)}
                            class="text-sm"
                        >
                            Delete Selected
                        </Button>
                    </div>
                {/if}
                <div class="overflow-x-auto -mx-4 md:mx-0">
                    <TradeTable
                        trades={pagedTrades}
                        bind:selectedIds={selectedTradeIds}
                        on:edit={(e) => handleEditTrade(e.detail)}
                        on:delete={(e) => handleDeleteTrade(e.detail)}
                    />
                </div>
            </Card>
        {/if}
    </div>
</div>

<!-- New Trade Modal -->
<Modal
    open={showNewModal}
    title="Create Trade"
    onClose={() => (showNewModal = false)}
>
    <TradeForm
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

<!-- Edit Trade Modal -->
{#if editingTrade}
    <Modal
        open={showEditModal}
        title="Edit Trade"
        onClose={() => {
            showEditModal = false;
            editingTrade = null;
        }}
    >
        <TradeForm
            on:submit={(e) => handleUpdateTrade(e.detail)}
            trade={editingTrade}
        />
        <svelte:fragment slot="footer">
            <Button
                variant="outline"
                on:click={() => {
                    showEditModal = false;
                    editingTrade = null;
                }}
            >
                Cancel
            </Button>
        </svelte:fragment>
    </Modal>
{/if}

<!-- Bulk Delete Modal -->
<Modal
    open={showBulkDeleteModal}
    title="Delete Selected Trades"
    onClose={() => (showBulkDeleteModal = false)}
>
    <div class="space-y-4">
        <p class="text-muted-foreground">
            Are you sure you want to delete {selectedTradeIds.size} trade{selectedTradeIds.size !==
            1
                ? "s"
                : ""}? This cannot be undone.
        </p>
    </div>
    <svelte:fragment slot="footer">
        <Button
            variant="outline"
            on:click={() => (showBulkDeleteModal = false)}
        >
            Cancel
        </Button>
        <Button variant="destructive" on:click={handleBulkDelete}>
            Delete {selectedTradeIds.size} Trade{selectedTradeIds.size !== 1
                ? "s"
                : ""}
        </Button>
    </svelte:fragment>
</Modal>
