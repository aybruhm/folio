<script lang="ts">
    import { page } from "$app/stores";
    import { goto } from "$app/navigation";
    import Button from "./Button.svelte";
    import { portfolios, currentPortfolio, hideAmounts } from "$lib/stores";
    import { clearAuthToken } from "$lib/stores/offlineAuth";
    import { createEventDispatcher } from "svelte";

    const dispatch = createEventDispatcher();

    export let isDark: boolean;

    let showPortfolioMenu = false;

    function handleToggleSidebar() {
        dispatch("toggleSidebar");
    }

    function handleToggleTheme() {
        dispatch("toggleTheme");
    }

    async function handleLogout() {
        clearAuthToken();
        await goto("/login");
    }
</script>

<nav class="sticky top-0 z-30 border-b border-border/60 bg-background/90 backdrop-blur-md">
    <div class="flex h-14 items-center justify-between px-4 md:px-6">
        <!-- Logo -->
        <div class="flex items-center gap-4 md:gap-6">
            <a href="/" class="flex items-center gap-2.5 group">
                <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 border border-accent/30 transition-colors group-hover:bg-accent/25">
                    <svg class="h-3.5 w-3.5 text-accent" viewBox="0 0 16 16" fill="currentColor">
                        <rect x="1" y="1" width="6" height="6" rx="1" />
                        <rect x="9" y="1" width="6" height="6" rx="1" opacity="0.6" />
                        <rect x="1" y="9" width="6" height="6" rx="1" opacity="0.6" />
                        <rect x="9" y="9" width="6" height="6" rx="1" opacity="0.3" />
                    </svg>
                </div>
                <span class="font-serif text-xl font-normal tracking-tight text-foreground">Folio</span>
            </a>
        </div>

        <div class="flex items-center gap-1 md:gap-2">
            <!-- Portfolio selector (desktop) -->
            <div class="relative hidden md:block">
                <button
                    on:click={() => (showPortfolioMenu = !showPortfolioMenu)}
                    class="flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:border-accent/50 hover:bg-muted"
                >
                    <span class="max-w-[140px] truncate font-medium">
                        {$currentPortfolio?.id ? $currentPortfolio.name : "All Portfolios"}
                    </span>
                    <svg
                        class="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground transition-transform {showPortfolioMenu ? 'rotate-180' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {#if showPortfolioMenu}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div class="fixed inset-0 z-10" on:click={() => (showPortfolioMenu = false)}></div>
                    <div class="absolute right-0 top-full z-20 mt-2 w-52 overflow-hidden rounded-xl border border-border bg-popover py-1 shadow-xl shadow-black/20">
                        <button
                            on:click={() => {
                                currentPortfolio.set({ id: "", name: "", base_currency: "USD", created_at: "", updated_at: "" });
                                showPortfolioMenu = false;
                            }}
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors {!$currentPortfolio?.id ? 'bg-accent/15 text-accent font-medium' : 'text-foreground hover:bg-muted'}"
                        >
                            {#if !$currentPortfolio?.id}
                                <span class="h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0"></span>
                            {:else}
                                <span class="h-1.5 w-1.5 flex-shrink-0"></span>
                            {/if}
                            All Portfolios
                        </button>
                        {#each $portfolios as p}
                            <button
                                on:click={() => { currentPortfolio.set(p); showPortfolioMenu = false; }}
                                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors {$currentPortfolio.id === p.id ? 'bg-accent/15 text-accent font-medium' : 'text-foreground hover:bg-muted'}"
                            >
                                {#if $currentPortfolio.id === p.id}
                                    <span class="h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0"></span>
                                {:else}
                                    <span class="h-1.5 w-1.5 flex-shrink-0"></span>
                                {/if}
                                {p.name}
                            </button>
                        {/each}
                    </div>
                {/if}
            </div>

            <!-- Divider (desktop) -->
            <div class="hidden md:block h-5 w-px bg-border mx-1"></div>

            <!-- Hide amounts toggle -->
            <Button
                variant="ghost"
                size="icon"
                on:click={() => hideAmounts.toggle()}
                title={$hideAmounts ? "Show amounts" : "Hide amounts"}
                class="text-muted-foreground hover:text-foreground"
            >
                {#if $hideAmounts}
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                {:else}
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                {/if}
            </Button>

            <!-- Theme toggle -->
            <Button
                variant="ghost"
                size="icon"
                on:click={handleToggleTheme}
                title={isDark ? "Light mode" : "Dark mode"}
                class="text-muted-foreground hover:text-foreground"
            >
                {#if isDark}
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                {:else}
                    <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                    </svg>
                {/if}
            </Button>

            <!-- Logout -->
            <Button
                variant="ghost"
                size="icon"
                on:click={handleLogout}
                title="Sign out"
                class="text-muted-foreground hover:text-foreground"
            >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
            </Button>

            <!-- Hamburger (mobile) -->
            <button
                on:click={handleToggleSidebar}
                class="md:hidden rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                title="Toggle menu"
            >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
            </button>
        </div>
    </div>
</nav>
