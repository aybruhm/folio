<script lang="ts">
  import { page } from '$app/stores'
  import { goto } from '$app/navigation'
  import { portfolios, currentPortfolio } from '$lib/stores'
  import { clearAuthToken } from '$lib/stores/offlineAuth'

  export let open = false
  export let onClose: () => void = () => {}

  let showPortfolioMenu = false

  const navLinks = [
    {
      label: 'Dashboard',
      href: '/',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />`
    },
    {
      label: 'Portfolios',
      href: '/portfolios',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />`
    },
    {
      label: 'Holdings',
      href: '/holdings',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />`
    },
    {
      label: 'Trades',
      href: '/trades',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />`
    },
    {
      label: 'Goals',
      href: '/goals',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />`
    },
    {
      label: 'Analytics',
      href: '/analytics',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />`
    }
  ]

  $: currentPath = $page.url.pathname

  async function handleLogout() {
    clearAuthToken()
    onClose()
    await goto('/login')
  }
</script>

<!-- Desktop sidebar -->
<aside class="hidden md:flex md:flex-col md:w-[220px] border-r border-border/60 bg-card/50 shrink-0">
  <!-- Portfolio context label -->
  <div class="px-4 py-3 border-b border-border/40">
    <p class="text-[10px] font-medium uppercase tracking-widest text-muted-foreground mb-1">Portfolio</p>
    <p class="text-sm font-medium text-foreground truncate">
      {$currentPortfolio?.id ? $currentPortfolio.name : 'All Portfolios'}
    </p>
  </div>

  <nav class="flex-1 space-y-0.5 px-2 py-3">
    {#each navLinks as link}
      <a
        href={link.href}
        class="relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all {currentPath === link.href
          ? 'text-foreground bg-accent/8'
          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'}"
      >
        {#if currentPath === link.href}
          <span class="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-accent"></span>
        {/if}
        <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {@html link.icon}
        </svg>
        {link.label}
      </a>
    {/each}
  </nav>

  <div class="border-t border-border/40 px-2 py-3">
    <button
      on:click={handleLogout}
      class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all w-full text-muted-foreground hover:bg-muted/50 hover:text-foreground"
    >
      <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
      </svg>
      Sign out
    </button>
  </div>
</aside>

<!-- Mobile drawer overlay -->
{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
    on:click={onClose}
  ></div>

  <aside class="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border/60 bg-card md:hidden">
    <div class="flex h-14 items-center justify-between px-4 border-b border-border/40">
      <div class="flex items-center gap-2.5">
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 border border-accent/30">
          <svg class="h-3 w-3 text-accent" viewBox="0 0 16 16" fill="currentColor">
            <rect x="1" y="1" width="6" height="6" rx="1" />
            <rect x="9" y="1" width="6" height="6" rx="1" opacity="0.6" />
            <rect x="1" y="9" width="6" height="6" rx="1" opacity="0.6" />
            <rect x="9" y="9" width="6" height="6" rx="1" opacity="0.3" />
          </svg>
        </div>
        <span class="font-serif text-lg text-foreground">Folio</span>
      </div>
      <button on:click={onClose} class="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <nav class="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
      <!-- Portfolio selector (mobile) -->
      <div class="mb-3 pb-3 border-b border-border/40">
        <button
          on:click={() => (showPortfolioMenu = !showPortfolioMenu)}
          class="w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors bg-muted/50 hover:bg-muted text-foreground"
        >
          <span class="truncate">{$currentPortfolio?.id ? $currentPortfolio.name : 'All Portfolios'}</span>
          <svg class="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground transition-transform {showPortfolioMenu ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {#if showPortfolioMenu}
          <div class="mt-1.5 space-y-0.5">
            <button
              on:click={() => { currentPortfolio.set({ id: "", name: "", base_currency: "USD", created_at: "", updated_at: "" }); showPortfolioMenu = false }}
              class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm rounded-lg transition-colors {!$currentPortfolio?.id ? 'bg-accent/15 text-accent font-medium' : 'text-foreground hover:bg-muted/50'}"
            >
              {#if !$currentPortfolio?.id}<span class="h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0"></span>{:else}<span class="h-1.5 w-1.5 flex-shrink-0"></span>{/if}
              All Portfolios
            </button>
            {#each $portfolios as p}
              <button
                on:click={() => { currentPortfolio.set(p); showPortfolioMenu = false }}
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm rounded-lg transition-colors {$currentPortfolio.id === p.id ? 'bg-accent/15 text-accent font-medium' : 'text-foreground hover:bg-muted/50'}"
              >
                {#if $currentPortfolio.id === p.id}<span class="h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0"></span>{:else}<span class="h-1.5 w-1.5 flex-shrink-0"></span>{/if}
                {p.name}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      {#each navLinks as link}
        <a
          href={link.href}
          on:click={onClose}
          class="relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all {currentPath === link.href
            ? 'text-foreground bg-accent/8'
            : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'}"
        >
          {#if currentPath === link.href}
            <span class="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-accent"></span>
          {/if}
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {@html link.icon}
          </svg>
          {link.label}
        </a>
      {/each}
    </nav>

    <div class="border-t border-border/40 px-2 py-3">
      <button
        on:click={handleLogout}
        class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all w-full text-muted-foreground hover:bg-muted/50 hover:text-foreground"
      >
        <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        Sign out
      </button>
    </div>
  </aside>
{/if}
