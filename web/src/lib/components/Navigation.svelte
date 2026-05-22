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

    const navLinks = [
        { label: "Dashboard", href: "/" },
        { label: "Portfolios", href: "/portfolios" },
        { label: "Holdings", href: "/holdings" },
        { label: "Trades", href: "/trades" },
        { label: "Goals", href: "/goals" },
        { label: "Analytics", href: "/analytics" },
    ];

    function isActive(href: string): boolean {
        return $page.url.pathname === href;
    }

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

<nav class="border-b border-border bg-card">
    <div class="flex h-16 items-center justify-between px-4 md:px-6">
        <div class="flex items-center gap-4 md:gap-8">
            <a href="/" class="flex items-center gap-2">
                <svg
                    class="h-5 w-5 text-primary md:h-6 md:w-6"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        d="M3 3h8v8H3V3zm10 0h8v8h-8V3zM3 13h8v8H3v-8zm10 0h8v8h-8v-8z"
                    />
                </svg>
                <span class="text-lg font-bold text-foreground md:text-xl"
                    >Folio</span
                >
            </a>
        </div>

        <div class="flex items-center gap-2 md:gap-4">
            <div class="relative hidden md:block">
                <button
                    on:click={() => (showPortfolioMenu = !showPortfolioMenu)}
                    class="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm hover:bg-muted md:px-3 md:py-2"
                >
                    <span
                        class="max-w-[120px] truncate font-medium text-foreground md:max-w-none"
                    >
                        {$currentPortfolio?.id
                            ? $currentPortfolio.name
                            : "Aggregated"}
                    </span>
                    <svg
                        class="h-4 w-4 flex-shrink-0 text-muted-foreground"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 9l-7 7-7-7"
                        />
                    </svg>
                </button>

                {#if showPortfolioMenu}
                    <div
                        class="absolute right-0 top-full mt-2 w-48 rounded-md border border-border bg-card py-1 shadow-lg z-10"
                    >
                        <button
                            on:click={() => {
                                currentPortfolio.set({
                                    id: "",
                                    name: "",
                                    base_currency: "USD",
                                    created_at: "",
                                    updated_at: "",
                                });
                                showPortfolioMenu = false;
                            }}
                            class="block w-full px-4 py-2 text-left text-sm hover:bg-muted {!$currentPortfolio?.id
                                ? 'bg-accent text-accent-foreground'
                                : 'text-foreground'}"
                        >
                            Aggregated
                        </button>
                        {#each $portfolios as p}
                            <button
                                on:click={() => {
                                    currentPortfolio.set(p);
                                    showPortfolioMenu = false;
                                }}
                                class="block w-full px-4 py-2 text-left text-sm hover:bg-muted {$currentPortfolio.id ===
                                p.id
                                    ? 'bg-accent text-accent-foreground'
                                    : 'text-foreground'}"
                            >
                                {p.name}
                            </button>
                        {/each}
                    </div>
                {/if}
            </div>

            <!-- Hide amounts toggle -->
            <Button
                variant="ghost"
                size="icon"
                on:click={() => hideAmounts.toggle()}
                title={$hideAmounts ? "Show amounts" : "Hide amounts"}
            >
                {#if $hideAmounts}
                    <svg
                        class="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                        />
                    </svg>
                {:else}
                    <svg
                        class="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                        />
                    </svg>
                {/if}
            </Button>

            <!-- Theme toggle -->
            <Button
                variant="ghost"
                size="icon"
                on:click={handleToggleTheme}
                title={isDark ? "Light mode" : "Dark mode"}
            >
                {#if isDark}
                    <svg
                        class="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                        />
                    </svg>
                {:else}
                    <svg
                        class="h-5 w-5"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
                        />
                    </svg>
                {/if}
            </Button>

            <!-- Logout button -->
            <Button
                variant="ghost"
                size="icon"
                on:click={handleLogout}
                title="Logout"
            >
                <svg
                    class="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                </svg>
            </Button>

            <!-- Hamburger menu for mobile -->
            <button
                on:click={handleToggleSidebar}
                class="md:hidden rounded-md p-2 hover:bg-muted"
                title="Toggle menu"
            >
                <svg
                    class="h-5 w-5 text-foreground"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 6h16M4 12h16M4 18h16"
                    />
                </svg>
            </button>
        </div>
    </div>
</nav>
