<script lang="ts">
  import { page } from '$app/stores'
  import Button from './Button.svelte'
  import { portfolios, currentPortfolio } from '$lib/stores'

  export let isDark: boolean
  export let onToggleTheme: (() => void) | undefined = undefined

  let showPortfolioMenu = false

  const navLinks = [
    { label: 'Dashboard', href: '/' },
    { label: 'Portfolios', href: '/portfolios' },
    { label: 'Holdings', href: '/holdings' },
    { label: 'Trades', href: '/trades' },
    { label: 'Goals', href: '/goals' },
    { label: 'Analytics', href: '/analytics' }
  ]

  function isActive(href: string): boolean {
    return $page.url.pathname === href
  }
</script>

<nav class="border-b border-border bg-card">
  <div class="flex h-16 items-center justify-between px-6">
    <div class="flex items-center gap-8">
      <a href="/" class="flex items-center gap-2">
        <svg class="h-6 w-6 text-primary" fill="currentColor" viewBox="0 0 24 24">
          <path d="M3 3h8v8H3V3zm10 0h8v8h-8V3zM3 13h8v8H3v-8zm10 0h8v8h-8v-8z" />
        </svg>
        <span class="text-xl font-bold text-foreground">Folio</span>
      </a>

      <div class="hidden gap-1 md:flex">
        {#each navLinks as link}
          <a
            href={link.href}
            class="rounded-md px-3 py-2 text-sm font-medium transition-colors {isActive(
              link.href
            )
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
          >
            {link.label}
          </a>
        {/each}
      </div>
    </div>

    <div class="flex items-center gap-4">
      {#if $currentPortfolio}
        <div class="relative">
          <button
            on:click={() => (showPortfolioMenu = !showPortfolioMenu)}
            class="flex items-center gap-2 rounded-md px-3 py-2 hover:bg-muted"
          >
            <span class="text-sm font-medium text-foreground">{$currentPortfolio.name}</span>
            <svg class="h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {#if showPortfolioMenu}
            <div class="absolute right-0 top-full mt-2 w-48 rounded-md border border-border bg-card py-1 shadow-lg">
              {#each $portfolios as p}
                <button
                  on:click={() => {
                    currentPortfolio.set(p)
                    showPortfolioMenu = false
                  }}
                  class="block w-full px-4 py-2 text-left text-sm hover:bg-muted {$currentPortfolio.id === p.id
                    ? 'bg-accent text-accent-foreground'
                    : 'text-foreground'}"
                >
                  {p.name}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <Button
        variant="ghost"
        size="icon"
        on:click={onToggleTheme}
        title={isDark ? 'Light mode' : 'Dark mode'}
      >
        {#if isDark}
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        {:else}
          <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        {/if}
      </Button>
    </div>
  </div>
</nav>
