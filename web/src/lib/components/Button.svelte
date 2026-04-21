<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'danger' = 'primary'
  export let size: 'sm' | 'md' | 'lg' = 'md'
  export let disabled = false
  export let type: 'button' | 'submit' | 'reset' = 'button'

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  }

  const variantClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-700 dark:hover:bg-blue-800',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-900 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white dark:bg-red-700 dark:hover:bg-red-800'
  }

  const baseClasses = 'font-medium rounded transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed'
</script>

<button
  {type}
  {disabled}
  class="{baseClasses} {sizeClasses[size]} {variantClasses[variant]}"
  on:click
>
  <slot />
</button>
