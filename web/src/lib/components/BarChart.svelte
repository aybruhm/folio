<script lang="ts">
  export let data: { label: string; value: number }[] = []
  export let title: string = ''
  export let color: string = '#3b82f6'
  export let height: string = 'h-80'

  $: maxValue = Math.max(...data.map(d => d.value), 0)
</script>

<div class="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
  {#if title}
    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
  {/if}

  {#if data.length === 0}
    <div class="flex items-center justify-center {height} text-gray-500">
      No data available
    </div>
  {:else}
    <div class={`flex items-end gap-4 ${height} justify-around p-4`}>
      {#each data as item}
        <div class="flex flex-col items-center gap-2 flex-1">
          <div class="relative w-full h-full flex items-end justify-center">
            <div
              class="w-full rounded-t transition-all"
              style="background-color: {color}; height: {maxValue > 0 ? (item.value / maxValue) * 100 : 0}%"
            />
          </div>
          <span class="text-xs text-gray-600 dark:text-gray-400 text-center truncate w-full">
            {item.label}
          </span>
          <span class="text-xs font-semibold text-gray-900 dark:text-white">
            {item.value.toFixed(2)}
          </span>
        </div>
      {/each}
    </div>
  {/if}
</div>
