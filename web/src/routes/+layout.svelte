<script lang="ts">
  import '../app.css'
  import Navigation from '$lib/components/Navigation.svelte'
  import { onMount } from 'svelte'
  import { portfolios, currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'

  let isDark = true

  onMount(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark = localStorage.getItem('theme') === 'light' ? false : prefersDark || true
    applyTheme()

    loadPortfolios()
  })

  function applyTheme() {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleTheme() {
    isDark = !isDark
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
    applyTheme()
  }

  async function loadPortfolios() {
    try {
      const data = await api.get<any[]>('/portfolios')
      portfolios.set(data || [])
      if (data && data.length > 0) {
        currentPortfolio.set(data[0])
      }
    } catch (e) {
      console.error('Failed to load portfolios:', e)
    }
  }
</script>

<div class="flex h-screen flex-col bg-background text-foreground">
  <Navigation {isDark} on:toggleTheme={toggleTheme} />

  <main class="flex-1 overflow-auto">
    <slot />
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', 'Geist', system-ui, sans-serif;
  }
</style>
