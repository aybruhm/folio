<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let title: string = ''
  export let subtitle: string = ''
  export let className: string = ''
</script>

<div class={cn('rounded-lg border border-border bg-card p-4 shadow-sm md:p-6', className)}>
  {#if title}
    <div class="mb-4">
      <h3 class="text-lg font-semibold text-card-foreground">
        {title}
      </h3>
      {#if subtitle}
        <p class="mt-1 text-sm text-muted-foreground">
          {subtitle}
        </p>
      {/if}
    </div>
  {/if}

  <slot />
</div>

