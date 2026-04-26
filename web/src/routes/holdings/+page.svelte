<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import HoldingsTable from '$lib/components/HoldingsTable.svelte'
  import Button from '$lib/components/Button.svelte'
  import Input from '$lib/components/Input.svelte'
  import Modal from '$lib/components/Modal.svelte'
  import TradeForm from '$lib/components/TradeForm.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { PortfolioController, TradeController } from '$lib/api/controllers'
  import type { CreateTradeRequest, Holding } from '$lib/api/types'
  import { onMount } from 'svelte'

  let loading = true
  let holdings: Holding[] = []
  let searchTerm = ''
  let filteredHoldings: Holding[] = []
  let portfolioController: PortfolioController
  let tradeController: TradeController
  let showNewModal = false

  onMount(async () => {
    portfolioController = new PortfolioController(api.getInstance())
    tradeController = new TradeController(api.getInstance())
    if ($currentPortfolio) await loadHoldings()
  })

  $: if ($currentPortfolio && portfolioController) loadHoldings()

  async function loadHoldings() {
    try {
      loading = true
      const response = await portfolioController.getHoldings({
        portfolio_id: $currentPortfolio.id
      })
      holdings = (response.data || []).map((h: any) => ({
        ticker: h.ticker,
        quantity: h.quantity,
        average_cost: h.avg_price,
        current_price: h.current_price,
        current_value: h.total_value,
        gain_loss: h.gain_loss,
        return_pct: h.gain_loss_percent,
        currency: response.currency ?? 'USD'
      }))
      filterHoldings()
    } catch (e) {
      console.error('Failed to load holdings:', e)
    } finally {
      loading = false
    }
  }

  function filterHoldings() {
    if (!searchTerm) {
      filteredHoldings = holdings
    } else {
      const term = searchTerm.toLowerCase()
      filteredHoldings = holdings.filter(h =>
        h.ticker.toLowerCase().includes(term)
      )
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
        asset_class: trade.asset_class || undefined,
      }
      await tradeController.createTrade(tradeRequest)
      await loadHoldings()
      showNewModal = false
    } catch (e) {
      console.error('Failed to create trade:', e)
    }
  }

  async function handleDeleteHolding(ticker: string) {
    if (!confirm(`Delete all trades for ${ticker}? This cannot be undone.`)) return
    try {
      const response = await tradeController.listTrades({
        portfolio_id: $currentPortfolio.id,
        ticker,
        limit: 1000,
      })
      const tradesForTicker = (response.data as any[]) || []
      await Promise.all(tradesForTicker.map((t: any) => tradeController.deleteTrade(t.id)))
      await loadHoldings()
    } catch (e) {
      console.error('Failed to delete holding:', e)
    }
  }

  $: searchTerm, filterHoldings()
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center">
      <div class="space-y-2">
        <h1 class="text-2xl md:text-3xl font-bold text-foreground">Holdings</h1>
        <p class="text-xs md:text-sm text-muted-foreground">Current positions in {$currentPortfolio?.name}</p>
      </div>
      <Button variant="default" on:click={() => (showNewModal = true)} class="w-full sm:w-auto">
        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Trade
      </Button>
    </div>

    <!-- Search -->
    <Card>
      <Input
        label="Search holdings"
        placeholder="Search by ticker (e.g., AAPL)"
        bind:value={searchTerm}
      />
    </Card>

    <!-- Holdings Table -->
    {#if loading}
      <div class="flex justify-center py-12">
        <div class="text-muted-foreground">Loading holdings...</div>
      </div>
    {:else if filteredHoldings.length === 0}
      <Card title="No holdings" subtitle="Create a trade to add holdings to your portfolio">
        <div class="py-8 text-center">
          <p class="mb-4 text-muted-foreground">
            You don't have any positions yet.
          </p>
          <Button variant="default" on:click={() => (showNewModal = true)}>
            Create First Trade
          </Button>
        </div>
      </Card>
    {:else}
      <Card title="Portfolio Holdings">
        <div class="overflow-x-auto -mx-4 md:mx-0">
          <HoldingsTable
            holdings={filteredHoldings}
            on:deleteHolding={(e) => handleDeleteHolding(e.detail)}
          />
        </div>
      </Card>
    {/if}
  </div>
</div>

<!-- Add Trade Modal -->
<Modal
  open={showNewModal}
  title="Add Trade"
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
