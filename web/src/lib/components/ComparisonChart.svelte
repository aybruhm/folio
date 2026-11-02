<script lang="ts">
    // Two cumulative-return lines (percent), both starting at 0, so the gap
    // between them is the story. Hover or touch shows both values on a date.
    export let series: { date: string; portfolio: number; benchmark: number }[] = [];
    export let portfolioLabel = "Your portfolio";
    export let benchmarkLabel = "Benchmark";
    export let height = 300;

    const MARGIN = { top: 12, right: 14, bottom: 28, left: 52 };
    const PORTFOLIO_COLOR = "hsl(var(--accent))";
    const BENCHMARK_COLOR = "#60a5fa";

    let width = 640;
    let hoverIndex: number | null = null;

    $: innerW = Math.max(width - MARGIN.left - MARGIN.right, 10);
    $: innerH = height - MARGIN.top - MARGIN.bottom;

    // Zero is always in view: it is where both lines start.
    $: values = series.flatMap((s) => [s.portfolio, s.benchmark]).concat(0);
    $: lowest = Math.min(...values);
    $: highest = Math.max(...values);
    $: pad = (highest - lowest) * 0.08 || 1;
    $: yMin = lowest - pad;
    $: yMax = highest + pad;

    // Reactive declarations, not plain functions: a template call like x(i) only
    // re-runs when its arguments change, so a function reading `width` inside
    // would keep drawing at the old width after the chart is resized.
    $: x = (i: number): number =>
        series.length <= 1
            ? MARGIN.left + innerW / 2
            : MARGIN.left + (i / (series.length - 1)) * innerW;

    $: y = (value: number): number =>
        MARGIN.top + innerH - ((value - yMin) / (yMax - yMin)) * innerH;

    $: path = (key: "portfolio" | "benchmark"): string =>
        series
            .map((point, i) => `${i === 0 ? "M" : "L"} ${x(i)},${y(point[key])}`)
            .join(" ");

    // Round tick spacing (1, 2, 5, 10, 20, 50 ...) giving about five labels.
    function niceStep(range: number): number {
        const raw = range / 4;
        const magnitude = 10 ** Math.floor(Math.log10(raw));
        const fraction = raw / magnitude;
        return (fraction < 1.5 ? 1 : fraction < 3 ? 2 : fraction < 7 ? 5 : 10) * magnitude;
    }

    $: yTicks = (() => {
        const step = niceStep(yMax - yMin);
        const ticks: number[] = [];
        for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) {
            ticks.push(Math.round(v * 1e6) / 1e6);
        }
        return ticks;
    })();

    function parse(date: string): Date {
        return new Date(`${date}T00:00:00`);
    }

    $: spansYears =
        series.length > 1 &&
        (parse(series[series.length - 1].date).getTime() -
            parse(series[0].date).getTime()) /
            86_400_000 >
            400;

    function dateLabel(date: string): string {
        return parse(date).toLocaleDateString("en-GB", spansYears
            ? { month: "short", year: "numeric" }
            : { day: "numeric", month: "short" });
    }

    $: xTicks = (() => {
        const count = Math.min(width < 480 ? 3 : 5, series.length);
        if (count < 2) return series.length ? [0] : [];
        return Array.from({ length: count }, (_, k) =>
            Math.round((k / (count - 1)) * (series.length - 1)),
        );
    })();

    function percent(value: number, digits = 1): string {
        return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
    }

    function move(event: PointerEvent) {
        const box = (event.currentTarget as SVGElement).getBoundingClientRect();
        const fraction = (event.clientX - box.left - MARGIN.left) / innerW;
        hoverIndex = Math.round(
            Math.min(1, Math.max(0, fraction)) * (series.length - 1),
        );
    }

    $: hovered = hoverIndex === null ? null : series[hoverIndex];
    $: last = series[series.length - 1];
</script>

<div class="relative w-full" bind:clientWidth={width}>
    {#if series.length < 2}
        <p class="py-16 text-center text-sm text-muted-foreground">
            Not enough data points to draw a chart yet.
        </p>
    {:else}
        <svg
            {width}
            {height}
            role="img"
            aria-label="Cumulative return: {portfolioLabel} {percent(last.portfolio)}, {benchmarkLabel} {percent(last.benchmark)}"
            class="touch-pan-y select-none"
            on:pointermove={move}
            on:pointerdown={move}
            on:pointerleave={() => (hoverIndex = null)}
        >
            {#each yTicks as tick}
                <line
                    x1={MARGIN.left}
                    x2={width - MARGIN.right}
                    y1={y(tick)}
                    y2={y(tick)}
                    class="stroke-border"
                    stroke-dasharray={tick === 0 ? "0" : "3 4"}
                    stroke-width={tick === 0 ? 1.25 : 1}
                    opacity={tick === 0 ? 1 : 0.7}
                />
                <text
                    x={MARGIN.left - 8}
                    y={y(tick) + 4}
                    text-anchor="end"
                    class="fill-muted-foreground"
                    font-size="11">{percent(tick, 0)}</text
                >
            {/each}

            {#each xTicks as i}
                <text
                    x={x(i)}
                    y={height - 8}
                    text-anchor={i === 0 ? "start" : i === series.length - 1 ? "end" : "middle"}
                    class="fill-muted-foreground"
                    font-size="11">{dateLabel(series[i].date)}</text
                >
            {/each}

            <path d={path("benchmark")} fill="none" stroke={BENCHMARK_COLOR} stroke-width="2" stroke-linejoin="round" />
            <path d={path("portfolio")} fill="none" stroke={PORTFOLIO_COLOR} stroke-width="2.5" stroke-linejoin="round" />

            {#if hoverIndex !== null && hovered}
                <line
                    x1={x(hoverIndex)}
                    x2={x(hoverIndex)}
                    y1={MARGIN.top}
                    y2={MARGIN.top + innerH}
                    class="stroke-muted-foreground"
                    stroke-dasharray="3 3"
                />
                <circle cx={x(hoverIndex)} cy={y(hovered.benchmark)} r="4" fill={BENCHMARK_COLOR} />
                <circle cx={x(hoverIndex)} cy={y(hovered.portfolio)} r="4.5" fill={PORTFOLIO_COLOR} />
            {/if}
        </svg>

        {#if hoverIndex !== null && hovered}
            <div
                class="pointer-events-none absolute top-2 z-10 rounded-md border border-border bg-card px-3 py-2 text-xs shadow-md"
                style="left: {Math.min(Math.max(x(hoverIndex) + 12, 8), width - 190)}px"
            >
                <p class="mb-1 font-medium text-foreground">{parse(hovered.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</p>
                <p class="flex items-center gap-2 text-foreground">
                    <span class="h-2 w-2 rounded-full" style="background: {PORTFOLIO_COLOR}"></span>
                    {portfolioLabel}
                    <span class="ml-auto font-mono">{percent(hovered.portfolio, 2)}</span>
                </p>
                <p class="flex items-center gap-2 text-foreground">
                    <span class="h-2 w-2 rounded-full" style="background: {BENCHMARK_COLOR}"></span>
                    {benchmarkLabel}
                    <span class="ml-auto font-mono">{percent(hovered.benchmark, 2)}</span>
                </p>
            </div>
        {/if}

        <div class="mt-2 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
            <span class="flex items-center gap-2">
                <span class="h-0.5 w-5 rounded" style="background: {PORTFOLIO_COLOR}"></span>
                {portfolioLabel}
            </span>
            <span class="flex items-center gap-2">
                <span class="h-0.5 w-5 rounded" style="background: {BENCHMARK_COLOR}"></span>
                {benchmarkLabel}
            </span>
        </div>
    {/if}
</div>
