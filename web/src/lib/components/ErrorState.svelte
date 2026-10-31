<script lang="ts">
    import Card from "./Card.svelte";
    import Button from "./Button.svelte";

    export let title = "Couldn't load this page";
    export let message =
        "Something went wrong while fetching your data. Check your connection and try again.";
    export let onRetry: (() => void) | null = null;
    export let retrying = false;
</script>

<Card>
    <div class="flex flex-col items-center justify-center py-12 text-center" role="alert">
        <p class="font-medium text-foreground mb-1">{title}</p>
        <p class="text-sm text-muted-foreground mb-6 max-w-md">{message}</p>
        {#if onRetry}
            <Button variant="outline" disabled={retrying} on:click={onRetry}>
                {retrying ? "Retrying…" : "Try again"}
            </Button>
        {/if}
    </div>
</Card>
