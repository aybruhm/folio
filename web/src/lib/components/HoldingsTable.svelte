<script lang="ts">
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

  let sortKey: string | null = null
  let sortDesc = false

  function handleSort(key: string) {
    if (sortKey === key) {
      sortDesc = !sortDesc
    } else {
      sortKey = key
      sortDesc = false
    }
    holdings = [...holdings].sort((a, b) => {
      const aVal = a[key]
      const bVal = b[key]
      return sortDesc ? (aVal > bVal ? -1 : 1) : (aVal > bVal ? 1 : -1)
    })
  }

  function getReturnBadge(val: number): 'success' | 'danger' | 'default' {
    if (val > 0) return 'success'
    if (val < 0) return 'danger'
    return 'default'
  }
</script>

<div>
  {#if loading}
    <div class="text-center py-8 text-gray-500">Loading holdings...</div>
  {:else}
    <div class="w-full overflow-auto rounded-md border border-border">
      <table class="w-full text-sm">
        <thead class="border-b border-border bg-muted">
          <tr>
            {#each columns as col}
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
                {#if col.sortable}
                  <button on:click={() => handleSort(col.key)} class="flex items-center gap-2 hover:text-foreground">
                    {col.label}
                    {#if sortKey === col.key}
                      <span class="text-xs">{sortDesc ? '↓' : '↑'}</span>
                    {/if}
                  </button>
                {:else}
                  {col.label}
                {/if}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="[&_tr:last-child]:border-0">
          {#each holdings as row}
            <tr class="border-b border-border hover:bg-muted/50 transition-colors">
              <td class="p-4 align-middle">
                <button on:click={() => onSelectHolding(row.ticker)} class="text-blue-600 hover:underline dark:text-blue-400">
                  {row.ticker}
                </button>
              </td>
              <td class="p-4 align-middle">{formatNumber(row.quantity)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.average_cost, row.currency)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.current_price, row.currency)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.current_value, row.currency)}</td>
              <td class="p-4 align-middle">
                <Badge variant={getReturnBadge(row.gain_loss)}>
                  {formatCurrency(row.gain_loss, row.currency)}
                </Badge>
              </td>
              <td class="p-4 align-middle">
                <Badge variant={getReturnBadge(row.return_pct)}>
                  {formatPercent(row.return_pct)}
                </Badge>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      {#if holdings.length === 0}
        <div class="flex h-24 items-center justify-center text-muted-foreground">
          <p>No holdings available</p>
        </div>
      {/if}
    </div>
  {/if}
</div>
