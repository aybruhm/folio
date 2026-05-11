<script lang="ts">
  import Badge from './Badge.svelte'
  import { formatCurrency, formatDateTime, formatNumber } from '$lib/utils/format'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher()

  export let trades: any[] = []
  export let loading = false
  export let selectedIds: Set<string> = new Set()

  const columns = [
    { key: 'ticker', label: 'Ticker', sortable: true },
    { key: 'trade_date', label: 'Date & Time', sortable: true },
    { key: 'trade_type', label: 'Type', sortable: true },
    { key: 'quantity', label: 'Quantity', sortable: true },
    { key: 'price', label: 'Price', sortable: true },
    { key: 'total', label: 'Total', sortable: true },
    { key: 'actions', label: '', sortable: false }
  ]

  let sortKey: string | null = null
  let sortDesc = false
  let selectAll = false

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

  function toggleSelectAll() {
    if (selectAll) {
      selectedIds.clear()
      trades.forEach(t => selectedIds.add(t.id))
    } else {
      selectedIds.clear()
    }
    selectedIds = selectedIds
  }

  function toggleSelect(tradeId: string) {
    if (selectedIds.has(tradeId)) {
      selectedIds.delete(tradeId)
    } else {
      selectedIds.add(tradeId)
    }
    selectedIds = selectedIds
    selectAll = trades.length > 0 && trades.every(t => selectedIds.has(t.id))
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
            <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-12">
              <input
                type="checkbox"
                bind:checked={selectAll}
                on:change={toggleSelectAll}
                class="cursor-pointer"
                title="Select all trades"
              />
            </th>
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
          {#each trades as row (row.id)}
            <tr class="border-b border-border hover:bg-muted/50 transition-colors">
              <td class="p-4 align-middle w-12">
                <input
                  type="checkbox"
                  checked={selectedIds.has(row.id)}
                  on:change={() => toggleSelect(row.id)}
                  class="cursor-pointer"
                />
              </td>
              <td class="p-4 align-middle">{row.ticker}</td>
              <td class="p-4 align-middle">{formatDateTime(row.trade_date)}</td>
              <td class="p-4 align-middle">
                <Badge variant={getTradeTypeBadge(row.trade_type)}>
                  {row.trade_type.toUpperCase()}
                </Badge>
              </td>
              <td class="p-4 align-middle">{formatNumber(row.quantity, 4)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.price, row.trade_currency)}</td>
              <td class="p-4 align-middle">{formatCurrency(row.quantity * row.price, row.trade_currency)}</td>
              <td class="p-4 align-middle">
                <div class="flex gap-2">
                  <button
                    on:click={() => dispatch('edit', row)}
                    class="text-muted-foreground hover:text-foreground transition-colors"
                    title="Edit trade"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    on:click={() => dispatch('delete', row.id)}
                    class="text-muted-foreground hover:text-destructive transition-colors"
                    title="Delete trade"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
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
