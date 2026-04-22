<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import LineChart from '$lib/components/LineChart.svelte'
  import DonutChart from '$lib/components/DonutChart.svelte'
  import Button from '$lib/components/Button.svelte'
  import Badge from '$lib/components/Badge.svelte'
  import { formatCurrency, formatPercent } from '$lib/utils/format'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { onMount } from 'svelte'

  let loading = true
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

      <!-- Action Buttons -->
      <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button variant="default" href="/trades/new">
          <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Trade
        </Button>
        <Button variant="outline" href="/portfolios">
          Manage Portfolios
        </Button>
        <Button variant="outline" href="/analytics">
          View Analytics
        </Button>
      </div>
    {/if}
  </div>
</div>
