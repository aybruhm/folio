<script lang="ts">
  export let open = false
  export let title: string = ''
  export let onClose: () => void = () => {}

  function handleBackdropClick() {
    onClose()
  }

  function handleEscKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose()
    }
  }
</script>

<svelte:window on:keydown={handleEscKey} />

{#if open}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-900 rounded-lg shadow-lg max-w-md w-full mx-4">
      <div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-800">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
          {title}
        </h2>
        <button
          on:click={onClose}
          class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div class="p-6">
        <slot />
      </div>

      <div class="flex gap-3 p-6 border-t border-gray-200 dark:border-gray-800 justify-end">
        <slot name="footer" />
      </div>
    </div>
  </div>
{/if}
