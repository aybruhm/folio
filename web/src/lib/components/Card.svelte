<script lang="ts">
  export let title: string = ''
  export let subtitle: string = ''
</script>

<div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-800">
  {#if title}
    <div class="mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
        {title}
      </h3>
      {#if subtitle}
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {subtitle}
        </p>
      {/if}
    </div>
  {/if}

  <slot />
</div>
