<script lang="ts">
    import Amount from "./Amount.svelte";
    import {
        formatCompactCurrency,
        formatCurrency,
        formatPercent,
    } from "#lib/utils/format.js";
    import { cn } from "#lib/utils/cn.js";

    export let label: string;
    export let value: number | string;
    export let description = "";
    export let currency = "USD";
    export let format: "currency" | "percent" = "currency";
    export let tone: "neutral" | "positive" | "negative" = "neutral";

    $: full =
        format === "percent"
            ? formatPercent(value)
            : formatCurrency(value, currency);
    // Below md, long amounts shrink to "$1.39M" with the exact figure underneath.
    $: compact =
        format === "percent" ? full : formatCompactCurrency(value, currency);
    $: isCompacted = compact !== full;
</script>

<div
    class={cn(
        "rounded-xl border p-4 md:p-5 shadow-sm",
        tone === "positive" && "border-positive/20 bg-positive/5",
        tone === "negative" && "border-negative/20 bg-negative/5",
        tone === "neutral" && "border-border bg-card",
    )}
>
    <p
        class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2"
    >
        {label}
    </p>
    <div
        class={cn(
            "font-serif text-2xl sm:text-3xl md:text-4xl leading-none",
            tone === "positive" && "text-positive",
            tone === "negative" && "text-negative",
            tone === "neutral" && "text-foreground",
        )}
    >
        {#if isCompacted}
            <span class="md:hidden"><Amount value={compact} /></span>
            <span class="hidden md:inline"><Amount value={full} /></span>
        {:else}
            <Amount value={full} />
        {/if}
    </div>
    <p class="mt-2 text-xs text-muted-foreground">
        {#if isCompacted}
            <span class="md:hidden"><Amount value={full} /></span>
            <span class="hidden md:inline">{description}</span>
        {:else}
            {description}
        {/if}
    </p>
</div>
