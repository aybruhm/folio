<script lang="ts">
    import Card from "#lib/components/Card.svelte";
    import Skeleton from "#lib/components/Skeleton.svelte";
    import Button from "#lib/components/Button.svelte";
    import Modal from "#lib/components/Modal.svelte";
    import PortfolioForm from "#lib/components/PortfolioForm.svelte";
    import Input from "#lib/components/Input.svelte";
    import Amount from "#lib/components/Amount.svelte";
    import Badge from "#lib/components/Badge.svelte";
    import {
        currentPortfolio,
        portfolios,
        selectInitialPortfolio,
    } from "#lib/stores/index.js";
    import { api } from "#lib/api/client.js";
    import { PortfolioController } from "#lib/api/controllers/index.js";
    import type {
        CreatePortfolioRequest,
        Portfolio,
        UpdatePortfolioRequest,
    } from "#lib/api/types/index.js";
    import { onMount } from "svelte";
    import { page } from "$app/state";
    import { formatCurrency } from "#lib/utils/format.js";
    import { invalidateAllAnalytics } from "#lib/cache/index.js";

    let loading = true;
    let showNewModal = false;
    let portfolioController: PortfolioController;
    let portfolioStats: Record<string, any> = {};

    let editingPortfolio: { id: string; name: string; description: string } | null = null;
    let editSaving = false;

    // $portfolios (shared with the switcher and other pages) only holds active
    // portfolios; archived ones are kept locally and shown on request.
    let archivedPortfolios: Portfolio[] = [];
    let showArchived = false;
    let archivingId: string | null = null;

    $: visiblePortfolios = showArchived
        ? [...$portfolios, ...archivedPortfolios]
        : $portfolios;

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        if (page.url.searchParams.get("new") === "true") showNewModal = true;
        await loadPortfolios();
    });

    async function loadPortfolios() {
        try {
            loading = true;
            const data = await portfolioController.listPortfolios(true) || [];
            const active = data.filter((p) => !p.archived_at);
            archivedPortfolios = data.filter((p) => p.archived_at);
            portfolios.set(active as any);
            // Drop the selection if the selected portfolio was just archived.
            if (
                $currentPortfolio?.id &&
                !active.some((p) => p.id === $currentPortfolio.id)
            ) {
                selectInitialPortfolio(active as any);
            }

            try {
                const analyticsList =
                    await portfolioController.listPortfolioAnalytics({
                        timeframe: "all",
                        include_archived: showArchived,
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

    function openEditModal(portfolio: { id: string; name: string; description?: string }) {
        editingPortfolio = { id: portfolio.id, name: portfolio.name, description: portfolio.description ?? "" };
    }

    async function handleUpdatePortfolio() {
        if (!editingPortfolio) return;
        editSaving = true;
        try {
            const request: UpdatePortfolioRequest = {
                name: editingPortfolio.name,
                description: editingPortfolio.description || null,
            };
            await portfolioController.updatePortfolio(editingPortfolio.id, request);
            await loadPortfolios();
            editingPortfolio = null;
        } catch (e) {
            console.error("Failed to update portfolio:", e);
        } finally {
            editSaving = false;
        }
    }

    async function handleSetArchived(id: string, archived: boolean) {
        archivingId = id;
        try {
            if (archived) {
                await portfolioController.archivePortfolio(id);
            } else {
                await portfolioController.unarchivePortfolio(id);
            }
            // Cached aggregate views (dashboard, analytics) include this portfolio.
            await invalidateAllAnalytics();
            await loadPortfolios();
        } catch (e) {
            console.error(
                `Failed to ${archived ? "archive" : "unarchive"} portfolio:`,
                e,
            );
        } finally {
            archivingId = null;
        }
    }

    async function toggleShowArchived() {
        showArchived = !showArchived;
        // Archived stats are only fetched when they are shown.
        if (showArchived) await loadPortfolios();
    }

    async function handleDeletePortfolio(id: string) {
        if (!confirm("Are you sure you want to delete this portfolio?")) return;

        try {
            await portfolioController.deletePortfolio(id);
            await invalidateAllAnalytics();
            await loadPortfolios();
        } catch (e) {
            console.error("Failed to delete portfolio:", e);
        }
    }
</script>

<svelte:head><title>Portfolios — Folio</title></svelte:head>

<div class="min-h-screen p-4 md:p-6">
    <div class="mx-auto max-w-6xl space-y-6">
        <!-- Header -->
        <div class="flex flex-col gap-4 sm:gap-0 sm:flex-row sm:items-center sm:justify-between">
            <div class="space-y-1">
                <h1 class="font-serif text-3xl md:text-4xl text-foreground">Portfolios</h1>
                <p class="text-xs md:text-sm text-muted-foreground">Manage your investment portfolios</p>
            </div>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
                {#if archivedPortfolios.length > 0}
                    <Button variant="ghost" size="sm" on:click={toggleShowArchived} class="w-full sm:w-auto">
                        {showArchived ? "Hide" : "Show"} archived ({archivedPortfolios.length})
                    </Button>
                {/if}

                <Button
                    variant="default"
                    on:click={() => showNewModal = true}
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
                        ></path>
                    </svg>
                    New Portfolio
                </Button>
            </div>
        </div>

        {#if loading}
            <Card>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="border-b border-border">
                            <tr>
                                {#each Array(7) as _}
                                    <th class="h-9 px-3 text-left"><Skeleton className="h-3 w-16" /></th>
                                {/each}
                            </tr>
                        </thead>
                        <tbody>
                            {#each Array(4) as _}
                                <tr class="border-b border-border/60">
                                    {#each Array(7) as _}
                                        <td class="px-3 py-3"><Skeleton className="h-4 w-full" /></td>
                                    {/each}
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </Card>
        {:else if visiblePortfolios.length === 0 && archivedPortfolios.length > 0}
            <Card>
                <div class="flex flex-col items-center justify-center py-16 text-center">
                    <p class="font-medium text-foreground mb-1">All portfolios are archived</p>
                    <p class="text-sm text-muted-foreground mb-6">Show archived portfolios to view or restore them, or create a new one.</p>
                    <div class="flex gap-2">
                        <Button variant="outline" on:click={toggleShowArchived}>Show archived</Button>

                        <Button
                            variant="default"
                            on:click={() => showNewModal = true}
                        >New Portfolio</Button>
                    </div>
                </div>
            </Card>
        {:else if visiblePortfolios.length === 0}
            <Card>
                <div
                    class="flex flex-col items-center justify-center py-16 text-center"
                >
                    <div
                        class="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-muted"
                    >
                        <svg
                            class="h-6 w-6 text-muted-foreground"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="1.75"
                                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                            ></path>
                        </svg>
                    </div>
                    <p class="font-medium text-foreground mb-1">No portfolios yet</p>
                    <p class="text-sm text-muted-foreground mb-6">Create your first portfolio to start tracking your investments.</p>

                    <Button
                        variant="default"
                        on:click={() => showNewModal = true}
                    >Create First Portfolio</Button>
                </div>
            </Card>
        {:else}
            <Card>
                <div class="overflow-x-auto -mx-4 md:mx-0">
                    <table class="w-full text-sm">
                        <thead class="border-b border-border">
                            <tr>
                                <th class="h-9 px-3 text-left align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                                <th class="h-9 px-3 text-left align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Currency</th>
                                <th class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Value</th>
                                <th class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hidden sm:table-cell">TWR</th>
                                <th class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hidden sm:table-cell">MWR</th>
                                <th class="h-9 px-3 text-left align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hidden lg:table-cell">Description</th>
                                <th class="h-9 px-3 text-right align-middle text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="[&_tr:last-child]:border-0">
                            {#each visiblePortfolios as portfolio (portfolio.id)}
                                {@const stats = portfolioStats[portfolio.id]}
                                <tr
                                    class="border-b border-border/60 hover:bg-muted/30 transition-colors"
                                    class:opacity-60={portfolio.archived_at}
                                >
                                    <td class="px-3 py-3 align-middle">
                                        <span class="font-medium text-foreground">{portfolio.name}</span>
                                        {#if portfolio.archived_at}
                                            <span class="ml-2 inline-block align-middle">
                                                <Badge variant="secondary">Archived</Badge>
                                            </span>
                                        {/if}
                                    </td>
                                    <td class="px-3 py-3 align-middle">
                                        <span class="font-mono text-xs text-muted-foreground">{portfolio.base_currency}</span>
                                    </td>
                                    <td class="px-3 py-3 align-middle text-right font-mono text-xs">
                                        {#if stats}
                                            <Amount value={formatCurrency(stats.current_value ?? 0, portfolio.base_currency)} />
                                        {:else}
                                            <span class="text-muted-foreground">—</span>
                                        {/if}
                                    </td>
                                    <td class="px-3 py-3 align-middle text-right font-mono text-xs hidden sm:table-cell">
                                        {#if stats}
                                            <span class:text-positive={parseFloat(stats.twr) >= 0} class:text-negative={parseFloat(stats.twr) < 0}>
                                                {stats.twr}%
                                            </span>
                                        {:else}
                                            <span class="text-muted-foreground">—</span>
                                        {/if}
                                    </td>
                                    <td class="px-3 py-3 align-middle text-right font-mono text-xs hidden sm:table-cell">
                                        {#if stats}
                                            <span class:text-positive={parseFloat(stats.mwr) >= 0} class:text-negative={parseFloat(stats.mwr) < 0}>
                                                {stats.mwr}%
                                            </span>
                                        {:else}
                                            <span class="text-muted-foreground">—</span>
                                        {/if}
                                    </td>
                                    <td class="px-3 py-3 align-middle hidden lg:table-cell">
                                        {#if portfolio.description}
                                            <span class="text-xs text-muted-foreground block max-w-[200px] truncate">{portfolio.description}</span>
                                        {:else}
                                            <span class="text-muted-foreground">—</span>
                                        {/if}
                                    </td>
                                    <td class="px-3 py-3 align-middle">
                                        <div class="flex items-center justify-end gap-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                href="/portfolios/{portfolio.id}"
                                            >View</Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                on:click={() => openEditModal(portfolio)}
                                            >Edit</Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                disabled={archivingId === portfolio.id}
                                                on:click={() => handleSetArchived(portfolio.id, !portfolio.archived_at)}
                                            >
                                                {portfolio.archived_at ? "Unarchive" : "Archive"}
                                            </Button>
                                            <Button variant="destructive" size="sm" on:click={() => handleDeletePortfolio(portfolio.id)}>Delete</Button>
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </Card>
        {/if}
    </div>
</div>

<!-- Create modal -->

<Modal
    open={showNewModal}
    title="Create Portfolio"
    onClose={() => showNewModal = false}
>
    <PortfolioForm
        onSubmit={handleCreatePortfolio}
        portfolio={{ name: "", base_currency: "USD", description: "" }}
    />
    <svelte:fragment slot="footer">
        <Button
            variant="outline"
            on:click={() => showNewModal = false}
        >Cancel</Button>
    </svelte:fragment>
</Modal>

<!-- Edit modal -->

<Modal
    open={!!editingPortfolio}
    title="Edit Portfolio"
    onClose={() => editingPortfolio = null}
>
    {#if editingPortfolio}
        <form on:submit|preventDefault={handleUpdatePortfolio} class="space-y-4">
            <Input
                label="Portfolio Name"
                placeholder="My Investment Portfolio"
                bind:value={editingPortfolio.name}
                required
            />
            <Input
                label="Description"
                placeholder="Optional description"
                bind:value={editingPortfolio.description}
            />
        </form>
    {/if}
    <svelte:fragment slot="footer">
        <Button
            variant="outline"
            on:click={() => editingPortfolio = null}
        >Cancel</Button>

        <Button
            variant="default"
            disabled={editSaving}
            on:click={handleUpdatePortfolio}
        >{editSaving ? "Saving…" : "Save Changes"}</Button>
    </svelte:fragment>
</Modal>
