<script lang="ts">
  import Input from './Input.svelte'
  import Select from './Select.svelte'
  import Button from './Button.svelte'

  export let portfolio: { name: string; base_currency: string; description: string } = {
    name: '',
    base_currency: 'USD',
    description: ''
  }
  export let onSubmit: (data: typeof portfolio) => Promise<void> = async () => {}
  export let isLoading = false

  const currencies = [
    { label: 'USD', value: 'USD' },
    { label: 'GBP', value: 'GBP' },
    { label: 'EUR', value: 'EUR' },
    { label: 'JPY', value: 'JPY' }
  ]

  let errors: Record<string, string> = {}

  async function handleSubmit() {
    errors = {}

    if (!portfolio.name) {
      errors.name = 'Portfolio name is required'
    }

    if (Object.keys(errors).length > 0) {
      return
    }

    try {
      await onSubmit(portfolio)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'An error occurred'
      errors.submit = message
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
  <Input
    label="Portfolio Name"
    placeholder="My Investment Portfolio"
    bind:value={portfolio.name}
    required
    error={errors.name}
  />

  <Select
    label="Base Currency"
    bind:value={portfolio.base_currency}
    options={currencies}
    required
  />

  <Input
    label="Description"
    placeholder="Optional description"
    bind:value={portfolio.description}
    error={errors.description}
  />

  {#if errors.submit}
    <div class="text-red-600 dark:text-red-400 text-sm">{errors.submit}</div>
  {/if}

  <div class="flex gap-3">
    <Button type="submit" variant="primary" disabled={isLoading}>
      {isLoading ? 'Saving...' : 'Save Portfolio'}
    </Button>
  </div>
</form>
