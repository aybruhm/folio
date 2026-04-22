<script lang="ts">
  import Badge from './Badge.svelte'
  import { formatCurrency, formatDateTime, formatNumber } from '$lib/utils/format'

  export let trades: any[] = []
  export let loading = false

  const columns = [
    { key: 'ticker', label: 'Ticker', sortable: true },
    { key: 'trade_date', label: 'Date & Time', sortable: true },
    { key: 'trade_type', label: 'Type', sortable: true },
    { key: 'quantity', label: 'Quantity', sortable: true },
    { key: 'price', label: 'Price', sortable: true },
    { key: 'total', label: 'Total', sortable: true }
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
    trades = [...trades].sort((a, b) => {
      const aVal = a[key]
      const bVal = b[key]
      return sortDesc ? (aVal > bVal ? -1 : 1) : (aVal > bVal ? 1 : -1)
    })
  }

  function getTradeTypeBadge(type: string): 'success' | 'danger' | 'info' | 'warning' | 'default' {
    const variants: Record<string, 'success' | 'danger' | 'info' | 'warning'> = {
      buy: 'info',
      sell: 'success',
      dividend: 'warning',
      fee: 'danger'
    }
    return variants[type] || 'default'
  }
</script>

<div>
  {#if loading}
    <div class="text-center py-8 text-gray-500">Loading trades...</div>
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
          {#each trades as row}
            <tr class="border-b border-border hover:bg-muted/50 transition-colors">
              <td class="p-4 align-middle">{row.ticker}</td>
              <td class="p-4 align-middle">{formatDateTime(row.trade_date)}</td>
              <td class="p-4 align-middle">
                <Badge variant={getTradeTypeBadge(row.trade_type)}>
                  {row.trade_type.toUpperCase()}
                </Badge>
              </td>
              <td class="p-4 align-middle">{formatNumber(row.quantity)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.price, row.trade_currency)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.quantity * row.price, row.trade_currency)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      {#if trades.length === 0}
        <div class="flex h-24 items-center justify-center text-muted-foreground">
          <p>No trades available</p>
        </div>
      {/if}
    </div>
  {/if}
</div>
