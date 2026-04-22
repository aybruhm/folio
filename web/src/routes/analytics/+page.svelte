<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import LineChart from '$lib/components/LineChart.svelte'
  import BarChart from '$lib/components/BarChart.svelte'
  import DonutChart from '$lib/components/DonutChart.svelte'
  import Select from '$lib/components/Select.svelte'
  import Badge from '$lib/components/Badge.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { formatPercent, formatCurrency } from '$lib/utils/format'
  import { onMount } from 'svelte'

  let loading = true
  let timeframe = '1y'
  let analyticsData: any = {
    twr: '0',
    mwr: '0',
    allocation: [],
    performance_history: [],
    contribution_history: [],
    sector_breakdown: []
  }

  const timeframeOptions = [
    { label: 'YTD', value: 'ytd' },
    { label: '3 Months', value: '3m' },
    { label: '1 Year', value: '1y' },
    { label: '3 Years', value: '3y' },
    { label: '5 Years', value: '5y' },
    { label: 'All Time', value: 'all' }
  ]

  onMount(async () => {
    if ($currentPortfolio) {
      await loadAnalytics()
    }
  })

  async function loadAnalytics() {
    try {
      loading = true
      const data = await api.get(`/portfolios/${$currentPortfolio.id}/analytics`, {
        timeframe
      })
      analyticsData = data || {}
    } catch (e) {
      console.error('Failed to load analytics:', e)
    } finally {
      loading = false
    }
  }

  $: if (timeframe) loadAnalytics()
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:gap-6 sm:items-center sm:justify-between">
      <div class="space-y-2">
        <h1 class="text-2xl md:text-3xl font-bold text-foreground">Analytics</h1>
        <p class="text-xs md:text-sm text-muted-foreground">Performance analysis for {$currentPortfolio?.name}</p>
      </div>
    </div>

    <!-- Timeframe Filter -->
    <Card>
      <Select
        label="Timeframe"
        bind:value={timeframe}
        options={timeframeOptions}
      />
    </Card>

    {#if loading}
      <div class="flex justify-center py-12">
        <div class="text-muted-foreground">Loading analytics...</div>
      </div>
    {:else}
      <!-- Metrics Cards -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Time-Weighted Return (TWR)" subtitle="Adjusted for cash flows">
          <div class="flex items-baseline gap-2">
            <div class="text-4xl font-bold text-accent">
              {formatPercent(analyticsData.twr)}
            </div>
            <Badge variant="default">
              Standard Measure
            </Badge>
          </div>
        </Card>

        <Card title="Money-Weighted Return (MWR)" subtitle="Including cash flow timing">
          <div class="flex items-baseline gap-2">
            <div class="text-4xl font-bold text-accent">
              {formatPercent(analyticsData.mwr)}
            </div>
            <Badge variant="secondary">
              IRR Method
            </Badge>
          </div>
        </Card>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
        <Card title="Performance History">
          <LineChart
            data={analyticsData.performance_history}
            title=""
            height="h-64 md:h-80"
          />
        </Card>

        <Card title="Contributions Over Time">
          <BarChart
            data={analyticsData.contribution_history}
            title=""
            height="h-64 md:h-80"
          />
        </Card>
      </div>

      <!-- Asset Allocation and Sector Breakdown -->
      <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-2">
        <Card title="Asset Allocation">
          <DonutChart
            data={analyticsData.allocation}
            title=""
          />
        </Card>

        <Card title="Sector Breakdown">
          <DonutChart
            data={analyticsData.sector_breakdown}
            title=""
          />
        </Card>
      </div>
    {/if}
  </div>
</div>
