<script lang="ts">
  export let data: { label: string; value: number }[] = []
  export let title: string = ''
  export let colors: string[] = [
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#8b5cf6',
    '#ec4899'
  ]

  $: total = data.reduce((sum, d) => sum + d.value, 0)
  $: items = data.map((d, i) => ({
    ...d,
    percentage: (d.value / total) * 100,
    color: colors[i % colors.length]
  }))

  function getSlicePath(startAngle: number, endAngle: number): string {
    const radius = 80
    const innerRadius = 50
    const startRad = (startAngle * Math.PI) / 180
    const endRad = (endAngle * Math.PI) / 180

    const x1 = 100 + radius * Math.cos(startRad)
    const y1 = 100 + radius * Math.sin(startRad)
    const x2 = 100 + radius * Math.cos(endRad)
    const y2 = 100 + radius * Math.sin(endRad)

    const ix1 = 100 + innerRadius * Math.cos(startRad)
    const iy1 = 100 + innerRadius * Math.sin(startRad)
    const ix2 = 100 + innerRadius * Math.cos(endRad)
    const iy2 = 100 + innerRadius * Math.sin(endRad)

    const largeArc = endAngle - startAngle > 180 ? 1 : 0

    return [
      `M ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
      `L ${ix2} ${iy2}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix1} ${iy1}`,
      'Z'
    ].join(' ')
  }

  let currentAngle = 0
  $: slices = items.map(item => {
    const startAngle = currentAngle
    const endAngle = currentAngle + (item.percentage / 100) * 360
    currentAngle = endAngle
    return {
      ...item,
      startAngle,
      endAngle,
      path: getSlicePath(startAngle, endAngle)
    }
  })
</script>

<div class="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
  {#if title}
    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
  {/if}

  {#if data.length === 0}
    <div class="flex items-center justify-center h-80 text-gray-500">
      No data available
    </div>
  {:else}
    <div class="flex gap-8">
      <div class="flex-shrink-0">
        <svg width="200" height="200" viewBox="0 0 200 200">
          {#each slices as slice}
            <path d={slice.path} fill={slice.color} opacity="0.8" />
          {/each}
        </svg>
      </div>

      <div class="flex flex-col justify-center gap-2">
        {#each items as item}
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full" style="background-color: {item.color}" />
            <span class="text-sm text-gray-700 dark:text-gray-300">
              {item.label}: {item.percentage.toFixed(1)}%
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
