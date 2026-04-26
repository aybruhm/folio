<script lang="ts">
  import Input from './Input.svelte'
  import Select from './Select.svelte'
  import Button from './Button.svelte'

  export let goal: {
    name: string
    target_amount: string
    target_date: string
    expected_annual_return: string
    description: string
  } = {
    name: '',
    target_amount: '',
    target_date: '',
    expected_annual_return: '0.07',
    description: ''
  }
  export let onSubmit: (data: typeof goal) => Promise<void> = async () => {}
  export let isLoading = false

  let errors: Record<string, string> = {}

  async function handleSubmit() {
    errors = {}

    if (!goal.name) errors.name = 'Goal name is required'
    if (!goal.target_amount) errors.target_amount = 'Target amount is required'
    if (!goal.target_date) errors.target_date = 'Target date is required'
    if (!goal.expected_annual_return) errors.expected_annual_return = 'Expected return is required'

    if (Object.keys(errors).length > 0) return

    try {
      await onSubmit(goal)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'An error occurred'
      errors.submit = message
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
  <Input
    label="Goal Name"
    placeholder="Retirement Fund"
    bind:value={goal.name}
    required
    error={errors.name}
  />

  <Input
    label="Target Amount"
    type="number"
    step="1000"
    placeholder="1000000"
    bind:value={goal.target_amount}
    required
    error={errors.target_amount}
  />

  <Input
    label="Target Date"
    type="date"
    bind:value={goal.target_date}
    required
    error={errors.target_date}
  />

  <Input
    label="Expected Annual Return (%)"
    type="number"
    step="0.1"
    min="0"
    placeholder="7.0"
    bind:value={goal.expected_annual_return}
    required
    error={errors.expected_annual_return}
  />

  <Input
    label="Description"
    placeholder="Optional notes about this goal"
    bind:value={goal.description}
  />

  {#if errors.submit}
    <div class="text-red-600 dark:text-red-400 text-sm">{errors.submit}</div>
  {/if}

  <div class="flex gap-3">
    <Button type="submit" variant="default" disabled={isLoading}>
      {isLoading ? 'Saving...' : 'Save Goal'}
    </Button>
  </div>
</form>
