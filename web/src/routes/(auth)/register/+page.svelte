<script lang="ts">
    import { goto } from "$app/navigation";
    import { api } from "$lib/api/client";
    import { authUser } from "$lib/stores";

    let email = "";
    let password = "";
    let confirmPassword = "";
    let errorMessage = "";
    let emailError = "";
    let passwordError = "";
    let confirmError = "";
    let isSubmitting = false;

    function validate(): boolean {
        passwordError = "";
        confirmError = "";
        emailError = "";

        if (password.length < 8) {
            passwordError = "Password must be at least 8 characters.";
        }
        if (password !== confirmPassword) {
            confirmError = "Passwords do not match.";
        }
        return !passwordError && !confirmError;
    }

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        errorMessage = "";

        if (!validate()) return;

        isSubmitting = true;

        try {
            const user = await api.post<{ id: string; email: string }>(
                "/auth/register",
                { email, password },
            );
            authUser.set(user);
            await goto("/");
        } catch (err: unknown) {
            const message = (err as Error).message ?? "";
            if (
                message.includes("already registered") ||
                message.includes("409")
            ) {
                emailError = "An account with this email already exists.";
            } else if (message.includes("429")) {
                errorMessage =
                    "Too many attempts. Please wait a moment and try again.";
            } else {
                errorMessage = "Something went wrong. Please try again.";
            }
        } finally {
            isSubmitting = false;
        }
    }
</script>

<svelte:head>
    <title>Create account — folio</title>
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
                Create your account
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
                        aria-describedby={emailError
                            ? "email-error"
                            : undefined}
                        class="w-full px-3 py-2 rounded-lg bg-background border {emailError
                            ? 'border-destructive'
                            : 'border-input'} text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
                        placeholder="you@example.com"
                    />
                    {#if emailError}
                        <p
                            id="email-error"
                            class="mt-1 text-xs text-destructive"
                        >
                            {emailError}
                        </p>
                    {/if}
                </div>

                <div class="mb-4">
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
                        autocomplete="new-password"
                        aria-describedby="password-hint {passwordError
                            ? 'password-error'
                            : ''}"
                        class="w-full px-3 py-2 rounded-lg bg-background border {passwordError
                            ? 'border-destructive'
                            : 'border-input'} text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
                        placeholder="••••••••"
                    />
                    {#if passwordError}
                        <p
                            id="password-error"
                            class="mt-1 text-xs text-destructive"
                        >
                            {passwordError}
                        </p>
                    {:else}
                        <p
                            id="password-hint"
                            class="mt-1 text-xs text-muted-foreground"
                        >
                            Must be at least 8 characters.
                        </p>
                    {/if}
                </div>

                <div class="mb-6">
                    <label
                        for="confirm-password"
                        class="block text-sm font-medium text-foreground mb-1.5"
                    >
                        Confirm password
                    </label>
                    <input
                        id="confirm-password"
                        type="password"
                        bind:value={confirmPassword}
                        required
                        autocomplete="new-password"
                        aria-describedby={confirmError
                            ? "confirm-error"
                            : undefined}
                        class="w-full px-3 py-2 rounded-lg bg-background border {confirmError
                            ? 'border-destructive'
                            : 'border-input'} text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
                        placeholder="••••••••"
                    />
                    {#if confirmError}
                        <p
                            id="confirm-error"
                            class="mt-1 text-xs text-destructive"
                        >
                            {confirmError}
                        </p>
                    {/if}
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    class="w-full py-2.5 px-4 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-60 disabled:cursor-not-allowed font-medium text-sm transition-colors"
                >
                    {isSubmitting ? "Creating account…" : "Create account"}
                </button>
            </form>

            <p class="mt-6 text-center text-sm text-muted-foreground">
                Already have an account?
                <a
                    href="/login"
                    class="text-primary hover:text-primary/80 ml-1"
                >
                    Sign in →
                </a>
            </p>
        </div>
    </div>
</div>
