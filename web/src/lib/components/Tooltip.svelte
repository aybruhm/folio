<script lang="ts">
  export let text: string = ''
  export let position: 'top' | 'bottom' | 'left' | 'right' = 'top'

  let showTooltip = false

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2'
  }
</script>

<div class="relative inline-block">
  <div
    on:mouseenter={() => (showTooltip = true)}
    on:mouseleave={() => (showTooltip = false)}
  >
    <slot />
  </div>

  {#if showTooltip && text}
    <div
      class="absolute bg-gray-900 dark:bg-gray-700 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10 {positionClasses[position]}"
    >
      {text}
    </div>
  {/if}
</div>
