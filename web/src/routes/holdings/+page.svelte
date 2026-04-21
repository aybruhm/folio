<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import HoldingsTable from '$lib/components/HoldingsTable.svelte'
  import Button from '$lib/components/Button.svelte'
  import Input from '$lib/components/Input.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { onMount } from 'svelte'

  let loading = true
  let holdings: any[] = []
  let searchTerm = ''
  let filteredHoldings: any[] = []

  onMount(async () => {
    if ($currentPortfolio) {
      await loadHoldings()
    }
  })

  async function loadHoldings() {
    try {
      loading = true
      const data = await api.get(`/portfolios/${$currentPortfolio.id}/holdings`)
      holdings = data || []
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

  function handleSelectHolding(ticker: string) {
    // Navigate to holding detail
  }

  $: searchTerm, filterHoldings()
</script>

<div class="min-h-screen bg-background p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold text-foreground">Holdings</h1>
        <p class="text-muted-foreground">Current positions in {$currentPortfolio?.name}</p>
      </div>
      <Button variant="default" href="/trades/new">
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
          <Button variant="default" href="/trades/new">
            Create First Trade
          </Button>
        </div>
      </Card>
    {:else}
      <Card title="Portfolio Holdings">
        <HoldingsTable
          holdings={filteredHoldings}
          onSelectHolding={handleSelectHolding}
        />
      </Card>
    {/if}
  </div>
</div>

<style>
  :global(.text-positive) {
    @apply text-positive;
  }

  :global(.text-negative) {
    @apply text-negative;
  }
</style>
