<script lang="ts">
    export const title: string = "";
    export let showLegend: boolean = true;
    export let data: { label: string; value: number }[] = [];

    const COLORS = [
        "hsl(217, 91%, 60%)",
        "hsl(160, 84%, 39%)",
        "hsl(38, 92%, 50%)",
        "hsl(346, 87%, 64%)",
        "hsl(271, 81%, 66%)",
        "hsl(196, 94%, 47%)",
        "hsl(25, 95%, 53%)",
        "hsl(142, 71%, 45%)",
    ];

    const CX = 100,
        CY = 100,
        R = 80,
        IR = 52;

    $: total = data.reduce((s, d) => s + d.value, 0);
    $: items = data.map((d, i) => ({
        ...d,
        pct: total > 0 ? (d.value / total) * 100 : 0,
        color: COLORS[i % COLORS.length],
    }));

    function slice(startDeg: number, endDeg: number): string {
        const span = endDeg - startDeg;

        if (span <= 0) return "";

        // SVG arc commands cannot represent a full 360° arc in a single segment.
        // Draw full donut slices (100%) using two half-arcs for outer and inner rings.
        if (span >= 359.999) {
            return [
                `M ${CX} ${CY - R}`,
                `A ${R} ${R} 0 1 1 ${CX} ${CY + R}`,
                `A ${R} ${R} 0 1 1 ${CX} ${CY - R}`,
                `L ${CX} ${CY - IR}`,
                `A ${IR} ${IR} 0 1 0 ${CX} ${CY + IR}`,
                `A ${IR} ${IR} 0 1 0 ${CX} ${CY - IR}`,
                "Z",
            ].join(" ");
        }

        const s = ((startDeg - 90) * Math.PI) / 180;
        const e = ((endDeg - 90) * Math.PI) / 180;
        const x1 = CX + R * Math.cos(s),
            y1 = CY + R * Math.sin(s);
        const x2 = CX + R * Math.cos(e),
            y2 = CY + R * Math.sin(e);
        const ix1 = CX + IR * Math.cos(s),
            iy1 = CY + IR * Math.sin(s);
        const ix2 = CX + IR * Math.cos(e),
            iy2 = CY + IR * Math.sin(e);
        const large = span > 180 ? 1 : 0;
        return [
            `M ${x1} ${y1}`,
            `A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`,
            `L ${ix2} ${iy2}`,
            `A ${IR} ${IR} 0 ${large} 0 ${ix1} ${iy1}`,
            "Z",
        ].join(" ");
    }

    $: slices = (() => {
        let angle = 0;
        return items.map((item) => {
            const start = angle;
            const end = angle + (item.pct / 100) * 360;
            angle = end;
            return { ...item, path: slice(start, end) };
        });
    })();

    let hoveredIdx = -1;
</script>

<div class="flex flex-col gap-4">
    {#if data.length === 0}
        <div
            class="flex items-center justify-center h-40 text-muted-foreground text-sm"
        >
            No data available
        </div>
    {:else}
        <div class="flex items-center gap-6 flex-wrap">
            <!-- Donut SVG -->
            <div class="relative flex-shrink-0">
                <svg width="200" height="200" viewBox="0 0 200 200">
                    {#each slices as s, i}
                        <path
                            role="img"
                            aria-label={`${s.label}: ${s.pct.toFixed(1)}%`}
                            d={s.path}
                            fill={s.color}
                            opacity={hoveredIdx === -1 || hoveredIdx === i
                                ? 1
                                : 0.4}
                            class="transition-opacity duration-150 cursor-pointer"
                            on:mouseenter={() => (hoveredIdx = i)}
                            on:mouseleave={() => (hoveredIdx = -1)}
                        />
                    {/each}
                    <!-- Center label -->
                    {#if hoveredIdx >= 0}
                        <text
                            x={CX}
                            y={CY - 6}
                            text-anchor="middle"
                            font-size="11"
                            fill="hsl(var(--muted-foreground))"
                            >{slices[hoveredIdx].label}</text
                        >
                        <text
                            x={CX}
                            y={CY + 12}
                            text-anchor="middle"
                            font-size="16"
                            font-weight="700"
                            fill="hsl(var(--foreground))"
                            >{slices[hoveredIdx].pct.toFixed(1)}%</text
                        >
                    {:else}
                        <text
                            x={CX}
                            y={CY + 6}
                            text-anchor="middle"
                            font-size="13"
                            font-weight="600"
                            fill="hsl(var(--muted-foreground))">Portfolio</text
                        >
                    {/if}
                </svg>
            </div>

            <!-- Legend -->
            {#if showLegend}
                <div class="flex flex-col gap-2 flex-1 min-w-0">
                    {#each items as item, i}
                        <button
                            class="flex items-center gap-2 text-left hover:opacity-80 transition-opacity w-full"
                            on:mouseenter={() => (hoveredIdx = i)}
                            on:mouseleave={() => (hoveredIdx = -1)}
                        >
                            <span
                                class="flex-shrink-0 w-2.5 h-2.5 rounded-full"
                                style="background-color: {item.color}"
                            />
                            <span
                                class="text-sm text-foreground truncate flex-1"
                                >{item.label}</span
                            >
                            <span
                                class="text-sm font-semibold text-foreground flex-shrink-0"
                            >
                                {item.pct.toFixed(1)}%
                            </span>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}
</div>
