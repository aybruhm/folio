<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import LineChart from '$lib/components/LineChart.svelte'
  import DonutChart from '$lib/components/DonutChart.svelte'
  import Button from '$lib/components/Button.svelte'
  import Badge from '$lib/components/Badge.svelte'
  import TradeForm from '$lib/components/TradeForm.svelte'
  import { formatCurrency, formatPercent } from '$lib/utils/format'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { onMount } from 'svelte'

  let loading = true
  let fabOpen = false
  let showTradeModal = false
  let stats = {
    totalValue: '0',
    totalCostBasis: '0',
    gainLoss: '0',
    gainLossPercent: '0',
    portfolioAllocation: [] as { label: string; value: number }[],
    performanceHistory: [] as { name: string; value: number }[],
    topHoldings: [] as { ticker: string; value: string; percent: string }[]
  }

  $: topHoldingsChart = stats.topHoldings.map(h => ({
    label: h.ticker,
    value: parseFloat(h.percent)
  }))

  onMount(async () => {
    if ($currentPortfolio) await loadDashboardData()
  })

  $: if ($currentPortfolio) loadDashboardData()

  async function loadDashboardData() {
    try {
      loading = true
      const data = await api.get(`/portfolios/${$currentPortfolio.id}`)

      stats = {
        totalValue: data.current_value || '0',
        totalCostBasis: data.cost_basis || '0',
        gainLoss: data.gain_loss || '0',
        gainLossPercent: data.return_percent || '0',
        portfolioAllocation: data.allocation || [],
        performanceHistory: data.performance_history || [],
        topHoldings: data.top_holdings || []
      }
    } catch (e) {
      console.error('Failed to load dashboard data:', e)
    } finally {
      loading = false
    }
  }

  async function handleCreateTrade(event: CustomEvent) {
    const trade = event.detail
    try {
      await api.post(`/portfolios/${$currentPortfolio.id}/trades`, {
        ticker: trade.ticker,
        trade_type: trade.trade_type,
        trade_date: trade.trade_date,
        quantity: parseFloat(trade.quantity),
        price: parseFloat(trade.price),
        trade_currency: trade.trade_currency,
        fees: parseFloat(trade.fees) || 0,
      })
      showTradeModal = false
      fabOpen = false
      await loadDashboardData()
    } catch (e) {
      console.error('Failed to create trade:', e)
    }
  }


  $: isPositive = Number(stats.gainLoss) >= 0
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-7xl space-y-6">
    <!-- Header -->
    <div class="space-y-2">
      <h1 class="text-2xl md:text-3xl font-bold text-foreground">Dashboard</h1>
      <p class="text-xs md:text-sm text-muted-foreground">
        {#if $currentPortfolio}
          <span>{$currentPortfolio.name}</span>
          {#if $currentPortfolio.description}
            <span class="text-xs">· {$currentPortfolio.description}</span>
          {/if}
        {/if}
      </p>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <div class="text-muted-foreground">Loading portfolio data...</div>
      </div>
    {:else}
      <!-- Stats Cards -->
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <Card title="Total Value" subtitle="Current portfolio value">
          <div class="text-3xl font-bold text-foreground">
            {formatCurrency(stats.totalValue)}
          </div>
        </Card>

        <Card title="Cost Basis" subtitle="Total amount invested">
          <div class="text-3xl font-bold text-foreground">
            {formatCurrency(stats.totalCostBasis)}
          </div>
        </Card>

        <Card title="Gain/Loss" subtitle="Unrealized P&L">
          <div
            class="text-3xl font-bold"
            class:text-positive={isPositive}
            class:text-negative={!isPositive}
          >
            {formatCurrency(stats.gainLoss)}
          </div>
        </Card>

        <Card title="Return" subtitle="Total return %">
          <div
            class="text-3xl font-bold"
            class:text-positive={isPositive}
            class:text-negative={!isPositive}
          >
            {formatPercent(stats.gainLossPercent)}
          </div>
        </Card>
      </div>

      <!-- Charts Section -->
      <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-3">
        <div class="lg:col-span-2">
          <Card title="Performance" subtitle="Portfolio value over time">
            <LineChart
              data={stats.performanceHistory}
              title=""
              height="h-80 md:h-96"
            />
          </Card>
        </div>

        <div>
          <Card title="Allocation" subtitle="Asset class breakdown">
            <DonutChart
              data={stats.portfolioAllocation}
              title=""
            />
          </Card>
        </div>
      </div>

      <!-- Top Holdings -->
      <Card title="Top Holdings" subtitle="5 largest positions">
        <div class="space-y-2 md:space-y-3">
          {#each stats.topHoldings as holding}
            <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between rounded-lg border border-border p-3 md:p-4">
              <div class="flex flex-col gap-1">
                <span class="text-sm md:text-base font-semibold text-foreground">{holding.ticker}</span>
                <span class="text-xs md:text-sm text-muted-foreground">
                  {formatPercent(holding.percent)} of portfolio
                </span>
              </div>
              <div class="text-left md:text-right">
                <div class="text-sm md:text-base font-semibold text-foreground">
                  {formatCurrency(holding.value)}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </Card>

      <!-- Allocation + Top Holdings (side by side) -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Allocation" subtitle="Asset class breakdown">
          <DonutChart data={stats.portfolioAllocation} />
        </Card>

        <Card title="Top Holdings" subtitle="5 largest positions by portfolio weight">
          <DonutChart data={topHoldingsChart} />
        </Card>
      </div>
    {/if}
  </div>
</div>

<!-- Floating Action Button -->
<div class="fixed bottom-6 right-6 z-30 flex flex-col-reverse gap-2">
  {#if fabOpen}
    <a
      href="/trades/new"
      class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
      title="New Trade"
    >
      <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
      </svg>
    </a>
    <a
      href="/portfolios"
      class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
      title="Manage Portfolios"
    >
      <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </a>
    <a
      href="/analytics"
      class="h-10 w-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
      title="View Analytics"
    >
      <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    </a>
  {/if}
  
  <button
    on:click={() => fabOpen = !fabOpen}
    class="h-10 w-10 rounded-full bg-accent text-accent-foreground flex items-center justify-center hover:bg-accent/90 transition-all {fabOpen ? 'rotate-45' : ''}"
    title="Actions"
  >
    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
    </svg>
  </button>
</div>

<!-- Trade Modal -->
{#if showTradeModal}
  <div class="fixed inset-0 z-40 bg-black/50 flex items-end sm:items-center justify-center" on:click={() => showTradeModal = false}>
    <div class="bg-card rounded-t-lg sm:rounded-lg w-full sm:max-w-md p-6 space-y-4" on:click|stopPropagation>
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Add Trade</h2>
        <button on:click={() => showTradeModal = false} class="text-muted-foreground hover:text-foreground">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <TradeForm on:submit={handleCreateTrade} />
    </div>
  </div>
{/if}
