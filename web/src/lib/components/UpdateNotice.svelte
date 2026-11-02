<script lang="ts">
  import { availableUpdate, dismissUpdate } from '#lib/stores/updateNotice.js'
  import { releaseUrl, toTag } from '#lib/utils/version.js'
</script>

{#if $availableUpdate}
  <div
    class="relative mb-2 rounded-xl border border-border bg-background/60 p-3 shadow-sm"
    role="status"
  >
    <button
      type="button"
      class="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      aria-label="Dismiss update notice"
      title="Dismiss"
      on:click={dismissUpdate}
    >
      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <div class="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.75"
          d="M12 8v13m0-13a4 4 0 10-4-4m4 4a4 4 0 114-4M4 12h16v9H4v-9zm-1-4h18v4H3V8z"
        />
      </svg>
    </div>

    <p class="text-xs font-semibold text-foreground">Update available</p>
    <p class="mt-0.5 text-[11px] leading-snug text-muted-foreground">
      {toTag($availableUpdate.tag)} is now available with new features and improvements.
    </p>
    <a
      href={releaseUrl($availableUpdate.tag)}
      target="_blank"
      rel="noopener noreferrer"
      class="mt-2 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
    >
      View release notes
      <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
      </svg>
    </a>
  </div>
{/if}
