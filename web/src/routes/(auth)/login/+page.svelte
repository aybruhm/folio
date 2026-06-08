<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { api } from "$lib/api/client";
    import { authUser } from "$lib/stores";
    import { env } from "$env/dynamic/public";

    let email = "";
    let password = "";
    let errorMessage = "";
    let isSubmitting = false;

    const registrationEnabled = env.PUBLIC_ENABLE_REGISTRATION !== "false";

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        errorMessage = "";
        isSubmitting = true;

        try {
            const user = await api.post<{ id: string; email: string }>(
                "/auth/login",
                { email, password },
            );
            authUser.set(user);
            const redirectTo = $page.url.searchParams.get("redirect") ?? "/";
            await goto(redirectTo);
        } catch {
            errorMessage = "Invalid email or password. Please try again.";
            password = "";
        } finally {
            isSubmitting = false;
        }
    }
</script>

<svelte:head>
    <title>Sign in — Folio</title>
</svelte:head>

<div class="min-h-screen bg-background flex items-center justify-center px-4 py-12">
    <!-- Background texture is inherited from body -->

    <div class="w-full max-w-sm animate-in">
        <!-- Brand -->
        <div class="text-center mb-10">
            <div class="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-accent/15 border border-accent/30 mb-5">
                <svg class="h-6 w-6 text-accent" viewBox="0 0 16 16" fill="currentColor">
                    <rect x="1" y="1" width="6" height="6" rx="1" />
                    <rect x="9" y="1" width="6" height="6" rx="1" opacity="0.6" />
                    <rect x="1" y="9" width="6" height="6" rx="1" opacity="0.6" />
                    <rect x="9" y="9" width="6" height="6" rx="1" opacity="0.3" />
                </svg>
            </div>
            <h1 class="font-serif text-4xl text-foreground mb-2">Folio</h1>
            <p class="text-sm text-muted-foreground">Track your wealth, clearly.</p>
        </div>

        <!-- Card -->
        <div class="rounded-2xl border border-border bg-card/80 backdrop-blur-sm p-7 shadow-xl shadow-black/10">
            <h2 class="text-base font-semibold text-foreground mb-5">
                Welcome back
            </h2>

            {#if errorMessage}
                <div
                    class="mb-4 p-3 rounded-lg border border-destructive/40 bg-destructive/8 text-destructive text-sm"
                    role="alert"
                    aria-live="assertive"
                >
                    {errorMessage}
                </div>
            {/if}

            <form on:submit={handleSubmit} novalidate>
                <div class="mb-4">
                    <label for="email" class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        required
                        autocomplete="email"
                        class="w-full px-3.5 py-2.5 rounded-lg bg-background border border-input text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm transition-colors"
                        placeholder="you@example.com"
                    />
                </div>

                <div class="mb-6">
                    <label for="password" class="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        bind:value={password}
                        required
                        autocomplete="current-password"
                        class="w-full px-3.5 py-2.5 rounded-lg bg-background border border-input text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm transition-colors"
                        placeholder="••••••••"
                    />
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    class="w-full py-2.5 px-4 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-60 disabled:cursor-not-allowed font-medium text-sm transition-all shadow-sm shadow-accent/20"
                >
                    {isSubmitting ? "Signing in…" : "Sign in"}
                </button>
            </form>

            {#if registrationEnabled}
                <p class="mt-5 text-center text-xs text-muted-foreground">
                    Don't have an account?
                    <a href="/register" class="text-accent hover:text-accent/80 ml-1 font-medium transition-colors">
                        Create one →
                    </a>
                </p>
            {/if}
        </div>
    </div>
</div>
