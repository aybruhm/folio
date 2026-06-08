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
    <title>Sign in — folio</title>
</svelte:head>

<div class="min-h-screen bg-background flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
        <div class="text-center mb-8">
            <h1 class="text-2xl font-bold text-foreground tracking-tight">
                folio
            </h1>
        </div>

        <div class="bg-card border border-border rounded-xl p-8">
            <h2 class="text-lg font-semibold text-foreground mb-6">
                Welcome back
            </h2>

            {#if errorMessage}
                <div
                    class="mb-4 p-3 rounded-lg border border-destructive bg-destructive/10 text-destructive text-sm"
                    role="alert"
                    aria-live="assertive"
                >
                    {errorMessage}
                </div>
            {/if}

            <form on:submit={handleSubmit} novalidate>
                <div class="mb-4">
                    <label
                        for="email"
                        class="block text-sm font-medium text-foreground mb-1.5"
                    >
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        required
                        autocomplete="email"
                        class="w-full px-3 py-2 rounded-lg bg-background border border-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
                        placeholder="you@example.com"
                    />
                </div>

                <div class="mb-6">
                    <label
                        for="password"
                        class="block text-sm font-medium text-foreground mb-1.5"
                    >
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        bind:value={password}
                        required
                        autocomplete="current-password"
                        class="w-full px-3 py-2 rounded-lg bg-background border border-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
                        placeholder="••••••••"
                    />
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    class="w-full py-2.5 px-4 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-60 disabled:cursor-not-allowed font-medium text-sm transition-colors"
                >
                    {isSubmitting ? "Signing in…" : "Sign in"}
                </button>
            </form>

            {#if registrationEnabled}
                <p class="mt-6 text-center text-sm text-muted-foreground">
                    Don't have an account?
                    <a
                        href="/register"
                        class="text-primary hover:text-primary/80 ml-1"
                    >
                        Register →
                    </a>
                </p>
            {/if}
        </div>
    </div>
</div>
