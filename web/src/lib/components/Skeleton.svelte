<script lang="ts">
    export let className: string = "";
</script>

<div class="skeleton rounded {className}" />

<style>
    .skeleton {
        position: relative;
        overflow: hidden;
        background-color: hsl(0, 0%, 88%);
    }

    :global(.dark .skeleton) {
        background-color: hsl(0, 0%, 22%);
    }

    .skeleton::after {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(
            90deg,
            transparent 0%,
            rgba(255, 255, 255, 0.45) 50%,
            transparent 100%
        );
        animation: skeleton-shimmer 1.5s ease-in-out infinite;
    }

    @keyframes skeleton-shimmer {
        0% {
            transform: translateX(-100%);
        }
        100% {
            transform: translateX(100%);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .skeleton::after {
            animation: none;
        }
    }
</style>
