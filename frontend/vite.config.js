import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on 0.0.0.0
    port: 3000,
    // Enable polling for hot-reloading in Docker
    watch: {
      usePolling: true,
    },
  },
})
