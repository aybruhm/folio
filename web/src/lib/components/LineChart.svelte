<script lang="ts">
  import { formatCurrency } from '$lib/utils/format'

  export let data: { name: string; value: number }[] = []
  export let title: string = ''
  export let height: string = 'h-80'
  export let currency: string = 'USD'

  $: maxValue = Math.max(...data.map(d => d.value), 0)
  $: minValue = Math.min(...data.map(d => d.value), 0)
  $: range = maxValue - minValue || 1

  function scaleY(value: number): string {
    return `${((value - minValue) / range) * 100}%`
  }
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
    <div class={`relative ${height}`}>
      <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 300">
        <!-- Grid lines -->
        {#each { length: 5 } as _, i}
          <line
            x1="0"
            y1={(i / 4) * 300}
            x2="1000"
            y2={(i / 4) * 300}
            stroke="currentColor"
            stroke-width="1"
            opacity="0.1"
            class="text-gray-400"
          />
        {/each}

        <!-- Data line -->
        {#if data.length > 1}
          <polyline
            points={data
              .map((d, i) => `${(i / (data.length - 1)) * 1000},${300 - parseFloat(scaleY(d.value)) * 3}`)
              .join(' ')}
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            class="text-blue-600"
          />
        {/if}

        <!-- Data points -->
        {#each data as d, i}
          <circle
            cx={(i / (data.length - 1)) * 1000}
            cy={300 - parseFloat(scaleY(d.value)) * 3}
            r="6"
            fill="currentColor"
            class="text-blue-600"
          />
        {/each}
      </svg>

      <!-- Tooltip on hover -->
      <div class="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-gray-600 dark:text-gray-400 mt-2">
        <span>{data[0]?.name}</span>
        <span>{data[data.length - 1]?.name}</span>
      </div>
    </div>
  {/if}
</div>
