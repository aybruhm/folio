<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let title: string = ''
  export let subtitle: string = ''
  export let className: string = ''
</script>

<div class={cn('rounded-lg border border-border bg-card p-4 md:p-6 shadow-sm', className)}>
  {#if title}
    <div class="mb-3 md:mb-4">
      <h3 class="text-base md:text-lg font-semibold text-card-foreground">
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

