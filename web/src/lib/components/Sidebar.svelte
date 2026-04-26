<script lang="ts">
  import { page } from '$app/stores'

  export let open = false
  export let onClose: () => void = () => {}

  const navLinks = [
    {
      label: 'Dashboard',
      href: '/',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />`
    },
    {
      label: 'Portfolios',
      href: '/portfolios',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />`
    },
    {
      label: 'Holdings',
      href: '/holdings',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />`
    },
    {
      label: 'Trades',
      href: '/trades',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />`
    },
    {
      label: 'Goals',
      href: '/goals',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />`
    },
    {
      label: 'Analytics',
      href: '/analytics',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />`
    }
  ]

  $: currentPath = $page.url.pathname
</script>

<!-- Desktop sidebar -->
<aside class="hidden md:flex md:flex-col md:w-56 border-r border-border bg-card shrink-0">
  <nav class="flex-1 space-y-1 px-3 py-4">
    {#each navLinks as link}
      <a
        href={link.href}
        class="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors {currentPath === link.href
          ? 'bg-accent text-accent-foreground'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
      >
        <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {@html link.icon}
        </svg>
        {link.label}
      </a>
    {/each}
  </nav>
</aside>

<!-- Mobile drawer overlay -->
{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/50 md:hidden"
    on:click={onClose}
  ></div>

  <aside class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card md:hidden">
    <div class="flex h-16 items-center justify-between px-4 border-b border-border">
      <span class="text-sm font-semibold text-foreground">Menu</span>
      <button on:click={onClose} class="rounded-md p-1.5 hover:bg-muted">
        <svg class="h-5 w-5 text-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
      {#each navLinks as link}
        <a
          href={link.href}
          on:click={onClose}
          class="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors {currentPath === link.href
            ? 'bg-accent text-accent-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
        >
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {@html link.icon}
          </svg>
          {link.label}
        </a>
      {/each}
    </nav>
  </aside>
{/if}
