export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0f0f0f',
        surface: '#1a1a1a',
        border: '#2a2a2a',
        positive: '#22c55e',
        negative: '#ef4444',
        accent: '#6366f1'
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'Geist', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
}
