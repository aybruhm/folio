<script lang="ts">
    import { cn } from "$lib/utils/cn";

    export let variant:
        | "default"
        | "secondary"
        | "destructive"
        | "outline"
        | "success"
        | "danger" = "default";

    const variants = {
        default:
            "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
            "border-transparent bg-muted text-muted-foreground hover:bg-muted/80",
        destructive:
            "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        success:
            "border-transparent bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900 dark:text-green-100",
        danger: "border-transparent bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900 dark:text-red-100",
    };
</script>

<div
    class={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
    )}
>
    <slot />
</div>
