<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let title: string = ''
  export let subtitle: string = ''
  export let className: string = ''
  export let variant: 'default' | 'stat' = 'default'
</script>

<div class={cn(
  'rounded-xl border bg-card p-3 sm:p-4 md:p-6 transition-shadow hover:shadow-lg',
  variant === 'stat' ? 'border-border/60' : 'border-border shadow-sm',
  className
)}>
  {#if title}
    <div class="mb-3 md:mb-4">
      <h3 class="text-sm font-semibold tracking-tight text-card-foreground">
        {title}
      </h3>
      {#if subtitle}
        <p class="mt-0.5 text-xs text-muted-foreground">
          {subtitle}
        </p>
      {/if}
    </div>
  {/if}

  <slot />
</div>
