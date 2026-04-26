import { defineConfig } from 'vite'
import { sveltekit } from '@sveltejs/kit/vite'

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    hmr: {
      host: 'localhost',
      port: 3000
    }
  }
})
