<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import TradeTable from '$lib/components/TradeTable.svelte'
  import Button from '$lib/components/Button.svelte'
  import Modal from '$lib/components/Modal.svelte'
  import TradeForm from '$lib/components/TradeForm.svelte'
  import Select from '$lib/components/Select.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { TradeController } from '$lib/api/controllers'
  import type { CreateTradeRequest, Trade } from '$lib/api/types'
  import { onMount } from 'svelte'

  let loading = true
  let trades: Trade[] = []
  let showNewModal = false
  let showEditModal = false
  let editingTrade: any = null
  let tradeTypeFilter = 'all'
  let tradeController: TradeController

  const tradeTypeOptions = [
    { label: 'All Types', value: 'all' },
    { label: 'Buy', value: 'buy' },
    { label: 'Sell', value: 'sell' },
    { label: 'Dividend', value: 'dividend' },
    { label: 'Fee', value: 'fee' }
  ]

  onMount(async () => {
    tradeController = new TradeController(api.getInstance())
    if ($currentPortfolio) await loadTrades()
  })

  $: if ($currentPortfolio && tradeController) loadTrades()

  async function loadTrades() {
    try {
      loading = true
      const response = await tradeController.listTrades({
        portfolio_id: $currentPortfolio.id,
        limit: 500
      })
      trades = (response.data as Trade[]) || []
    } catch (e) {
      console.error('Failed to load trades:', e)
    } finally {
      loading = false
    }
  }

  async function handleCreateTrade(trade: any) {
    try {
      const tradeRequest: CreateTradeRequest = {
        portfolio_id: $currentPortfolio.id,
        ticker: trade.ticker,
        trade_type: trade.trade_type,
        trade_date: trade.trade_date,
        quantity: parseFloat(trade.quantity),
        price: parseFloat(trade.price),
        trade_currency: trade.trade_currency,
        fees: parseFloat(trade.fees) || 0,
      }
      await tradeController.createTrade(tradeRequest)
      await loadTrades()
      showNewModal = false
    } catch (e) {
      console.error('Failed to create trade:', e)
    }
  }

  function handleEditTrade(row: any) {
    editingTrade = {
      id: row.id,
      ticker: row.ticker,
      trade_type: row.trade_type,
      trade_date: row.trade_date.slice(0, 16),
      quantity: String(row.quantity),
      price: String(row.price),
      trade_currency: row.trade_currency,
      fees: String(row.fees ?? 0),
    }
    showEditModal = true
  }

  async function handleUpdateTrade(trade: any) {
    try {
      const tradeRequest: CreateTradeRequest = {
        portfolio_id: $currentPortfolio.id,
        ticker: trade.ticker,
        trade_type: trade.trade_type,
        trade_date: trade.trade_date,
        quantity: parseFloat(trade.quantity),
        price: parseFloat(trade.price),
        trade_currency: trade.trade_currency,
        fees: parseFloat(trade.fees) || 0,
      }
      await tradeController.updateTrade(editingTrade.id, tradeRequest)
      await loadTrades()
      showEditModal = false
      editingTrade = null
    } catch (e) {
      console.error('Failed to update trade:', e)
    }
  }

  async function handleDeleteTrade(tradeId: string) {
    if (!confirm('Delete this trade? This cannot be undone.')) return
    try {
      await tradeController.deleteTrade(tradeId)
      await loadTrades()
    } catch (e) {
      console.error('Failed to delete trade:', e)
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
          <TradeTable
            trades={filteredTrades}
            on:edit={(e) => handleEditTrade(e.detail)}
            on:delete={(e) => handleDeleteTrade(e.detail)}
          />
        </div>
      </Card>
    {/if}
  </div>
</div>

<!-- New Trade Modal -->
<Modal
  open={showNewModal}
  title="Create Trade"
  onClose={() => (showNewModal = false)}
>
  <TradeForm
    on:submit={(e) => handleCreateTrade(e.detail)}
    trade={{
      ticker: '',
      trade_type: 'buy',
      trade_date: new Date().toISOString().slice(0, 16),
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

<!-- Edit Trade Modal -->
{#if editingTrade}
  <Modal
    open={showEditModal}
    title="Edit Trade"
    onClose={() => { showEditModal = false; editingTrade = null }}
  >
    <TradeForm
      on:submit={(e) => handleUpdateTrade(e.detail)}
      trade={editingTrade}
    />
    <svelte:fragment slot="footer">
      <Button variant="outline" on:click={() => { showEditModal = false; editingTrade = null }}>
        Cancel
      </Button>
    </svelte:fragment>
  </Modal>
{/if}
