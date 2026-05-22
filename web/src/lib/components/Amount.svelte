<script lang="ts">
    import { hideAmounts } from "$lib/stores";

    export let value: string;
    let className: string = "";
    export { className as class };
</script>

<span class={className}>
    {#if $hideAmounts}
        ••••
    {:else}
        {value}
    {/if}
</span>
