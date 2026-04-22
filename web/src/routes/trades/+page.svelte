<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import TradeTable from '$lib/components/TradeTable.svelte'
  import Button from '$lib/components/Button.svelte'
  import Modal from '$lib/components/Modal.svelte'
  import TradeForm from '$lib/components/TradeForm.svelte'
  import Select from '$lib/components/Select.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { onMount } from 'svelte'

  let loading = true
  let trades: any[] = []
  let showNewModal = false
  let tradeTypeFilter = 'all'

  const tradeTypeOptions = [
    { label: 'All Types', value: 'all' },
    { label: 'Buy', value: 'buy' },
    { label: 'Sell', value: 'sell' },
    { label: 'Dividend', value: 'dividend' },
    { label: 'Fee', value: 'fee' }
  ]

  onMount(async () => {
    if ($currentPortfolio) {
      await loadTrades()
    }
  })

  async function loadTrades() {
    try {
      loading = true
      const data = await api.get(`/portfolios/${$currentPortfolio.id}/trades`)
      trades = data || []
    } catch (e) {
      console.error('Failed to load trades:', e)
    } finally {
      loading = false
    }
  }

  async function handleCreateTrade(trade: any) {
    try {
      await api.post(`/portfolios/${$currentPortfolio.id}/trades`, trade)
      await loadTrades()
      showNewModal = false
    } catch (e) {
      console.error('Failed to create trade:', e)
    }
  }

  $: filteredTrades = tradeTypeFilter === 'all' 
    ? trades 
    : trades.filter(t => t.trade_type === tradeTypeFilter)
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center">
      <div class="space-y-2">
        <h1 class="text-2xl md:text-3xl font-bold text-foreground">Trades</h1>
        <p class="text-xs md:text-sm text-muted-foreground">Transaction history for {$currentPortfolio?.name}</p>
      </div>
      <Button variant="default" on:click={() => (showNewModal = true)} class="w-full sm:w-auto">
        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Trade
      </Button>
    </div>

    <!-- Filter -->
    <Card>
      <Select
        label="Filter by type"
        bind:value={tradeTypeFilter}
        options={tradeTypeOptions}
      />
    </Card>

    <!-- Trades Table -->
    {#if loading}
      <div class="flex justify-center py-12">
        <div class="text-muted-foreground">Loading trades...</div>
      </div>
    {:else if filteredTrades.length === 0}
      <Card title="No trades" subtitle="Create your first trade to track investments">
        <div class="py-8 text-center">
          <p class="mb-4 text-muted-foreground">
            {tradeTypeFilter === 'all' 
              ? "You don't have any trades yet." 
              : `No ${tradeTypeFilter} trades found.`}
          </p>
          <Button variant="default" on:click={() => (showNewModal = true)}>
            Create First Trade
          </Button>
        </div>
      </Card>
    {:else}
      <Card title="Trade History">
        <div class="overflow-x-auto -mx-4 md:mx-0">
          <TradeTable trades={filteredTrades} />
        </div>
      </Card>
    {/if}
  </div>
</div>

<Modal
  open={showNewModal}
  title="Create Trade"
  onClose={() => (showNewModal = false)}
>
  <TradeForm
    onSubmit={handleCreateTrade}
    trade={{
      ticker: '',
      trade_type: 'buy',
      trade_date: new Date().toISOString().split('T')[0],
      quantity: '',
      price: '',
      trade_currency: 'USD',
      fees: '0'
    }}
  />
  <svelte:fragment slot="footer">
    <Button variant="outline" on:click={() => (showNewModal = false)}>
      Cancel
    </Button>
  </svelte:fragment>
</Modal>
