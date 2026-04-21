<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let label: string = ''
  export let type: string = 'text'
  export let placeholder: string = ''
  export let value: string = ''
  export let error: string = ''
  export let required = false
  export let disabled = false
  export let className: string = ''

  let input: HTMLInputElement
</script>

<div class="flex flex-col gap-2">
  {#if label}
    <label for={label} class="text-sm font-medium text-foreground">
      {label}
      {#if required}
        <span class="text-destructive">*</span>
      {/if}
    </label>
  {/if}

  <input
    bind:this={input}
    bind:value
    {type}
    {placeholder}
    {disabled}
    {required}
    class={cn(
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      error ? 'border-destructive' : '',
      className
    )}
    on:change
    on:blur
  />

  {#if error}
    <span class="text-xs text-destructive">{error}</span>
  {/if}
</div>

