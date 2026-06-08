export default {
    content: ['./src/**/*.{html,js,svelte,ts}'],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                background: 'hsl(var(--background))',
                foreground: 'hsl(var(--foreground))',
                card: 'hsl(var(--card))',
                'card-foreground': 'hsl(var(--card-foreground))',
                popover: 'hsl(var(--popover))',
                'popover-foreground': 'hsl(var(--popover-foreground))',
                muted: 'hsl(var(--muted))',
                'muted-foreground': 'hsl(var(--muted-foreground))',
                accent: 'hsl(var(--accent))',
                'accent-foreground': 'hsl(var(--accent-foreground))',
                destructive: 'hsl(var(--destructive))',
                'destructive-foreground': 'hsl(var(--destructive-foreground))',
                border: 'hsl(var(--border))',
                input: 'hsl(var(--input))',
                ring: 'hsl(var(--ring))',
                secondary: 'hsl(var(--secondary))',
                'secondary-foreground': 'hsl(var(--secondary-foreground))',
                primary: 'hsl(var(--primary))',
                'primary-foreground': 'hsl(var(--primary-foreground))',
                positive: '#22c55e',
                negative: '#ef4444'
            },
            borderRadius: {
                lg: 'calc(var(--radius) + 0.25rem)',
                md: 'calc(var(--radius))',
                sm: 'calc(var(--radius) - 0.125rem)'
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'monospace'],
                sans: ['DM Sans', 'system-ui', 'sans-serif'],
                serif: ['Instrument Serif', 'Georgia', 'serif']
            }
        }
    },
    plugins: []
}
