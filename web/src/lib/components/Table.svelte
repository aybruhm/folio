<script lang="ts">
  import { cn } from '$lib/utils/cn'

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

<div class="w-full overflow-auto rounded-md border border-border">
  <table class="w-full text-sm">
    <thead class="border-b border-border bg-muted">
      <tr>
        {#each columns as col}
          <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
            {#if col.sortable}
              <button
                on:click={() => handleSort(col.key)}
                class="flex items-center gap-2 hover:text-foreground"
              >
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
      {#each rows as row, i}
        <tr class="border-b border-border hover:bg-muted/50 transition-colors data-[state=selected]:bg-muted">
          {#each columns as col}
            <td class="p-4 align-middle [&:has([role=checkbox])]:pr-0">
              {row[col.key]}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>

  {#if rows.length === 0}
    <div class="flex h-24 items-center justify-center text-muted-foreground">
      <p>No data available</p>
    </div>
  {/if}
</div>

