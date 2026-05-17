<script lang="ts">
    import { onMount } from "svelte";
    import { formatCurrency } from "$lib/utils/format";

    export let data: { name: string; value: number }[] = [];
    export let title: string = "";
    export let height: string = "h-80";
    export let currency: string = "USD";

    const W = 1200,
        H = 420;
    const ML = 60,
        MR = 16,
        MT = 16,
        MB = 40;
    const innerW = W - ML - MR;
    const innerH = H - MT - MB;

    $: minVal = data.length ? Math.min(...data.map((d) => d.value)) : 0;
    $: maxVal = data.length ? Math.max(...data.map((d) => d.value)) : 1;
    $: yPad = (maxVal - minVal) * 0.08 || 1;
    $: yMin = minVal - yPad;
    $: yMax = maxVal + yPad;
    $: yRange = yMax - yMin;

    function xPos(i: number): number {
        if (data.length <= 1) return ML + innerW / 2;
        return ML + (i / (data.length - 1)) * innerW;
    }

    function yPos(v: number): number {
        return MT + innerH - ((v - yMin) / yRange) * innerH;
    }

    function buildPath(pts: { x: number; y: number }[]): string {
        if (pts.length < 2) return "";
        let d = `M ${pts[0].x},${pts[0].y}`;
        for (let i = 0; i < pts.length - 1; i++) {
            const cpx = pts[i].x + (pts[i + 1].x - pts[i].x) / 2;
            d += ` C ${cpx},${pts[i].y} ${cpx},${pts[i + 1].y} ${pts[i + 1].x},${pts[i + 1].y}`;
        }
        return d;
    }

    $: pts = data.map((d, i) => ({ x: xPos(i), y: yPos(d.value) }));
    $: linePath = buildPath(pts);
    $: areaPath =
        pts.length >= 2
            ? `${linePath} L ${pts[pts.length - 1].x},${MT + innerH} L ${pts[0].x},${MT + innerH} Z`
            : "";

    $: yTicks = Array.from({ length: 5 }, (_, i) => {
        const val = yMin + (yRange / 4) * i;
        return { val, y: yPos(val) };
    }).reverse();

    $: xTicks = (() => {
        if (!data.length) return [];
        const count = Math.min(6, data.length);
        return Array.from({ length: count }, (_, i) => {
            const idx = Math.round((i / (count - 1)) * (data.length - 1));
            return { label: data[idx].name, x: xPos(idx) };
        });
    })();

    let hoverIdx = -1;
    let svgEl: SVGSVGElement;
    let isMobile = false;

    function onMouseMove(e: MouseEvent) {
        if (!svgEl || !data.length) return;
        const rect = svgEl.getBoundingClientRect();
        const svgX = ((e.clientX - rect.left) / rect.width) * W;
        const frac = Math.max(0, Math.min(1, (svgX - ML) / innerW));
        hoverIdx = Math.round(frac * (data.length - 1));
    }

    onMount(() => {
        const media = window.matchMedia("(max-width: 768px)");
        const update = () => {
            isMobile = media.matches;
        };

        update();
        media.addEventListener("change", update);

        return () => {
            media.removeEventListener("change", update);
        };
    });

    $: hoverX = hoverIdx >= 0 ? xPos(hoverIdx) : -1;
    $: hoverY = hoverIdx >= 0 ? yPos(data[hoverIdx]?.value ?? 0) : -1;
    $: tooltipRight = hoverIdx >= 0 && hoverIdx > data.length * 0.65;

    // Keep the chart readable on mobile, but avoid creating an extremely
    // wide surface when there are many points (e.g. daily data).
    // This keeps horizontal scroll useful without a giant empty-looking gap.
    $: minChartWidth = Math.min(W, Math.max(640, data.length * 22));

    // SVG text uses viewBox units, not CSS px. Because the chart may render
    // narrower than its 1200-unit viewBox on mobile, we convert target pixel
    // sizes into SVG units so font size visually matches the intended size.
    $: viewScale = minChartWidth / W;
    $: svgUnitsPerPx = 1 / Math.max(viewScale, 0.01);

    $: axisFontSize = (isMobile ? 11 : 10) * svgUnitsPerPx;
    $: tooltipTitleFontSize = (isMobile ? 12 : 10) * svgUnitsPerPx;
    $: tooltipValueFontSize = (isMobile ? 14 : 13) * svgUnitsPerPx;

    // Roomier tooltip on mobile so date + value are easier to read.
    $: tooltipWidth = (isMobile ? 176 : 118) * svgUnitsPerPx;
    $: tooltipHeight = (isMobile ? 64 : 42) * svgUnitsPerPx;
    $: tooltipYOffset = (isMobile ? 72 : 38) * svgUnitsPerPx;
    $: tooltipHorizontalOffset = tooltipWidth + 10 * svgUnitsPerPx;
    $: tooltipPaddingX = (isMobile ? 12 : 8) * svgUnitsPerPx;
    $: tooltipTitleY = (isMobile ? 24 : 15) * svgUnitsPerPx;
    $: tooltipValueY = (isMobile ? 46 : 32) * svgUnitsPerPx;

    function abbrev(val: number): string {
        if (Math.abs(val) >= 1_000_000)
            return `$${(val / 1_000_000).toFixed(1)}M`;
        if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(0)}k`;
        return `$${val.toFixed(0)}`;
    }
</script>

<div class="{height} relative select-none overflow-x-auto">
    {#if data.length === 0}
        <div
            class="flex items-center justify-center h-full text-muted-foreground text-sm"
        >
            No data available
        </div>
    {:else}
        <div style="min-width: {minChartWidth}px" class="h-full">
            <svg
                bind:this={svgEl}
                viewBox="0 0 {W} {H}"
                class="w-full h-full cursor-crosshair"
                on:mousemove={onMouseMove}
                on:mouseleave={() => (hoverIdx = -1)}
            >
                <defs>
                    <linearGradient
                        id="lineAreaGrad"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                    >
                        <stop
                            offset="0%"
                            stop-color="hsl(var(--accent))"
                            stop-opacity="0.25"
                        />
                        <stop
                            offset="100%"
                            stop-color="hsl(var(--accent))"
                            stop-opacity="0.02"
                        />
                    </linearGradient>
                    <clipPath id="chartClip">
                        <rect x={ML} y={MT} width={innerW} height={innerH} />
                    </clipPath>
                </defs>

                <!-- Grid lines + Y labels -->
                {#each yTicks as tick}
                    <line
                        x1={ML}
                        y1={tick.y}
                        x2={W - MR}
                        y2={tick.y}
                        stroke="hsl(var(--border))"
                        stroke-width="1"
                        opacity="0.6"
                    />
                    <text
                        x={ML - 6}
                        y={tick.y + 4}
                        text-anchor="end"
                        font-size={axisFontSize}
                        fill="hsl(var(--muted-foreground))"
                        >{abbrev(tick.val)}</text
                    >
                {/each}

                <!-- Area fill -->
                {#if areaPath}
                    <path
                        d={areaPath}
                        fill="url(#lineAreaGrad)"
                        clip-path="url(#chartClip)"
                    />
                {/if}

                <!-- Line -->
                {#if linePath}
                    <path
                        d={linePath}
                        fill="none"
                        stroke="hsl(var(--accent))"
                        stroke-width="2"
                        stroke-linejoin="round"
                        stroke-linecap="round"
                        clip-path="url(#chartClip)"
                    />
                {/if}

                <!-- X labels -->
                {#each xTicks as tick}
                    <text
                        x={tick.x}
                        y={H - 4}
                        text-anchor="middle"
                        font-size={axisFontSize}
                        fill="hsl(var(--muted-foreground))">{tick.label}</text
                    >
                {/each}

                <!-- Hover elements -->
                {#if hoverIdx >= 0}
                    <line
                        x1={hoverX}
                        y1={MT}
                        x2={hoverX}
                        y2={MT + innerH}
                        stroke="hsl(var(--muted-foreground))"
                        stroke-width="1"
                        stroke-dasharray="3,3"
                        opacity="0.7"
                    />
                    <circle
                        cx={hoverX}
                        cy={hoverY}
                        r="4"
                        fill="hsl(var(--accent))"
                        stroke="hsl(var(--background))"
                        stroke-width="2"
                    />
                    <!-- Tooltip box -->
                    {@const tx = tooltipRight
                        ? hoverX - tooltipHorizontalOffset
                        : hoverX + 8}
                    {@const ty = Math.max(MT + 4, hoverY - tooltipYOffset)}
                    <rect
                        x={tx}
                        y={ty}
                        width={tooltipWidth}
                        height={tooltipHeight}
                        rx="5"
                        ry="5"
                        fill="hsl(var(--card))"
                        stroke="hsl(var(--border))"
                        stroke-width="1"
                    />
                    <text
                        x={tx + tooltipPaddingX}
                        y={ty + tooltipTitleY}
                        font-size={tooltipTitleFontSize}
                        fill="hsl(var(--muted-foreground))"
                        >{data[hoverIdx].name}</text
                    >
                    <text
                        x={tx + tooltipPaddingX}
                        y={ty + tooltipValueY}
                        font-size={tooltipValueFontSize}
                        font-weight="600"
                        fill="hsl(var(--foreground))"
                        >{formatCurrency(data[hoverIdx].value, currency)}</text
                    >
                {/if}
            </svg>
        </div>
    {/if}
</div>
