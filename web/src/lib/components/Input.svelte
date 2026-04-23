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
  export let step: string = ''

  let input: HTMLInputElement
</script>

<div class="flex flex-col gap-2">
  {#if label}
    <label for={label} class="text-xs md:text-sm font-medium text-foreground">
      {label}
      {#if required}
        <span class="text-destructive">*</span>
      {/if}
    </label>
  {/if}

  {#if type === 'datetime-local'}
    <input
      bind:this={input}
      bind:value
      type="datetime-local"
      {placeholder}
      {disabled}
      {required}
      class={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        error ? 'border-destructive' : '',
        className
      )}
      on:change
      on:blur
    />
  {:else if type === 'date'}
    <input
      bind:this={input}
      bind:value
      type="date"
      {placeholder}
      {disabled}
      {required}
      class={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        error ? 'border-destructive' : '',
        className
      )}
      on:change
      on:blur
    />
  {:else if type === 'number'}
    <input
      bind:this={input}
      bind:value
      type="number"
      {placeholder}
      {disabled}
      {required}
      {step}
      class={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        error ? 'border-destructive' : '',
        className
      )}
      on:change
      on:blur
    />
  {:else}
    <input
      bind:this={input}
      bind:value
      type="text"
      {placeholder}
      {disabled}
      {required}
      class={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        error ? 'border-destructive' : '',
        className
      )}
      on:change
      on:blur
    />
  {/if}

  {#if error}
    <span class="text-xs text-destructive">{error}</span>
  {/if}
</div>

