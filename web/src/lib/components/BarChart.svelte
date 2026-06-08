<script lang="ts">
    import { hideAmounts } from "$lib/stores";

    export let data: { label: string; value: number }[] = [];
    export let title: string = "";
    export let height: string = "h-80";

    const BAR_H = 340;
    const BAR_W = 52;

    $: maxAbs = data.length
        ? Math.max(...data.map((d) => Math.abs(d.value)), 1)
        : 1;

    function barHeight(v: number): number {
        return Math.max(2, (Math.abs(v) / maxAbs) * BAR_H);
    }

    function abbrev(val: number): string {
        if (Math.abs(val) >= 1_000_000)
            return `${(val / 1_000_000).toFixed(1)}M`;
        if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(0)}k`;
        return val.toFixed(0);
    }

    let hoveredIdx = -1;
</script>

<div class="overflow-x-auto pb-2">
    {#if data.length === 0}
        <div
            class="flex items-center justify-center {height} text-muted-foreground text-sm"
        >
            No data available
        </div>
    {:else}
        <div
            class="flex items-end gap-2 px-4"
            style="min-width: {data.length * (BAR_W + 8)}px; height: {BAR_H +
                72}px"
        >
            {#each data as item, i}
                {@const h = barHeight(item.value)}
                {@const isPos = item.value >= 0}
                <div
                    class="flex flex-col items-center gap-1 cursor-default"
                    style="width: {BAR_W}px"
                    on:mouseenter={() => (hoveredIdx = i)}
                    on:mouseleave={() => (hoveredIdx = -1)}
                >
                    <!-- Value label on hover -->
                    <div class="h-5 flex items-center justify-center">
                        {#if hoveredIdx === i}
                            <span
                                class="text-xs font-semibold px-1 rounded"
                                class:text-positive={isPos}
                                class:text-negative={!isPos}
                            >
                                {#if $hideAmounts}
                                    ••••••
                                {:else}
                                    {isPos ? "+" : ""}{abbrev(item.value)}
                                {/if}
                            </span>
                        {/if}
                    </div>

                    <!-- Bar area -->
                    <div
                        class="flex items-end justify-center"
                        style="height: {BAR_H}px; width: {BAR_W}px"
                    >
                        <div
                            class="w-full rounded-t transition-all duration-150"
                            style="
                height: {h}px;
                background-color: {isPos ? '#34D399' : '#F87171'};
                opacity: {hoveredIdx === -1 || hoveredIdx === i ? 1 : 0.5};
              "
                        />
                    </div>

                    <!-- Label -->
                    <span
                        class="text-center leading-tight"
                        style="font-size: 10px; color: hsl(var(--muted-foreground)); width: {BAR_W}px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;"
                        title={item.label}
                    >
                        {item.label}
                    </span>
                </div>
            {/each}
        </div>
    {/if}
</div>
