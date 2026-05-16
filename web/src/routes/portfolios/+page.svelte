<script lang="ts">
    import Card from "$lib/components/Card.svelte";
    import Button from "$lib/components/Button.svelte";
    import Modal from "$lib/components/Modal.svelte";
    import PortfolioForm from "$lib/components/PortfolioForm.svelte";
    import { portfolios } from "$lib/stores";
    import { api } from "$lib/api/client";
    import { PortfolioController } from "$lib/api/controllers";
    import type { CreatePortfolioRequest, Portfolio } from "$lib/api/types";
    import { onMount } from "svelte";
    import { formatCurrency } from "$lib/utils/format";

    let loading = true;
    let showNewModal = false;
    let portfolioController: PortfolioController;
    let portfolioStats: Record<string, any> = {};

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        await loadPortfolios();
    });

    async function loadPortfolios() {
        try {
            loading = true;
            const data = await portfolioController.listPortfolios();
            portfolios.set(data || []);

            try {
                const analyticsList =
                    await portfolioController.listPortfolioAnalytics({
                        timeframe: "1y",
                    });
                portfolioStats = (analyticsList || []).reduce(
                    (acc: Record<string, any>, item: any) => {
                        acc[item.portfolio_id] = item;
                        return acc;
                    },
                    {},
                );
            } catch (e) {
                console.error("Failed to load portfolio analytics:", e);
            }
        } catch (e) {
            console.error("Failed to load portfolios:", e);
        } finally {
            loading = false;
        }
    }

    async function handleCreatePortfolio(portfolio: any) {
        try {
            const request: CreatePortfolioRequest = {
                name: portfolio.name,
                base_currency: portfolio.base_currency,
                description: portfolio.description,
            };
            await portfolioController.createPortfolio(request);
            await loadPortfolios();
            showNewModal = false;
        } catch (e) {
            console.error("Failed to create portfolio:", e);
        }
    }

    async function handleDeletePortfolio(id: string) {
        if (!confirm("Are you sure you want to delete this portfolio?")) return;

        try {
            await portfolioController.deletePortfolio(id);
            await loadPortfolios();
        } catch (e) {
            console.error("Failed to delete portfolio:", e);
        }
    }
</script>

<svelte:head>
    <title>Portfolios — Folio</title>
</svelte:head>

<div class="min-h-screen bg-background p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div
            class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center"
        >
            <div class="space-y-2">
                <h1 class="text-2xl md:text-3xl font-bold text-foreground">
                    Portfolios
                </h1>
                <p class="text-xs md:text-sm text-muted-foreground">
                    Manage your investment portfolios
                </p>
            </div>
            <Button
                variant="default"
                on:click={() => (showNewModal = true)}
                class="w-full sm:w-auto"
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
                New Portfolio
            </Button>
        </div>

        {#if loading}
            <div class="flex justify-center py-12">
                <div class="text-muted-foreground">Loading portfolios...</div>
            </div>
        {:else if $portfolios.length === 0}
            <Card
                title="No portfolios yet"
                subtitle="Create your first portfolio to get started"
            >
                <div class="text-center py-8">
                    <p class="mb-4 text-muted-foreground">
                        Portfolios help you organize and track multiple
                        investment accounts.
                    </p>
                    <Button
                        variant="default"
                        on:click={() => (showNewModal = true)}
                    >
                        Create First Portfolio
                    </Button>
                </div>
            </Card>
        {:else}
            <div
                class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 lg:grid-cols-3"
            >
                {#each $portfolios as portfolio}
                    {@const stats = portfolioStats[portfolio.id]}
                    <Card
                        title={portfolio.name}
                        subtitle={portfolio.base_currency}
                    >
                        <div class="space-y-4">
                            {#if stats}
                                {@const currentValue = stats.current_value ?? 0}
                                <div class="space-y-2">
                                    <div class="flex justify-between">
                                        <span
                                            class="text-xs md:text-sm text-muted-foreground"
                                            >Value</span
                                        >
                                        <span
                                            class="text-sm md:text-base font-semibold text-foreground"
                                        >
                                            {formatCurrency(
                                                currentValue,
                                                portfolio.base_currency,
                                            )}
                                        </span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span
                                            class="text-xs md:text-sm text-muted-foreground"
                                            >TWR</span
                                        >
                                        <span
                                            class="text-sm md:text-base font-semibold"
                                            class:text-positive={parseFloat(
                                                stats.twr,
                                            ) >= 0}
                                            class:text-negative={parseFloat(
                                                stats.twr,
                                            ) < 0}
                                        >
                                            {stats.twr}%
                                        </span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span
                                            class="text-xs md:text-sm text-muted-foreground"
                                            >MWR</span
                                        >
                                        <span
                                            class="text-sm md:text-base font-semibold"
                                            class:text-positive={parseFloat(
                                                stats.mwr,
                                            ) >= 0}
                                            class:text-negative={parseFloat(
                                                stats.mwr,
                                            ) < 0}
                                        >
                                            {stats.mwr}%
                                        </span>
                                    </div>
                                </div>
                            {/if}

                            {#if portfolio.description}
                                <p class="text-xs text-muted-foreground italic">
                                    {portfolio.description}
                                </p>
                            {/if}

                            <div class="flex gap-2 pt-4">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    href="/portfolios/{portfolio.id}"
                                >
                                    View
                                </Button>
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    on:click={() =>
                                        handleDeletePortfolio(portfolio.id)}
                                >
                                    Delete
                                </Button>
                            </div>
                        </div>
                    </Card>
                {/each}
            </div>
        {/if}
    </div>
</div>

<Modal
    open={showNewModal}
    title="Create Portfolio"
    onClose={() => (showNewModal = false)}
>
    <PortfolioForm
        onSubmit={handleCreatePortfolio}
        portfolio={{ name: "", base_currency: "USD", description: "" }}
    />
    <svelte:fragment slot="footer">
        <Button variant="outline" on:click={() => (showNewModal = false)}>
            Cancel
        </Button>
    </svelte:fragment>
</Modal>
