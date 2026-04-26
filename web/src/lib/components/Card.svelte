<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let title: string = ''
  export let subtitle: string = ''
  export let className: string = ''
</script>

<div class={cn('rounded-lg border border-border bg-card p-3 sm:p-4 md:p-6 shadow-sm', className)}>
  {#if title}
    <div class="mb-2 md:mb-4">
      <h3 class="text-sm md:text-base font-semibold text-card-foreground">
        {title}
      </h3>
      {#if subtitle}
        <p class="mt-1 text-xs md:text-sm text-muted-foreground">
          {subtitle}
        </p>
      {/if}
    </div>
  {/if}

  <slot />
</div>

