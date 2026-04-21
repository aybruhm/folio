<script lang="ts">
  export let label: string = ''
  export let value: string = ''
  export let options: { label: string; value: string }[] = []
  export let error: string = ''
  export let required = false
  export let disabled = false
  export let placeholder: string = 'Select an option'
</script>

<div class="flex flex-col gap-2">
  {#if label}
    <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
      {label}
      {#if required}
        <span class="text-red-500">*</span>
      {/if}
    </label>
  {/if}

  <select
    bind:value
    {required}
    {disabled}
    class="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white dark:border-gray-700 {error
      ? 'border-red-500'
      : 'border-gray-300'}"
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
    <span class="text-sm text-red-500">{error}</span>
  {/if}
</div>
