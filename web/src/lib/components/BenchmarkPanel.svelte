<script lang="ts">
    import { onMount } from "svelte";
    import Button from "./Button.svelte";
    import Skeleton from "./Skeleton.svelte";
    import ComparisonChart from "./ComparisonChart.svelte";
    import { api } from "#lib/api/client.js";
    import { AssetController, PortfolioController } from "#lib/api/controllers/index.js";
    import type {
        BenchmarkComparisonQuery,
        BenchmarkComparisonResponse,
        BenchmarkOption,
        BenchmarkPeriod,
        BenchmarkProvider,
    } from "#lib/api/types/index.js";
    import { getCachedBenchmark, setCachedBenchmark } from "#lib/cache/index.js";
    import { authUser } from "#lib/stores/index.js";
    import { formatPercent } from "#lib/utils/format.js";

    // One portfolio, or null for all of them together, shown in `currency`.
    export let portfolioId: string | null = null;
    export let currency = "USD";
    export let scopeLabel = "All portfolios";

    const PERIODS: { value: BenchmarkPeriod; label: string; description: string }[] = [
        { value: "ytd", label: "YTD", description: "Year to date" },
        { value: "3m", label: "3M", description: "Last 3 months" },
        { value: "6m", label: "6M", description: "Last 6 months" },
        { value: "1y", label: "1Y", description: "Last year" },
        { value: "3y", label: "3Y", description: "Last 3 years" },
        { value: "5y", label: "5Y", description: "Last 5 years" },
        { value: "10y", label: "10Y", description: "Last 10 years" },
    ];
    // Where a typed-in ticker is looked up. Catalog entries know their own.
    const PROVIDERS: { value: BenchmarkProvider; label: string; example: string }[] = [
        { value: "yfinance", label: "Yahoo Finance", example: "e.g. MSFT, ^FTSE, SOL-USD" },
        { value: "ngxpulse", label: "NGXPulse", example: "e.g. ASI, NGX-30" },
        { value: "ngnmarket", label: "NGNMarket", example: "e.g. NGX30" },
    ];
    const CUSTOM = "__custom__";
    const STORAGE = {
        benchmark: "folio.benchmark",
        custom: "folio.benchmarkCustom",
        period: "folio.benchmarkPeriod",
        provider: "folio.benchmarkProvider",
    };

    function remembered(key: string, fallback: string): string {
        try {
            return localStorage.getItem(key) || fallback;
        } catch {
            return fallback;
        }
    }

    let catalog: BenchmarkOption[] = [];
    let selected = remembered(STORAGE.benchmark, "^GSPC");
    let customInput = remembered(STORAGE.custom, "");
    // The custom ticker actually being compared; it only changes on Compare, so
    // typing doesn't send a request per keystroke.
    let appliedCustom = selected === CUSTOM ? customInput.trim().toUpperCase() : "";
    let period = remembered(STORAGE.period, "1y") as BenchmarkPeriod;
    let customProvider = remembered(STORAGE.provider, "yfinance") as BenchmarkProvider;

    let portfolioController: PortfolioController | null = null;
    let result: BenchmarkComparisonResponse | null = null;
    let loading = true;
    let error: string | null = null;
    // An older response must not replace a newer one.
    let requestId = 0;

    $: ticker = selected === CUSTOM ? appliedCustom : selected;
    $: categories = [...new Set(catalog.map((b) => b.category))];
    // Only a typed-in ticker names its provider; the API knows the catalog's.
    $: provider = selected === CUSTOM ? customProvider : null;
    $: providerExample =
        PROVIDERS.find((p) => p.value === customProvider)?.example ?? "";
    $: if (portfolioController && ticker) {
        void run(ticker, period, portfolioId, currency, provider);
    }
    $: if (portfolioController && !ticker) {
        loading = false;
        result = null;
    }
    $: periodLabel = PERIODS.find((p) => p.value === period)?.description ?? "";

    onMount(async () => {
        portfolioController = new PortfolioController(api.getInstance());
        try {
            catalog = await new AssetController(api.getInstance()).listBenchmarks();
        } catch {
            // The catalog is a convenience: a custom ticker still works.
        }
    });

    function remember() {
        try {
            localStorage.setItem(STORAGE.benchmark, selected);
            localStorage.setItem(STORAGE.custom, customInput);
            localStorage.setItem(STORAGE.period, period);
            localStorage.setItem(STORAGE.provider, customProvider);
        } catch {
            // not remembered, no harm
        }
    }

    async function run(
        symbol: string,
        forPeriod: BenchmarkPeriod,
        forPortfolio: string | null,
        forCurrency: string,
        forProvider: BenchmarkProvider | null,
    ) {
        if (!portfolioController) return;
        const id = ++requestId;
        loading = true;
        error = null;
        const query: BenchmarkComparisonQuery = {
            benchmark: symbol,
            period: forPeriod,
            in_currency: forCurrency,
            portfolio_id: forPortfolio,
            provider: forProvider,
        };
        const userId = $authUser?.id;
        try {
            const cached = userId ? await getCachedBenchmark(userId, query) : null;
            if (id !== requestId) return;
            if (cached) {
                result = cached;
                return;
            }
            const data = await portfolioController.getBenchmarkComparison(query);
            if (id !== requestId) return;
            result = data;
            if (userId) void setCachedBenchmark(userId, query, data);
        } catch (e) {
            if (id !== requestId) return;
            result = null;
            error =
                e instanceof Error && e.message
                    ? e.message
                    : "Couldn't load the comparison. Try again.";
        } finally {
            if (id === requestId) loading = false;
        }
    }

    function choosePeriod(value: BenchmarkPeriod) {
        period = value;
        remember();
    }

    function chooseBenchmark() {
        remember();
        if (selected === CUSTOM) applyCustom();
    }

    function chooseProvider() {
        remember();
    }

    function applyCustom() {
        appliedCustom = customInput.trim().toUpperCase();
        remember();
    }

    function retry() {
        if (ticker) void run(ticker, period, portfolioId, currency, provider);
    }

    function day(iso: string): string {
        return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
        });
    }

    function points(value: number): string {
        return Math.abs(value).toFixed(2);
    }

    function clock(iso: string): string {
        return new Date(iso).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    $: verdict =
        result === null
            ? null
            : result.excess_return_pct > 0
              ? "ahead"
              : result.excess_return_pct < 0
                ? "behind"
                : "level";
    const selectClass =
        "h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
</script>

<div class="space-y-5">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="flex flex-1 flex-col gap-3 sm:flex-row sm:items-end">
            <label class="block flex-1 text-xs font-medium text-foreground md:text-sm">
                Compare {scopeLabel} against
                <select
                    class="{selectClass} mt-2"
                    bind:value={selected}
                    on:change={chooseBenchmark}
                    aria-label="Benchmark"
                >
                    {#each categories as category}
                        <optgroup label={category}>
                            {#each catalog.filter((b) => b.category === category) as option}
                                <option value={option.ticker}>{option.name} ({option.ticker})</option>
                            {/each}
                        </optgroup>
                    {/each}
                    {#if catalog.length === 0 && selected !== CUSTOM}
                        <option value={selected}>{selected}</option>
                    {/if}
                    <option value={CUSTOM}>Other ticker…</option>
                </select>
            </label>

            {#if selected === CUSTOM}
                <form
                    class="flex flex-1 gap-2"
                    on:submit|preventDefault={applyCustom}
                >
                    <select
                        class="{selectClass} w-auto shrink-0"
                        bind:value={customProvider}
                        on:change={chooseProvider}
                        aria-label="Where to look the ticker up"
                    >
                        {#each PROVIDERS as option}
                            <option value={option.value}>{option.label}</option>
                        {/each}
                    </select>
                    <input
                        class="{selectClass} uppercase placeholder:normal-case"
                        bind:value={customInput}
                        placeholder={providerExample}
                        aria-label="Custom benchmark ticker"
                        autocomplete="off"
                        spellcheck="false"
                    />
                    <Button
                        type="submit"
                        variant="outline"
                        disabled={!customInput.trim() || loading}>Compare</Button
                    >
                </form>
            {/if}
        </div>

        <div class="self-start lg:self-auto">
            <span class="block text-xs font-medium text-foreground md:text-sm">Period</span>
            <div
                class="mt-2 inline-flex h-10 items-center rounded-md border border-input bg-background p-1"
                role="group"
                aria-label="Period"
            >
                {#each PERIODS as option}
                    <button
                        type="button"
                        class="h-full rounded px-2.5 text-xs font-medium transition-colors {period === option.value
                            ? 'bg-muted text-foreground'
                            : 'text-muted-foreground hover:text-foreground'}"
                        aria-pressed={period === option.value}
                        title={option.description}
                        on:click={() => choosePeriod(option.value)}
                    >
                        {option.label}
                    </button>
                {/each}
            </div>
        </div>
    </div>

    {#if !ticker}
        <p class="py-12 text-center text-sm text-muted-foreground">
            Enter a ticker to compare against. Yahoo Finance covers stocks, ETFs,
            indices and crypto; NGXPulse and NGNMarket cover Nigerian indices.
        </p>
    {:else if loading}
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {#each Array(3) as _}
                <div class="rounded-xl border border-border p-4">
                    <Skeleton className="h-3 w-24 mb-3" />
                    <Skeleton className="h-8 w-28" />
                </div>
            {/each}
        </div>
        <Skeleton className="h-72 w-full" />
    {:else if error}
        <div class="py-10 text-center" role="alert">
            <p class="mb-1 font-medium text-foreground">Couldn't compare</p>
            <p class="mx-auto mb-5 max-w-md text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" on:click={retry}>Try again</Button>
        </div>
    {:else if result}
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div class="rounded-xl border border-border bg-card p-4">
                <p class="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                    {scopeLabel}
                </p>
                <p
                    class="font-serif text-3xl leading-none {result.portfolio.return_pct >= 0 ? 'text-positive' : 'text-negative'}"
                >
                    {formatPercent(result.portfolio.return_pct)}
                </p>
                <p class="mt-2 text-xs text-muted-foreground">
                    {#if result.portfolio.annualized_pct !== null}
                        {formatPercent(result.portfolio.annualized_pct)} a year
                    {:else}
                        {periodLabel}
                    {/if}
                </p>
            </div>

            <div class="rounded-xl border border-border bg-card p-4">
                <p class="mb-2 truncate text-[10px] font-semibold uppercase tracking-widest text-muted-foreground" title={result.benchmark.name}>
                    {result.benchmark.name}
                </p>
                <p
                    class="font-serif text-3xl leading-none {result.benchmark.return_pct >= 0 ? 'text-positive' : 'text-negative'}"
                >
                    {formatPercent(result.benchmark.return_pct)}
                </p>
                <p class="mt-2 text-xs text-muted-foreground">
                    {#if result.benchmark.annualized_pct !== null}
                        {formatPercent(result.benchmark.annualized_pct)} a year
                    {:else}
                        {result.benchmark.ticker}
                    {/if}
                </p>
            </div>

            <div class="rounded-xl border border-border bg-card p-4">
                <p class="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Difference
                </p>
                <p
                    class="font-serif text-3xl leading-none {verdict === 'ahead'
                        ? 'text-positive'
                        : verdict === 'behind'
                          ? 'text-negative'
                          : 'text-foreground'}"
                >
                    {#if verdict === "level"}
                        In line
                    {:else}
                        {verdict === "ahead" ? "+" : "−"}{points(result.excess_return_pct)}
                    {/if}
                </p>
                <p class="mt-2 text-xs text-muted-foreground">
                    {#if verdict === "ahead"}
                        percentage points ahead of {result.benchmark.name}
                    {:else if verdict === "behind"}
                        percentage points behind {result.benchmark.name}
                    {:else}
                        the same return as {result.benchmark.name}
                    {/if}
                </p>
            </div>
        </div>

        <ComparisonChart
            series={result.series}
            portfolioLabel={scopeLabel}
            benchmarkLabel={result.benchmark.name}
        />

        <div class="space-y-1.5 text-xs text-muted-foreground">
            <p>
                {day(result.start_date)} to {day(result.end_date)}, in {result.currency}.
                {#if result.limited_by === "portfolio"}
                    Your first trade was after the {periodLabel.toLowerCase()} window began
                    ({day(result.requested_start)}), so the comparison starts there.
                {:else if result.limited_by === "benchmark"}
                    {result.benchmark.name} has no prices before this date, so the
                    comparison starts here.
                {/if}
            </p>
            {#if !result.benchmark.converted}
                <p class="text-amber-700 dark:text-amber-400">
                    {result.benchmark.name} is priced in {result.benchmark.quote_currency} and no
                    exchange rate was available, so its return is in
                    {result.benchmark.quote_currency}, not {result.currency}.
                </p>
            {/if}
            {#if result.excluded_portfolio_ids.length > 0}
                <p class="text-amber-700 dark:text-amber-400">
                    {result.excluded_portfolio_ids.length === 1
                        ? "1 portfolio is"
                        : `${result.excluded_portfolio_ids.length} portfolios are`} left out:
                    no exchange rate to {result.currency} right now.
                </p>
            {/if}
            <p>
                Prices from {PROVIDERS.find((p) => p.value === result?.benchmark.provider)?.label ?? "Yahoo Finance"},
                updated {clock(result.generated_at)}. Results are kept for 35 minutes.
            </p>
            <p>
                Returns are time-weighted: money you add or withdraw isn't counted as
                gain or loss. Index figures are price returns.
            </p>
        </div>
    {/if}
</div>
