<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { api } from "$lib/api/client";
    import { authUser } from "$lib/stores";

    let email = "";
    let password = "";
    let errorMessage = "";
    let isSubmitting = false;

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

<div class="min-h-screen bg-gray-950 flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
        <div class="text-center mb-8">
            <h1 class="text-2xl font-bold text-white tracking-tight">folio</h1>
        </div>

        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8">
            <h2 class="text-lg font-semibold text-white mb-6">Welcome back</h2>

            {#if errorMessage}
                <div
                    class="mb-4 p-3 rounded-lg bg-red-950 border border-red-800 text-red-300 text-sm"
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
                        class="block text-sm font-medium text-gray-300 mb-1.5"
                    >
                        Email
                    </label>
                    <input
                        id="email"
                        type="email"
                        bind:value={email}
                        required
                        autocomplete="email"
                        class="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="you@example.com"
                    />
                </div>

                <div class="mb-6">
                    <label
                        for="password"
                        class="block text-sm font-medium text-gray-300 mb-1.5"
                    >
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        bind:value={password}
                        required
                        autocomplete="current-password"
                        class="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        placeholder="••••••••"
                    />
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    class="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
                >
                    {isSubmitting ? "Signing in…" : "Sign in"}
                </button>
            </form>

            <p class="mt-6 text-center text-sm text-gray-500">
                Don't have an account?
                <a href="/register" class="text-blue-400 hover:text-blue-300 ml-1">
                    Register →
                </a>
            </p>
        </div>
    </div>
</div>
