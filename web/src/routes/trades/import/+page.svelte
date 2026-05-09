<svelte:head>
    <title>Import Trades — Folio</title>
</svelte:head>

<script lang="ts">
  import { goto } from '$app/navigation'
  import Card from '$lib/components/Card.svelte'
  import Button from '$lib/components/Button.svelte'
  import Select from '$lib/components/Select.svelte'
  import Input from '$lib/components/Input.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { TradeController } from '$lib/api/controllers'
  import type { ValidateCsvResponse, ConfirmImportResponse } from '$lib/api/types'

  // ── wizard state ──────────────────────────────────────────────
  let step: 1 | 2 | 3 = 1
  let file: File | null = null
  let headers: string[] = []
  let sampleRows: Record<string, string>[] = []
  let dragOver = false

  // ── mapping state ─────────────────────────────────────────────
  const TRADE_FIELDS = [
    { key: 'ticker',         label: 'Ticker',          required: true,  hint: ''                             },
    { key: 'trade_type',     label: 'Trade Type',      required: true,  hint: 'buy, sell, dividend, fee'     },
    { key: 'trade_date',     label: 'Trade Date',      required: true,  hint: ''                             },
    { key: 'quantity',       label: 'Quantity',        required: true,  hint: ''                             },
    { key: 'price',          label: 'Price',           required: true,  hint: ''                             },
    { key: 'asset_class',    label: 'Asset Class',     required: false, hint: 'stock, etf, crypto, cash'     },
    { key: 'trade_currency', label: 'Currency',        required: false, hint: 'USD, GBP, EUR…'               },
    { key: 'fees',           label: 'Fees',            required: false, hint: ''                             },
    { key: 'notes',          label: 'Notes',           required: false, hint: ''                             },
  ]

  let mapping: Record<string, string> = {}
  let dateFormat = '%Y-%m-%d'

  const DATE_FORMAT_OPTIONS = [
    { label: 'YYYY-MM-DD  (e.g. 2024-01-31)', value: '%Y-%m-%d' },
    { label: 'DD/MM/YYYY  (e.g. 31/01/2024)', value: '%d/%m/%Y' },
    { label: 'MM/DD/YYYY  (e.g. 01/31/2024)', value: '%m/%d/%Y' },
    { label: 'YYYY/MM/DD  (e.g. 2024/01/31)', value: '%Y/%m/%d' },
    { label: 'Custom…',                        value: 'custom'   },
  ]
  let dateFormatPreset = '%Y-%m-%d'
  let customDateFormat = ''
  $: if (dateFormatPreset === 'custom') {
    dateFormat = customDateFormat
  } else {
    dateFormat = dateFormatPreset
  }

  // ── validate / confirm state ──────────────────────────────────
  let validation: ValidateCsvResponse | null = null
  let validating = false
  let importing = false
  let errorsExpanded = false
  let importResult: ConfirmImportResponse | null = null

  // ── helpers ───────────────────────────────────────────────────
  function parseCSVPreview(text: string) {
    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length === 0) return

    // simple split respecting quoted fields
    function splitLine(line: string): string[] {
      const result: string[] = []
      let cur = ''
      let inQuotes = false
      for (const ch of line) {
        if (ch === '"') { inQuotes = !inQuotes }
        else if (ch === ',' && !inQuotes) { result.push(cur.trim()); cur = '' }
        else cur += ch
      }
      result.push(cur.trim())
      return result
    }

    headers = splitLine(lines[0])
    sampleRows = lines.slice(1, 6).map(l => {
      const vals = splitLine(l)
      return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']))
    })

    // auto-map by fuzzy header name match
    mapping = {}
    for (const field of TRADE_FIELDS) {
      const match = headers.find(h =>
        h.toLowerCase().replace(/[^a-z]/g, '') ===
        field.key.toLowerCase().replace(/[^a-z]/g, '')
        || h.toLowerCase().includes(field.label.toLowerCase().split(' ')[0])
      )
      if (match) mapping[field.key] = match
    }
  }

  function onFileChange(e: Event) {
    const input = e.target as HTMLInputElement
    const f = input.files?.[0]
    if (!f) return
    loadFile(f)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    dragOver = false
    const f = e.dataTransfer?.files?.[0]
    if (f && f.name.endsWith('.csv')) loadFile(f)
  }

  function loadFile(f: File) {
    file = f
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      parseCSVPreview(text)
    }
    reader.readAsText(f)
  }

  $: headerOptions = [
    { label: '— skip —', value: '' },
    ...headers.map(h => ({ label: h, value: h })),
  ]

  $: canAdvanceStep1 = file !== null && headers.length > 0

  $: requiredMapped = TRADE_FIELDS
    .filter(f => f.required)
    .every(f => mapping[f.key])

  async function validate() {
    if (!file) return
    validating = true
    try {
      const controller = new TradeController(api.getInstance())
      validation = await controller.validateCsv(file, mapping, dateFormat)
      step = 3
    } catch (e) {
      console.error('Validation failed:', e)
    } finally {
      validating = false
    }
  }

  async function confirmImport() {
    if (!file || !$currentPortfolio) return
    importing = true
    try {
      const controller = new TradeController(api.getInstance())
      importResult = await controller.confirmImport(
        file, mapping, $currentPortfolio.id, dateFormat
      )
      goto('/trades')
    } catch (e) {
      console.error('Import failed:', e)
    } finally {
      importing = false
    }
  }

  // step indicator labels
  const STEPS = ['Upload', 'Map Columns', 'Review']
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-3xl space-y-6">

    <!-- Header -->
    <div class="space-y-1">
      <h1 class="text-2xl md:text-3xl font-bold text-foreground">Import Trades</h1>
      <p class="text-sm text-muted-foreground">
        Import historical trades from a CSV file
      </p>
    </div>

    <!-- Step indicator -->
    <div class="flex items-center gap-0">
      {#each STEPS as label, i}
        {@const n = i + 1}
        <div class="flex items-center {i < STEPS.length - 1 ? 'flex-1' : ''}">
          <div class="flex flex-col items-center gap-1">
            <div class="h-8 w-8 rounded-full flex items-center justify-center text-sm font-semibold
              {step === n ? 'bg-primary text-primary-foreground' :
               step > n  ? 'bg-primary/20 text-primary' :
               'bg-muted text-muted-foreground'}">
              {#if step > n}
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
              {:else}
                {n}
              {/if}
            </div>
            <span class="text-xs {step === n ? 'text-foreground font-medium' : 'text-muted-foreground'} hidden sm:block">
              {label}
            </span>
          </div>
          {#if i < STEPS.length - 1}
            <div class="flex-1 h-px mx-2 mt-[-1rem] {step > n ? 'bg-primary/40' : 'bg-border'}"></div>
          {/if}
        </div>
      {/each}
    </div>

    <!-- ── Step 1: Upload ───────────────────────────────────────── -->
    {#if step === 1}
      <Card title="Upload CSV File" subtitle="Select a CSV file with your trade history">

        <!-- Drop zone -->
        <label
          class="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 md:p-12 cursor-pointer transition-colors
            {dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/30'}"
          on:dragover|preventDefault={() => (dragOver = true)}
          on:dragleave={() => (dragOver = false)}
          on:drop={onDrop}
        >
          <svg class="h-10 w-10 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <div class="text-center">
            <p class="text-sm font-medium text-foreground">
              {file ? file.name : 'Drop your CSV here or click to browse'}
            </p>
            <p class="mt-1 text-xs text-muted-foreground">Only .csv files are supported</p>
          </div>
          <input type="file" accept=".csv" class="hidden" on:change={onFileChange} />
        </label>

        <!-- Preview table -->
        {#if sampleRows.length > 0}
          <div class="mt-4 space-y-2">
            <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Preview — first {sampleRows.length} rows
            </p>
            <div class="overflow-x-auto rounded-md border border-border">
              <table class="w-full text-xs">
                <thead class="bg-muted">
                  <tr>
                    {#each headers as h}
                      <th class="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">{h}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each sampleRows as row}
                    <tr class="border-t border-border">
                      {#each headers as h}
                        <td class="px-3 py-2 text-foreground whitespace-nowrap">{row[h] ?? ''}</td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      </Card>

      <div class="flex justify-end">
        <Button variant="default" disabled={!canAdvanceStep1} on:click={() => (step = 2)}>
          Next — Map Columns
        </Button>
      </div>
    {/if}

    <!-- ── Step 2: Map Columns ─────────────────────────────────── -->
    {#if step === 2}
      <Card title="Map Columns" subtitle="Match your CSV headers to the expected trade fields">
        <div class="space-y-3">
          {#each TRADE_FIELDS as field}
            <div class="flex items-center gap-3">
              <div class="w-40 shrink-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-sm font-medium text-foreground">{field.label}</span>
                  <span class="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold
                    {field.required ? 'border-transparent bg-primary text-primary-foreground' : 'text-muted-foreground'}">
                    {field.required ? 'required' : 'optional'}
                  </span>
                </div>
                {#if field.hint}
                  <p class="text-[10px] text-muted-foreground mt-0.5">{field.hint}</p>
                {/if}
              </div>
              <div class="flex-1">
                <Select
                  bind:value={mapping[field.key]}
                  options={headerOptions}
                />
              </div>
            </div>
          {/each}
        </div>
      </Card>

      <!-- Date format -->
      <Card title="Date Format" subtitle="How are dates written in your CSV?">
        <div class="space-y-3">
          <Select
            label="Format preset"
            bind:value={dateFormatPreset}
            options={DATE_FORMAT_OPTIONS}
          />
          {#if dateFormatPreset === 'custom'}
            <Input
              label="Custom format string"
              placeholder="%d-%b-%Y"
              bind:value={customDateFormat}
            />
          {/if}
          {#if mapping.trade_date}
            <p class="text-xs text-muted-foreground">
              Sample date value from CSV:
              <span class="font-mono text-foreground">
                {sampleRows[0]?.[mapping.trade_date] ?? '—'}
              </span>
            </p>
          {/if}
        </div>
      </Card>

      <div class="flex justify-between gap-3">
        <Button variant="outline" on:click={() => (step = 1)}>Back</Button>
        <Button
          variant="default"
          disabled={!requiredMapped || validating}
          on:click={validate}
        >
          {validating ? 'Validating…' : 'Validate'}
        </Button>
      </div>
    {/if}

    <!-- ── Step 3: Review & Confirm ────────────────────────────── -->
    {#if step === 3 && validation}
      <Card title="Review Import">
        <!-- Summary badges -->
        <div class="flex flex-wrap gap-3 mb-4">
          <div class="flex items-center gap-2 rounded-lg border border-border px-4 py-2">
            <span class="text-2xl font-bold text-positive">{validation.valid_count}</span>
            <span class="text-sm text-muted-foreground">rows ready</span>
          </div>
          {#if validation.error_count > 0}
            <div class="flex items-center gap-2 rounded-lg border border-border px-4 py-2">
              <span class="text-2xl font-bold text-negative">{validation.error_count}</span>
              <span class="text-sm text-muted-foreground">errors</span>
            </div>
          {/if}
        </div>

        <!-- Errors -->
        {#if validation.error_count > 0}
          <div class="mb-4">
            <button
              class="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground mb-2"
              on:click={() => (errorsExpanded = !errorsExpanded)}
            >
              <svg class="h-4 w-4 transition-transform {errorsExpanded ? 'rotate-90' : ''}"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
              {errorsExpanded ? 'Hide' : 'Show'} {validation.error_count} error{validation.error_count !== 1 ? 's' : ''}
            </button>
            {#if errorsExpanded}
              <div class="rounded-md border border-border divide-y divide-border max-h-48 overflow-y-auto">
                {#each validation.errors as err}
                  <div class="px-3 py-2 text-xs">
                    <span class="font-medium text-muted-foreground">Row {err.row}:</span>
                    <span class="ml-1 text-negative">{err.error}</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}

        <!-- Sample valid rows preview -->
        {#if validation.sample_valid_rows.length > 0}
          <div class="space-y-2">
            <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Sample valid rows
            </p>
            <div class="overflow-x-auto rounded-md border border-border">
              <table class="w-full text-xs">
                <thead class="bg-muted">
                  <tr>
                    {#each ['ticker', 'trade_type', 'trade_date', 'quantity', 'price', 'currency'] as col}
                      <th class="px-3 py-2 text-left font-medium text-muted-foreground capitalize whitespace-nowrap">
                        {col.replace('_', ' ')}
                      </th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each validation.sample_valid_rows as row}
                    <tr class="border-t border-border">
                      <td class="px-3 py-2 font-mono">{row.ticker ?? ''}</td>
                      <td class="px-3 py-2">{row.trade_type ?? ''}</td>
                      <td class="px-3 py-2 whitespace-nowrap">{String(row.trade_date ?? '').slice(0, 10)}</td>
                      <td class="px-3 py-2">{row.quantity != null ? Number(row.quantity) / 100 : ''}</td>
                      <td class="px-3 py-2">{row.price != null ? Number(row.price) / 100 : ''}</td>
                      <td class="px-3 py-2">{row.currency ?? ''}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      </Card>

      <div class="flex justify-between gap-3">
        <Button variant="outline" on:click={() => (step = 2)}>Back</Button>
        <Button
          variant="default"
          disabled={validation.valid_count === 0 || importing}
          on:click={confirmImport}
        >
          {importing ? 'Importing…' : `Import ${validation.valid_count} trade${validation.valid_count !== 1 ? 's' : ''}`}
        </Button>
      </div>
    {/if}

  </div>
</div>
