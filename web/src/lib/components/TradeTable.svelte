<script lang="ts">
  import Table from './Table.svelte'
  import Badge from './Badge.svelte'
  import { formatCurrency, formatDate, formatNumber } from '$lib/utils/format'

  export let trades: any[] = []
  export let loading = false

  const columns = [
    { key: 'ticker', label: 'Ticker', sortable: true },
    { key: 'trade_date', label: 'Date', sortable: true },
    { key: 'trade_type', label: 'Type', sortable: true },
    { key: 'quantity', label: 'Quantity', sortable: true },
    { key: 'price', label: 'Price', sortable: true },
    { key: 'total', label: 'Total', sortable: true }
  ]

  function getTradeTypeBadge(type: string) {
    const variants: Record<string, 'success' | 'danger' | 'info' | 'warning'> = {
      buy: 'info',
      sell: 'success',
      dividend: 'warning',
      fee: 'danger'
    }
    return variants[type] || 'default'
  }

  function handleSort(key: string) {
    trades = trades.sort((a, b) => {
      const aVal = a[key]
      const bVal = b[key]
      return aVal > bVal ? 1 : -1
    })
  }
</script>

<div>
  {#if loading}
    <div class="text-center py-8 text-gray-500">Loading trades...</div>
  {:else}
    <Table {columns} rows={trades} onSort={handleSort}>
      <svelte:fragment slot="cell-trade_type" let:row>
        <Badge variant={getTradeTypeBadge(row.trade_type)}>
          {row.trade_type.toUpperCase()}
        </Badge>
      </svelte:fragment>

      <svelte:fragment slot="cell-trade_date" let:row>
        {formatDate(row.trade_date)}
      </svelte:fragment>

      <svelte:fragment slot="cell-quantity" let:row>
        {formatNumber(row.quantity)}
      </svelte:fragment>

      <svelte:fragment slot="cell-price" let:row>
        {formatCurrency(row.price, row.trade_currency)}
      </svelte:fragment>

      <svelte:fragment slot="cell-total" let:row>
        {formatCurrency(row.quantity * row.price, row.trade_currency)}
      </svelte:fragment>
    </Table>
  {/if}
</div>
