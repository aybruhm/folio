<script lang="ts">
  import { cn } from '$lib/utils/cn'

  export let label: string = ''
  export let value: string = ''
  export let options: { label: string; value: string }[] = []
  export let error: string = ''
  export let required = false
  export let disabled = false
  export let placeholder: string = 'Select an option'
  export let className: string = ''
</script>

<div class="flex flex-col gap-2">
  {#if label}
    <label class="text-xs md:text-sm font-medium text-foreground">
      {label}
      {#if required}
        <span class="text-destructive">*</span>
      {/if}
    </label>
  {/if}

  <select
    bind:value
    {required}
    {disabled}
    class={cn(
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      error ? 'border-destructive' : '',
      className
    )}
    on:change
  >
    {#if !value}
      <option value="" disabled selected>{placeholder}</option>
    {/if}
    {#each options as opt}
      <option value={opt.value}>{opt.label}</option>
    {/each}
  </select>

  {#if error}
    <span class="text-xs text-destructive">{error}</span>
  {/if}
</div>

