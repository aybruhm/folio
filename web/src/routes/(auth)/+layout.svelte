<script lang="ts">
    import "../../app.css";
    import { onMount } from 'svelte';

    let isDark = true;

    onMount(() => {
        // Load theme preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        isDark = localStorage.getItem('theme') === 'light' ? false : prefersDark || true;
        applyTheme();
    });

    function applyTheme() {
        if (isDark) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }
</script>

<slot />
