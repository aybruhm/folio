<script lang="ts">
  import { page } from '$app/stores'
  import Button from './Button.svelte'
  import { portfolios, currentPortfolio } from '$lib/stores'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher()

  export let isDark: boolean

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

  function handleToggleSidebar() {
    dispatch('toggleSidebar')
  }

  function handleToggleTheme() {
    dispatch('toggleTheme')
  }
</script>

<nav class="border-b border-border bg-card">
  <div class="flex h-16 items-center justify-between px-4 md:px-6">
    <div class="flex items-center gap-4 md:gap-8">
      <a href="/" class="flex items-center gap-2">
        <svg class="h-5 w-5 text-primary md:h-6 md:w-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M3 3h8v8H3V3zm10 0h8v8h-8V3zM3 13h8v8H3v-8zm10 0h8v8h-8v-8z" />
        </svg>
        <span class="text-lg font-bold text-foreground md:text-xl">Folio</span>
      </a>
    </div>

    <div class="flex items-center gap-2 md:gap-4">
      {#if $currentPortfolio}
        <div class="relative hidden md:block">
          <button
            on:click={() => (showPortfolioMenu = !showPortfolioMenu)}
            class="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm hover:bg-muted md:px-3 md:py-2"
          >
            <span class="max-w-[120px] truncate font-medium text-foreground md:max-w-none">
              {$currentPortfolio.name}
            </span>
            <svg class="h-4 w-4 flex-shrink-0 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {#if showPortfolioMenu}
            <div class="absolute right-0 top-full mt-2 w-48 rounded-md border border-border bg-card py-1 shadow-lg z-10">
              {#each $portfolios as p}
                <button
                  on:click={() => { currentPortfolio.set(p); showPortfolioMenu = false }}
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

      <!-- Theme toggle -->
      <Button variant="ghost" size="icon" on:click={handleToggleTheme} title={isDark ? 'Light mode' : 'Dark mode'}>
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

      <!-- Hamburger menu for mobile -->
      <button
        on:click={handleToggleSidebar}
        class="md:hidden rounded-md p-2 hover:bg-muted"
        title="Toggle menu"
      >
        <svg class="h-5 w-5 text-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>
  </div>
</nav>
