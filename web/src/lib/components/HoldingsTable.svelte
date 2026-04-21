<script lang="ts">
  import Table from './Table.svelte'
  import Badge from './Badge.svelte'
  import { formatCurrency, formatNumber, formatPercent } from '$lib/utils/format'

  export let holdings: any[] = []
  export let loading = false
  export let onSelectHolding: (ticker: string) => void = () => {}

  const columns = [
    { key: 'ticker', label: 'Ticker', sortable: true },
    { key: 'quantity', label: 'Quantity', sortable: true },
    { key: 'average_cost', label: 'Avg Cost', sortable: true },
    { key: 'current_price', label: 'Current Price', sortable: true },
    { key: 'current_value', label: 'Current Value', sortable: true },
    { key: 'gain_loss', label: 'Gain/Loss', sortable: true },
    { key: 'return_pct', label: 'Return %', sortable: true }
  ]

  function getReturnBadge(returnPct: number) {
    if (returnPct > 0) return 'success'
    if (returnPct < 0) return 'danger'
    return 'default'
  }

  function handleSort(key: string) {
    holdings = holdings.sort((a, b) => {
      const aVal = a[key]
      const bVal = b[key]
      return aVal > bVal ? 1 : -1
    })
  }
</script>

<div>
  {#if loading}
    <div class="text-center py-8 text-gray-500">Loading holdings...</div>
  {:else}
    <Table {columns} rows={holdings} onSort={handleSort}>
      <svelte:fragment slot="cell-average_cost" let:row>
        {formatCurrency(row.average_cost, row.currency)}
      </svelte:fragment>

      <svelte:fragment slot="cell-current_price" let:row>
        {formatCurrency(row.current_price, row.currency)}
      </svelte:fragment>

      <svelte:fragment slot="cell-current_value" let:row>
        {formatCurrency(row.current_value, row.currency)}
      </svelte:fragment>

      <svelte:fragment slot="cell-gain_loss" let:row>
        <Badge variant={getReturnBadge(row.gain_loss)}>
          {formatCurrency(row.gain_loss, row.currency)}
        </Badge>
      </svelte:fragment>

      <svelte:fragment slot="cell-return_pct" let:row>
        <Badge variant={getReturnBadge(row.return_pct)}>
          {formatPercent(row.return_pct)}
        </Badge>
      </svelte:fragment>

      <svelte:fragment slot="cell-ticker" let:row>
        <button on:click={() => onSelectHolding(row.ticker)} class="text-blue-600 hover:underline dark:text-blue-400">
          {row.ticker}
        </button>
      </svelte:fragment>
    </Table>
  {/if}
</div>
