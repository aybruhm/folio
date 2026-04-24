<script lang="ts">
  import Input from './Input.svelte'
  import Select from './Select.svelte'
  import Button from './Button.svelte'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher()

  export let trade: {
    ticker: string
    trade_type: string
    trade_date: string
    quantity: string
    price: string
    trade_currency: string
    fees: string
  } = {
    ticker: '',
    trade_type: 'buy',
    trade_date: new Date().toISOString().slice(0, 16),
    quantity: '',
    price: '',
    trade_currency: 'USD',
    fees: '0'
  }
  export let isLoading = false

  const tradeTypes = [
    { label: 'Buy', value: 'buy' },
    { label: 'Sell', value: 'sell' },
    { label: 'Dividend', value: 'dividend' },
    { label: 'Fee', value: 'fee' }
  ]

  const currencies = [
    { label: 'USD', value: 'USD' },
    { label: 'GBP', value: 'GBP' },
    { label: 'EUR', value: 'EUR' },
    { label: 'JPY', value: 'JPY' }
  ]

  let errors: Record<string, string> = {}

  async function handleSubmit() {
    errors = {}

    if (!trade.ticker) errors.ticker = 'Ticker is required'
    if (!trade.quantity) errors.quantity = 'Quantity is required'
    if (!trade.price) errors.price = 'Price is required'

    if (Object.keys(errors).length > 0) return

    try {
      dispatch('submit', trade)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'An error occurred'
      errors.submit = message
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-4">
  <Input
    label="Ticker"
    placeholder="AAPL"
    bind:value={trade.ticker}
    required
    error={errors.ticker}
  />

  <Select
    label="Trade Type"
    bind:value={trade.trade_type}
    options={tradeTypes}
    required
  />

  <Input
    label="Trade Date & Time"
    type="datetime-local"
    bind:value={trade.trade_date}
    required
    error={errors.trade_date}
  />

  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <Input
      label="Quantity"
      type="number"
      step="0.001"
      placeholder="100"
      bind:value={trade.quantity}
      required
      error={errors.quantity}
    />

    <Input
      label="Price"
      type="number"
      step="0.01"
      placeholder="150.00"
      bind:value={trade.price}
      required
      error={errors.price}
    />
  </div>

  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <Select
      label="Currency"
      bind:value={trade.trade_currency}
      options={currencies}
    />

    <Input
      label="Fees"
      type="number"
      step="0.01"
      placeholder="0.00"
      bind:value={trade.fees}
    />
  </div>

  {#if errors.submit}
    <div class="text-red-600 dark:text-red-400 text-sm">{errors.submit}</div>
  {/if}

  <div class="flex gap-3">
    <Button type="submit" variant="default" disabled={isLoading}>
      {isLoading ? 'Saving...' : 'Save Trade'}
    </Button>
  </div>
</form>
