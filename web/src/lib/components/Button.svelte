<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let variant: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' = 'default'
  export let size: 'default' | 'sm' | 'lg' | 'icon' = 'default'
  export let disabled = false
  export let type: 'button' | 'submit' | 'reset' = 'button'
  export let href: string | undefined = undefined
  let className = ''
  export { className as class }

  const baseClasses =
    'inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs sm:text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50'

  const variants = {
    default: 'bg-primary text-primary-foreground hover:bg-primary/90',
    destructive: 'bg-[#F87171]/15 text-[#F87171] border border-[#F87171]/30 hover:bg-[#F87171]/25',
    outline: 'border border-input bg-background hover:bg-muted hover:text-foreground',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    ghost: 'hover:bg-muted hover:text-foreground',
    link: 'text-primary underline-offset-4 hover:underline'
  }

  const sizes = {
    default: 'h-10 px-4 py-2',
    sm: 'h-9 rounded-md px-3 text-xs',
    lg: 'h-11 rounded-md px-8',
    icon: 'h-10 w-10'
  }

  $: buttonClasses = cn(baseClasses, variants[variant], sizes[size], className)
</script>

{#if href}
  <a {href} class={buttonClasses} {...$$restProps}>
    <slot />
  </a>
{:else}
  <button {type} {disabled} class={buttonClasses} on:click {...$$restProps}>
    <slot />
  </button>
{/if}

