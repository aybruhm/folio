<script lang="ts">
    import Button from "./Button.svelte";
    import { CURRENCIES } from "#lib/constants/currencies.js";
    import type { BulkTradeRowError } from "#lib/api/types/index.js";
    import {
        ASSET_CLASSES,
        MARKET_DATA_PROVIDERS,
        MAX_BULK_ROWS,
        TRADE_TYPES,
        isBlankRow,
        newBulkRow,
        type BulkRow,
    } from "#lib/utils/bulkTrades.js";

    // Called with the filled rows once they pass this form's own checks.
    export let onSubmit: (rows: BulkRow[]) => void = () => {};
    export let rows: BulkRow[] = [newBulkRow(), newBulkRow(), newBulkRow()];
    export let isLoading = false;
    // Rejections from the server, indexed by position in the last submitted batch.
    export let serverErrors: BulkTradeRowError[] = [];
    // A problem that isn't about one row (network, session, ...).
    export let formError = "";

    const currencies = CURRENCIES.map((c) => c.value);
    const inputClass =
        "h-9 w-full rounded-md border border-input bg-background px-2 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

    let showAdvanced = false;
    let localError = "";
    // Errors by row key, from this form's own checks or from the server.
    let rowErrors: Record<number, string> = {};
    // Row keys in the order they were last sent, to map server indexes back to rows.
    let submittedKeys: number[] = [];

    $: applyServerErrors(serverErrors);
    $: filledCount = rows.filter((r) => !isBlankRow(r)).length;
    $: columnCount = showAdvanced ? 11 : 9;

    function applyServerErrors(errors: BulkTradeRowError[]) {
        const next: Record<number, string> = {};
        for (const error of errors) {
            const key = submittedKeys[error.index];
            if (key !== undefined) next[key] = error.message;
        }
        rowErrors = next;
    }

    function addRow() {
        if (rows.length >= MAX_BULK_ROWS) return;
        const last = rows[rows.length - 1];
        rows = [
            ...rows,
            newBulkRow(
                last && {
                    trade_type: last.trade_type,
                    trade_date: last.trade_date,
                    trade_currency: last.trade_currency,
                    asset_class: last.asset_class,
                    market_data_provider: last.market_data_provider,
                },
            ),
        ];
    }

    function duplicateRow(index: number) {
        if (rows.length >= MAX_BULK_ROWS) return;
        const copy = newBulkRow(rows[index]);
        rows = [...rows.slice(0, index + 1), copy, ...rows.slice(index + 1)];
    }

    function removeRow(index: number) {
        rows =
            rows.length > 1
                ? rows.filter((_, i) => i !== index)
                : [newBulkRow()];
    }

    function handleSubmit() {
        localError = "";
        const filled = rows.filter((r) => !isBlankRow(r));
        if (filled.length === 0) {
            localError = "Fill in at least one trade.";
            return;
        }

        const problems: Record<number, string> = {};
        for (const row of filled) {
            if (!row.ticker.trim()) problems[row.key] = "Ticker is required";
            else if (!row.trade_date) problems[row.key] = "Date is required";
            else if (!row.quantity) problems[row.key] = "Quantity is required";
            else if (!row.price) problems[row.key] = "Price is required";
        }
        rowErrors = problems;
        if (Object.keys(problems).length > 0) return;

        submittedKeys = filled.map((r) => r.key);
        onSubmit(filled);
    }

    // Enter moves on in a spreadsheet-style grid; it must not save the whole batch.
    function ignoreEnter(event: KeyboardEvent) {
        if (
            event.key === "Enter" &&
            (event.target as HTMLElement).tagName === "INPUT"
        ) {
            event.preventDefault();
        }
    }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        class="-mx-1 overflow-x-auto px-1"
        role="presentation"
        on:keydown={ignoreEnter}
    >
        <table class="w-full {showAdvanced ? 'min-w-[1240px]' : 'min-w-[960px]'} text-sm">
            <thead>
                <tr
                    class="text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                >
                    <th class="w-8 pb-2 pr-2">#</th>
                    <th class="w-32 pb-2 pr-2">Ticker</th>
                    <th class="w-24 pb-2 pr-2">Type</th>
                    <th class="w-48 pb-2 pr-2">Date &amp; time</th>
                    <th class="w-32 pb-2 pr-2">Quantity</th>
                    <th class="w-28 pb-2 pr-2">Price</th>
                    <th class="w-24 pb-2 pr-2">Fees</th>
                    <th class="w-24 pb-2 pr-2">Currency</th>
                    {#if showAdvanced}
                        <th class="w-32 pb-2 pr-2">Asset class</th>
                        <th class="w-40 pb-2 pr-2">Market data</th>
                    {/if}
                    <th class="w-20 pb-2"><span class="sr-only">Actions</span></th>
                </tr>
            </thead>
            <tbody>
                {#each rows as row, i (row.key)}
                    <tr
                        class="align-top {rowErrors[row.key]
                            ? 'bg-destructive/5'
                            : ''}"
                    >
                        <td class="py-1.5 pr-2 text-xs text-muted-foreground">
                            {i + 1}
                        </td>
                        <td class="py-1.5 pr-2">
                            <input
                                class={inputClass}
                                bind:value={row.ticker}
                                placeholder="AAPL"
                                aria-label="Ticker, row {i + 1}"
                                autocomplete="off"
                            />
                        </td>
                        <td class="py-1.5 pr-2">
                            <select
                                class={inputClass}
                                bind:value={row.trade_type}
                                aria-label="Type, row {i + 1}"
                            >
                                {#each TRADE_TYPES as option}
                                    <option value={option.value}>{option.label}</option>
                                {/each}
                            </select>
                        </td>
                        <td class="py-1.5 pr-2">
                            <input
                                class={inputClass}
                                type="datetime-local"
                                bind:value={row.trade_date}
                                aria-label="Date and time, row {i + 1}"
                            />
                        </td>
                        <td class="py-1.5 pr-2">
                            <input
                                class={inputClass}
                                type="number"
                                step="0.00000001"
                                bind:value={row.quantity}
                                placeholder="0.00000001"
                                aria-label="Quantity, row {i + 1}"
                            />
                        </td>
                        <td class="py-1.5 pr-2">
                            <input
                                class={inputClass}
                                type="number"
                                step="0.01"
                                bind:value={row.price}
                                placeholder="150.00"
                                aria-label="Price, row {i + 1}"
                            />
                        </td>
                        <td class="py-1.5 pr-2">
                            <input
                                class={inputClass}
                                type="number"
                                step="0.0001"
                                bind:value={row.fees}
                                aria-label="Fees, row {i + 1}"
                            />
                        </td>
                        <td class="py-1.5 pr-2">
                            <select
                                class={inputClass}
                                bind:value={row.trade_currency}
                                aria-label="Currency, row {i + 1}"
                            >
                                {#each currencies as code}
                                    <option value={code}>{code}</option>
                                {/each}
                            </select>
                        </td>
                        {#if showAdvanced}
                            <td class="py-1.5 pr-2">
                                <select
                                    class={inputClass}
                                    bind:value={row.asset_class}
                                    aria-label="Asset class, row {i + 1}"
                                >
                                    {#each ASSET_CLASSES as option}
                                        <option value={option.value}>{option.label}</option>
                                    {/each}
                                </select>
                            </td>
                            <td class="py-1.5 pr-2">
                                <select
                                    class={inputClass}
                                    bind:value={row.market_data_provider}
                                    aria-label="Market data, row {i + 1}"
                                >
                                    {#each MARKET_DATA_PROVIDERS as option}
                                        <option value={option.value}>{option.label}</option>
                                    {/each}
                                </select>
                            </td>
                        {/if}
                        <td class="py-1.5">
                            <div class="flex gap-1">
                                <button
                                    type="button"
                                    class="h-9 rounded-md px-2 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
                                    title="Duplicate row {i + 1}"
                                    aria-label="Duplicate row {i + 1}"
                                    disabled={rows.length >= MAX_BULK_ROWS}
                                    on:click={() => duplicateRow(i)}>Copy</button
                                >
                                <button
                                    type="button"
                                    class="h-9 rounded-md px-2 text-xs text-muted-foreground hover:bg-muted hover:text-destructive"
                                    title="Remove row {i + 1}"
                                    aria-label="Remove row {i + 1}"
                                    on:click={() => removeRow(i)}>✕</button
                                >
                            </div>
                        </td>
                    </tr>
                    {#if rowErrors[row.key]}
                        <tr class="bg-destructive/5">
                            <td></td>
                            <td
                                colspan={columnCount - 1}
                                class="pb-2 pr-2 text-xs text-destructive"
                            >
                                <span role="alert">
                                    Row {i + 1}: {rowErrors[row.key]}
                                </span>
                            </td>
                        </tr>
                    {/if}
                {/each}
            </tbody>
        </table>
    </div>

    {#if localError || formError}
        <p class="text-sm text-destructive" role="alert">
            {localError || formError}
        </p>
    {/if}

    <div
        class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
        <div class="flex flex-wrap items-center gap-3">
            <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={rows.length >= MAX_BULK_ROWS}
                on:click={addRow}>Add row</Button
            >
            <label class="flex items-center gap-2 text-xs text-muted-foreground">
                <input type="checkbox" bind:checked={showAdvanced} />
                Asset class &amp; market data
            </label>
            <span class="text-xs text-muted-foreground">
                {rows.length} of {MAX_BULK_ROWS} rows
            </span>
        </div>
        <Button
            type="submit"
            variant="default"
            disabled={isLoading || filledCount === 0}
        >
            {isLoading
                ? "Saving..."
                : `Save ${filledCount} trade${filledCount === 1 ? "" : "s"}`}
        </Button>
    </div>
    <p class="text-xs text-muted-foreground">
        All trades are saved together. If any row is rejected, none are saved and
        the rejected rows are marked.
    </p>
</form>
