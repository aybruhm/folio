<script lang="ts">
    import Input from "$lib/components/Input.svelte";
    import Select from "$lib/components/Select.svelte";
    import Button from "$lib/components/Button.svelte";
    import { cn } from "$lib/utils/cn";

    export let search = "";
    export let searchLabel = "Search";
    export let searchPlaceholder = "Search...";
    export let page = 1;
    export let pageSize = 25;
    export let total = 0;
    export let pageSizeOptions: number[] = [10, 25, 50, 100];
    export let showPageSize = true;
    export let showSummary = true;
    export let className: string = "";

    let pageSizeSelection = String(pageSize);

    $: totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
    $: if (page < 1) page = 1;
    $: if (page > totalPages) page = totalPages;
    $: pageSizeSelection = String(pageSize);

    function handlePageSizeChange() {
        const next = Number(pageSizeSelection);
        if (!Number.isNaN(next) && next > 0 && next !== pageSize) {
            pageSize = next;
            page = 1;
        }
    }

    function handleClearSearch() {
        if (search) {
            search = "";
            page = 1;
        }
    }

    function goToPage(nextPage: number) {
        if (nextPage < 1 || nextPage > totalPages || nextPage === page) return;
        page = nextPage;
    }

    $: startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
    $: endItem = Math.min(total, page * pageSize);
    $: pageSizeOptionsWithLabels = pageSizeOptions.map((option) => ({
        label: `${option} / page`,
        value: String(option),
    }));
</script>

<div class={cn("space-y-4", className)}>
    <div
        class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between"
    >
        <div class="flex-1">
            <Input
                label={searchLabel}
                placeholder={searchPlaceholder}
                bind:value={search}
                on:change
            />
        </div>
        <div class="flex flex-col gap-3 md:flex-row md:items-end">
            <slot name="filters" />
            {#if showPageSize}
                <div class="min-w-[160px]">
                    <Select
                        label="Page size"
                        bind:value={pageSizeSelection}
                        options={pageSizeOptionsWithLabels}
                        on:change={handlePageSizeChange}
                    />
                </div>
            {/if}
            <Button
                variant="outline"
                class="h-10"
                on:click={handleClearSearch}
                disabled={!search}
            >
                Clear
            </Button>
        </div>
    </div>

    <div
        class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
        {#if showSummary}
            <div class="text-xs md:text-sm text-muted-foreground">
                {#if total === 0}
                    No results
                {:else}
                    Showing {startItem}-{endItem} of {total}
                {/if}
            </div>
        {/if}
        <div class="flex items-center gap-2">
            <Button
                variant="outline"
                size="sm"
                on:click={() => goToPage(page - 1)}
                disabled={page <= 1}
            >
                Previous
            </Button>
            <div class="text-xs md:text-sm text-muted-foreground">
                Page {page} of {totalPages}
            </div>
            <Button
                variant="outline"
                size="sm"
                on:click={() => goToPage(page + 1)}
                disabled={page >= totalPages}
            >
                Next
            </Button>
        </div>
    </div>
</div>
