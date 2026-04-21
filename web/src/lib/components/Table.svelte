<script lang="ts">
  export let columns: { key: string; label: string; sortable?: boolean }[] = []
  export let rows: Record<string, unknown>[] = []
  export let onSort: ((key: string) => void) | null = null

  let sortKey: string | null = null
  let sortDesc = false

  function handleSort(key: string) {
    if (!onSort) return

    if (sortKey === key) {
      sortDesc = !sortDesc
    } else {
      sortKey = key
      sortDesc = false
    }

    onSort(key)
  }
</script>

<div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
  <table class="w-full">
    <thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <tr>
        {#each columns as col}
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            {#if col.sortable}
              <button
                on:click={() => handleSort(col.key)}
                class="flex items-center gap-2 hover:text-gray-900 dark:hover:text-white"
              >
                {col.label}
                {#if sortKey === col.key}
                  <span>{sortDesc ? '↓' : '↑'}</span>
                {/if}
              </button>
            {:else}
              {col.label}
            {/if}
          </th>
        {/each}
      </tr>
    </thead>

    <tbody>
      {#each rows as row, i}
        <tr class="border-b border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
          {#each columns as col}
            <td class="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
              <slot name={`cell-${col.key}`} {row}>
                {row[col.key]}
              </slot>
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>

  {#if rows.length === 0}
    <div class="text-center py-8 text-gray-500 dark:text-gray-400">
      No data available
    </div>
  {/if}
</div>
