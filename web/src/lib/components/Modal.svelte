<script lang="ts">
  import { cn } from '$lib/utils/cn'
  import Button from './Button.svelte'

  export let open = false
  export let title: string = ''
  export let onClose: () => void = () => {}

  function handleEscKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose()
    }
  }
</script>

<svelte:window on:keydown={handleEscKey} />

{#if open}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-background/80 backdrop-blur-sm sm:items-center">
    <div
      class="relative w-full overflow-hidden rounded-t-xl border border-border bg-card shadow-lg sm:max-w-lg sm:rounded-lg"
      role="dialog"
      aria-labelledby="modal-title"
    >
      <div class="flex items-center justify-between border-b border-border p-4 md:p-6">
        <h2 id="modal-title" class="text-lg font-semibold text-card-foreground">
          {title}
        </h2>
        <Button variant="ghost" size="icon" on:click={onClose} class="h-8 w-8">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </Button>
      </div>

      <div class="max-h-[70vh] overflow-y-auto p-4 md:p-6">
        <slot />
      </div>

      <div class="flex justify-end gap-3 border-t border-border p-4 md:p-6">
        <slot name="footer" />
      </div>
    </div>
  </div>
{/if}

