<script lang="ts">
    import { offlineStore } from "$lib/stores/offline";
</script>

{#if !$offlineStore.isOnline}
    <div class="offline-banner">
        <span class="text">You're offline</span>
        {#if $offlineStore.syncInProgress}
            <span class="spinner" />
        {/if}
        {#if $offlineStore.pendingChanges > 0}
            <span class="badge">{$offlineStore.pendingChanges} pending</span>
        {/if}
    </div>
{/if}

<style>
    .offline-banner {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #f97316;
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
    }

    .icon {
        font-size: 16px;
    }

    .spinner {
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .badge {
        background: rgba(255, 255, 255, 0.2);
        padding: 0 6px;
        border-radius: 4px;
    }
</style>
